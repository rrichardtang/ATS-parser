"""Provider abstraction. Both branches return the same JSON shape so downstream
code is provider-agnostic and results are directly comparable for ensembling.

Keys are read from the request or the environment, never persisted, never logged.
"""
from __future__ import annotations

import functools
import inspect
import json
import logging
import os
import re
import threading
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("ats.llm")

ANTHROPIC_MODEL = "claude-sonnet-5"
OPENAI_MODEL = "gpt-5.6-luna"

# Sized for a whole pass of findings/rewrites. Too small and the model is cut off
# mid-object, which reads downstream as "unparseable JSON" -- a truncation bug
# wearing a parse bug's clothes, so it must not be tuned down casually.
MAX_TOKENS = 16000

# Sampling parameters (temperature/top_p/top_k) were removed on the newest Claude
# models, and the 1.x SDK dropped `temperature` from Messages.create() outright --
# so passing it raises TypeError before any HTTP request is made. Older families on
# an older SDK still take it; _accepts() below is what tells the two apart.
NO_SAMPLING_ANTHROPIC = re.compile(
    r"^claude-(?:fable-5|mythos-5|opus-5|opus-4-7|opus-4-8|sonnet-5)\b"
)
# OpenAI renamed max_tokens -> max_completion_tokens and fixed temperature at its
# default on everything after the gpt-4 generation. Both are 400s from the API,
# not signature errors, so they can only be avoided by spelling the request right.
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


# Parameters a model has already rejected, keyed by provider label and learned the
# first time it happens: {"max_tokens": "max_completion_tokens"} renames, None drops.
# Without this every concurrent call in a pass re-discovers the same rejection and
# pays an extra round trip for it.
_LEARNED: dict[str, dict[str, str | None]] = {}
_LEARNED_LOCK = threading.Lock()

_UNEXPECTED_KWARG = re.compile(r"unexpected keyword argument '([^']+)'")
_USE_INSTEAD = re.compile(r"'([^']+)' is not supported with this model\. Use '([^']+)' instead")
_UNSUPPORTED = re.compile(r"[Uu]nsupported (?:parameter|value): '([^']+)'")


def _rejection(message: str) -> tuple[str, str | None] | None:
    """The parameter a failure blames, and what to send instead (None = drop it)."""
    rename = _USE_INSTEAD.search(message)
    if rename:
        return rename.group(1), rename.group(2)
    dropped = _UNEXPECTED_KWARG.search(message) or _UNSUPPORTED.search(message)
    if dropped:
        return dropped.group(1), None
    return None


def _respell(kwargs: dict, label: str) -> dict:
    for param, replacement in _LEARNED.get(label, {}).items():
        if param in kwargs:
            value = kwargs.pop(param)
            if replacement:
                kwargs[replacement] = value
    return kwargs


def _create(fn, kwargs: dict, label: str):
    """Call fn(**kwargs), adapting to a model that rejects a parameter we send.

    Two shapes of rejection are handled: the installed SDK dropping a kwarg from
    its signature (a TypeError, raised before any request), and the provider
    answering 400 because the parameter was renamed or pinned to its default for
    this model. Both are recoverable by re-spelling the request, and what we learn
    is remembered per model so the next call gets it right the first time. Logged
    once, so a silent change in sampling behaviour is still visible.
    """
    kwargs = _respell(dict(kwargs), label)
    for _ in range(len(kwargs)):
        try:
            return fn(**kwargs)
        except Exception as exc:  # noqa: BLE001 - re-raised unless it names a parameter
            rejection = _rejection(str(exc))
            if rejection is None or rejection[0] not in kwargs:
                raise
            param, replacement = rejection
            log.warning(
                "%s rejected '%s' (%s) -- %s",
                label, param, exc,
                f"retrying as '{replacement}'" if replacement else "retrying without it",
            )
            with _LEARNED_LOCK:
                _LEARNED.setdefault(label, {})[param] = replacement
            kwargs = _respell(kwargs, label)
    raise LLMError(f"{label}: no parameter spelling this model accepts")


@functools.lru_cache(maxsize=8)
def _accepts(fn, param: str) -> bool:
    """Whether the installed SDK's signature still has this parameter."""
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return True
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()):
        return True
    return param in signature.parameters


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
        request: dict[str, Any] = dict(
            model=provider.model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if (not NO_SAMPLING_ANTHROPIC.match(provider.model)
                and _accepts(type(client.messages).create, "temperature")):
            request["temperature"] = temperature
        response = _create(client.messages.create, request, provider.label)
        _truncated(provider.label, getattr(response, "stop_reason", None))
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )

    if provider.name == "openai":
        import openai

        client = openai.OpenAI(api_key=provider.api_key)
        legacy = bool(LEGACY_OPENAI.match(provider.model))
        request = {
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
        response = _create(client.chat.completions.create, request, provider.label)
        choice = response.choices[0]
        _truncated(provider.label, getattr(choice, "finish_reason", None))
        return choice.message.content or ""

    raise LLMError(f"unknown provider {provider.name}")
