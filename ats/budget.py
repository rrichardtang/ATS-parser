"""The worst-case dollar cost of an agreement run, checked before anything is sent.

Worst case means every call writes the prompt cache and none reads it, every reply
runs to its token cap, and every live call needs its JSON-repair retry.
"""
from __future__ import annotations

import math

from . import llm
from .llm import Provider

# Claude Sonnet 5, $ per million tokens (Anthropic pricing page, 2026-09-26): $2 in,
# $10 out; the Message Batches API is 50% off both; a 5-minute cache write is 1.25x in.
CLAUDE_INPUT = 2.00
CLAUDE_OUTPUT = 10.00
CACHE_WRITE = 1.25
BATCH_DISCOUNT = 0.5

# English runs about 4 characters a token, so dividing by 3 overestimates.
CHARS_PER_TOKEN = 3

# `llm.call` may send a second, JSON-repair call per sample; a batch request makes none.
# Claude streams, and its SDK retries only before generation starts, so a live Claude
# sample is at most these two generations.
LIVE_ATTEMPTS = 2


class PriceUnknown(ValueError):
    pass


def input_tokens(system: str, user: str) -> int:
    return math.ceil(len(system + user) / CHARS_PER_TOKEN)


def _rates(provider: Provider, batch: bool, openai_price: tuple[float, float] | None):
    """($/MTok in, $/MTok out, output cap, attempts per sample) for one provider."""
    if provider.name == "anthropic":
        discount = BATCH_DISCOUNT if batch else 1.0
        return (CLAUDE_INPUT * CACHE_WRITE * discount, CLAUDE_OUTPUT * discount,
                provider.anthropic_max_tokens, 1 if batch else LIVE_ATTEMPTS)
    if openai_price is None:
        raise PriceUnknown(
            f"{provider.label}'s price is not known here: pass --openai-price IN,OUT "
            "($ per million tokens) or --claude-only."
        )
    import openai

    # OpenAI does not stream: a reply slower than `llm.CALL_TIMEOUT` times out and the
    # SDK resends it (default max_retries), and each abandoned generation may be billed.
    attempts = LIVE_ATTEMPTS * (1 + openai.DEFAULT_MAX_RETRIES)
    return (*openai_price, llm.MAX_TOKENS, attempts)


def worst_case(providers: list[Provider], prompt_tokens: list[int], samples: int,
               batch: bool, openai_price: tuple[float, float] | None) -> dict[str, float]:
    """Dollars per provider label; `prompt_tokens` has one entry per judged document.

    Raises ValueError on a negative sample count or price, or a cap below 1: any of
    them makes a negative cost that would hide another provider's real one.
    """
    if samples < 0:
        raise ValueError(f"samples must not be negative, got {samples}")
    costs = {}
    for provider in providers:
        in_rate, out_rate, cap, attempts = _rates(provider, batch, openai_price)
        if cap < 1 or in_rate < 0 or out_rate < 0:
            raise ValueError(f"{provider.label}: cap {cap} or price "
                             f"({in_rate}, {out_rate}) out of range")
        per_call = sum(tokens * in_rate + cap * out_rate for tokens in prompt_tokens)
        costs[provider.label] = samples * attempts * per_call / 1e6
    return costs


def verdict(providers: list[Provider], prompt_tokens: list[int], samples: int,
            batch: bool, openai_price: tuple[float, float] | None,
            budget: float) -> tuple[bool, str]:
    """Whether the run fits `budget`, and a line or two saying so."""
    try:
        costs = worst_case(providers, prompt_tokens, samples, batch, openai_price)
    except PriceUnknown as exc:
        return False, str(exc)
    total = sum(costs.values())
    breakdown = ", ".join(f"{label} ${cost:.2f}" for label, cost in costs.items())
    summary = f"Worst case ${total:.2f} against a ${budget:.2f} budget ({breakdown or 'no calls'})"
    if total <= budget:
        return True, summary + ": fits."
    return False, summary + ": over.\n" + _what_fits(
        providers, len(prompt_tokens), samples, batch, total, budget)


def _what_fits(providers, documents, samples, batch, total, budget) -> str:
    """The largest Claude output cap under which the same run would fit."""
    claude = next((p for p in providers if p.name == "anthropic"), None)
    fitting = 0
    if claude and documents:
        _, out_rate, cap, attempts = _rates(claude, batch, None)
        per_cap_token = samples * attempts * documents * out_rate / 1e6
        fitting = math.floor((budget - total) / per_cap_token) + cap
    if fitting < 1:
        return "No --max-tokens fits: judge fewer documents (--docs) or take fewer --samples."
    return f"The largest --max-tokens that fits these documents is {fitting}."
