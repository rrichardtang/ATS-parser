"""Claude's half of an agreement run through the Message Batches API.

Half the price of live calls, for results that arrive within hours instead of
minutes -- the trade a test run wants. Each request is the one a live content call
would stream (`llm.anthropic_params`), and each reply is read the way a live one is
(`llm.anthropic_text`), so a batched judgement is the same object a live run records.
The one difference: an unparseable reply is recorded as an error, with no repair call.
"""
from __future__ import annotations

import json
from typing import Iterable

from . import llm, passes
from .agreement import HarnessRun, content_prompt
from .llm import LLMError, Provider
from .sections import parse

NOTE = ("Claude's replies came through the Message Batches API: an unparseable reply "
        "is recorded as an error, with no JSON repair call as a live run makes.")


def custom_id(document: int, sample: int) -> str:
    """Positions in the saved run's `resumes`, never in the results stream."""
    return f"doc{document}-s{sample}"


def parse_custom_id(value: str) -> tuple[int, int]:
    document, sample = value.removeprefix("doc").split("-s")
    return int(document), int(sample)


def requests(provider: Provider, prepared: list, samples: int) -> list:
    """One batch request per (document, sample), skipping what cannot be judged."""
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    made = []
    for document, (run, resume, text) in enumerate(prepared):
        if run.skipped:
            continue
        system, user = content_prompt(run, resume, text)
        params = MessageCreateParamsNonStreaming(**llm.anthropic_params(provider, system, user))
        made += [Request(custom_id=custom_id(document, sample), params=params)
                 for sample in range(samples)]
    return made


def _payload(provider: Provider, outcome) -> dict:
    if outcome.type != "succeeded":
        detail = f" ({outcome.error})" if outcome.type == "errored" else ""
        raise LLMError(f"{provider.label}: batch request {outcome.type}{detail}")
    raw = llm.anthropic_text(provider.label, outcome.message)
    try:
        return llm.extract_json(raw)
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"{provider.label}: unparseable JSON, not repaired in batch mode ({exc})"
        ) from exc


def merge(run: HarnessRun, provider: Provider, results: Iterable, texts: list[str]) -> HarnessRun:
    """Add each batch result to the saved run as a judgement or a recorded error.

    `texts` is the text each document was submitted with, saved at submit time:
    parsing it again here (rather than the document's path) means a `pytest` run
    or any other edit to the file on disk between submit and collect cannot
    change what a batched judgement is scored against.
    """
    samples = run.meta.get("samples_per_provider", 0)
    expected = {custom_id(document, sample)
                for document, r in enumerate(run.resumes) if not r.skipped
                for sample in range(samples)}
    seen = set()
    resumes = {}
    for result in results:
        seen.add(result.custom_id)
        document, sample = parse_custom_id(result.custom_id)
        target = run.resumes[document]
        try:
            payload = _payload(provider, result.result)
        except LLMError as exc:
            target.errors.append(str(exc))
            continue
        if document not in resumes:
            resumes[document] = parse(texts[document])
        target.judgments.append(
            passes.content_judgment(provider.name, sample, payload, resumes[document])
        )
    for missing in expected - seen:
        document, _ = parse_custom_id(missing)
        run.resumes[document].errors.append(
            f"{provider.label}: batch request {missing} returned no result"
        )
    return run
