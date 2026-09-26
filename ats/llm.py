"""Provider abstraction. Both branches return the same JSON shape so downstream
code is provider-agnostic and results are directly comparable for ensembling.

Keys are read from the request or the environment, never persisted, never logged.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("ats.llm")

ANTHROPIC_MODEL = "claude-sonnet-5"
OPENAI_MODEL = "gpt-5.6-luna"

# Sized for a whole pass of findings/rewrites. Too small and the model is cut off
# mid-object, which reads downstream as "unparseable JSON" -- a truncation bug
# wearing a parse bug's clothes, so it must not be tuned down casually.
MAX_TOKENS = 16000

# Claude's cap is separate and larger because claude-sonnet-5 runs adaptive thinking
# when `thinking` is omitted, and thinking tokens count against max_tokens: the
# per-place content reply plus thinking overran 16000 on 13-14 bullet resumes. A cap
# this size needs the streaming helper; the SDK refuses it on a plain `create`.
ANTHROPIC_MAX_TOKENS = 64000

# Seconds per attempt. For Claude, which streams, this is the read timeout between
# chunks -- an inactivity bound, not a wall clock -- so a long healthy reply outlasts
# it; OpenAI does not stream, so there it bounds the whole reply. The SDKs retry a
# timeout (default max_retries=2) and `call()` may run a second `_dispatch` for JSON
# repair, so a thread `ensemble.gather` has given up on can outlive this by several
# attempts -- but it bounds what used to be the SDKs' default ten minutes per attempt.
CALL_TIMEOUT = 180.0

# Wall-clock seconds per streamed Claude attempt. Pings and deltas reset the read
# timeout above, so without this a runaway reply keeps billing up to the token cap
# after `ensemble.gather` has given up on it. Sits inside the content pass's 600 s
# budget (`passes.CONTENT_TIMEOUT`) with room for the connect and a slow first byte.
STREAM_DEADLINE = 540.0

# OpenAI renamed max_tokens -> max_completion_tokens and pinned temperature to its
# default on everything after the gpt-4 generation, and still serves both eras from
# one SDK -- so the model, not the SDK, decides which spelling a request gets.
# Anthropic needs no such split: sampling parameters are gone from the current
# models and from the 1.x SDK's signature, so temperature is simply never sent.
LEGACY_OPENAI = re.compile(r"^(?:gpt-4|gpt-3\.5|chatgpt-)")


class LLMError(RuntimeError):
    pass


@dataclass
class Provider:
    name: str
    api_key: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.name}:{self.model}"


def providers_from(keys: dict[str, str], models: dict[str, str] | None = None) -> list[Provider]:
    """Build the provider list. Both keys present means cross-provider ensembling."""
    models = models or {}
    found: list[Provider] = []
    anthropic_key = (keys.get("anthropic") or os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    openai_key = (keys.get("openai") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if anthropic_key:
        found.append(Provider("anthropic", anthropic_key,
                              models.get("anthropic") or ANTHROPIC_MODEL))
    if openai_key:
        found.append(Provider("openai", openai_key, models.get("openai") or OPENAI_MODEL))
    return found


def _extract_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def call(provider: Provider, system: str, user: str, temperature: float = 0.0) -> dict[str, Any]:
    """One JSON-mode call. Retries once with a repair instruction on parse failure."""
    try:
        raw = _dispatch(provider, system, user, temperature)
    except LLMError:
        raise
    except Exception as exc:  # noqa: BLE001 - surfaced as a per-pass degradation
        raise LLMError(f"{provider.label}: {exc}") from exc

    try:
        return _extract_json(raw)
    except json.JSONDecodeError:
        log.warning("%s returned unparseable JSON; retrying once", provider.label)
        repair = (
            f"{user}\n\nYour previous reply was not valid JSON. Return only the JSON "
            "object, with no prose, no markdown fence, and no trailing commas."
        )
        raw = _dispatch(provider, system, repair, 0.0)
        try:
            return _extract_json(raw)
        except json.JSONDecodeError as exc:
            raise LLMError(f"{provider.label}: unparseable JSON after repair ({exc})") from exc


def _truncated(label: str, reason: str | None, cap: int) -> None:
    """A response cut off at the token cap is a truncation failure, not a parse one.

    Retrying it with a "return valid JSON" repair prompt just buys a second
    truncated reply, so fail the sample loudly and let the pass degrade instead.
    """
    if reason in ("max_tokens", "length"):
        raise LLMError(
            f"{label}: response hit the {cap}-token cap and was cut off "
            "mid-JSON; raise the cap in ats.llm or narrow the prompt"
        )


def _anthropic_client(api_key: str):
    import anthropic

    return anthropic.Anthropic(
        api_key=api_key, timeout=anthropic.Timeout(CALL_TIMEOUT, connect=5.0)
    )


def _openai_client(api_key: str):
    import openai

    return openai.OpenAI(
        api_key=api_key, timeout=openai.Timeout(CALL_TIMEOUT, connect=5.0)
    )


def _dispatch(provider: Provider, system: str, user: str, temperature: float) -> str:
    if provider.name == "anthropic":
        client = _anthropic_client(provider.api_key)
        with client.messages.stream(
            model=provider.model,
            max_tokens=ANTHROPIC_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            deadline = time.monotonic() + STREAM_DEADLINE
            for _ in stream:
                if time.monotonic() > deadline:
                    raise LLMError(
                        f"{provider.label}: still streaming after {STREAM_DEADLINE:.0f}s; "
                        "abandoned so it stops billing"
                    )
            response = stream.get_final_message()
        log.info("%s used %s output tokens (stop_reason=%s)", provider.label,
                 response.usage.output_tokens, response.stop_reason)
        _truncated(provider.label, response.stop_reason, ANTHROPIC_MAX_TOKENS)
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )

    if provider.name == "openai":
        client = _openai_client(provider.api_key)
        legacy = bool(LEGACY_OPENAI.match(provider.model))
        request: dict[str, Any] = {
            "model": provider.model,
            "max_tokens" if legacy else "max_completion_tokens": MAX_TOKENS,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if legacy:
            request["temperature"] = temperature
        response = client.chat.completions.create(**request)
        choice = response.choices[0]
        _truncated(provider.label, getattr(choice, "finish_reason", None), MAX_TOKENS)
        return choice.message.content or ""

    raise LLMError(f"unknown provider {provider.name}")
