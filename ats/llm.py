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

MAX_TOKENS = 4000


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
        return _extract_json(raw)


def _create(fn, kwargs: dict, label: str):
    """Call fn(**kwargs); if the installed SDK's signature has dropped a param we
    pass (observed: newer anthropic clients rejecting `temperature`), drop it and
    retry once rather than degrading the whole pass. Logged so it's visible in the
    terminal instead of silently changing sampling behavior."""
    try:
        return fn(**kwargs)
    except TypeError as exc:
        message = str(exc)
        for key in list(kwargs):
            if key in message and "unexpected keyword argument" in message:
                log.warning(
                    "%s: SDK rejected '%s' (%s) -- retrying without it",
                    label, key, message,
                )
                kwargs = {k: v for k, v in kwargs.items() if k != key}
                return _create(fn, kwargs, label)
        raise


def _dispatch(provider: Provider, system: str, user: str, temperature: float) -> str:
    if provider.name == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=provider.api_key)
        response = _create(client.messages.create, dict(
            model=provider.model,
            max_tokens=MAX_TOKENS,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        ), provider.label)
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )

    if provider.name == "openai":
        import openai

        client = openai.OpenAI(api_key=provider.api_key)
        response = _create(client.chat.completions.create, dict(
            model=provider.model,
            max_tokens=MAX_TOKENS,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        ), provider.label)
        return response.choices[0].message.content or ""

    raise LLMError(f"unknown provider {provider.name}")
