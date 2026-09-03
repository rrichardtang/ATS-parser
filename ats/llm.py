"""Provider abstraction. Both branches return the same JSON shape so downstream
code is provider-agnostic and results are directly comparable for ensembling.

Keys are read from the request or the environment, never persisted, never logged.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("ats.llm")

ANTHROPIC_MODEL = "claude-sonnet-5"
OPENAI_MODEL = "gpt-5.6-luna"

# Sized for a whole pass of findings/rewrites. Too small and the model is cut off
# mid-object, which reads downstream as "unparseable JSON" -- a truncation bug
# wearing a parse bug's clothes, so it must not be tuned down casually.
MAX_TOKENS = 16000

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


def _truncated(label: str, reason: str | None) -> None:
    """A response cut off at the token cap is a truncation failure, not a parse one.

    Retrying it with a "return valid JSON" repair prompt just buys a second
    truncated reply, so fail the sample loudly and let the pass degrade instead.
    """
    if reason in ("max_tokens", "length"):
        raise LLMError(
            f"{label}: response hit the {MAX_TOKENS}-token cap and was cut off "
            "mid-JSON; raise ats.llm.MAX_TOKENS or narrow the prompt"
        )


def _dispatch(provider: Provider, system: str, user: str, temperature: float) -> str:
    if provider.name == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=provider.api_key)
        response = client.messages.create(
            model=provider.model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        _truncated(provider.label, getattr(response, "stop_reason", None))
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )

    if provider.name == "openai":
        import openai

        client = openai.OpenAI(api_key=provider.api_key)
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
        _truncated(provider.label, getattr(choice, "finish_reason", None))
        return choice.message.content or ""

    raise LLMError(f"unknown provider {provider.name}")
