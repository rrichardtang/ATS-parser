"""The three LLM passes and their ensembling.

Pass 1 and 2 are independent and run concurrently. Pass 3 depends on both, so a
rewrite fixes content defects and slop patterns in one edit instead of trading one
for the other.

Every pass degrades on its own: if one fails, the rest of the report still renders.
"""
from __future__ import annotations

import logging

from . import ensemble, prompts
from .llm import LLMError, Provider, call
from .models import Category, Finding, Provenance, Rewrite, Severity
from .sections import Resume

log = logging.getLogger("ats.passes")

MAX_REWRITE_TARGETS = 6

CATEGORY_BY_NAME = {c.value.lower(): c for c in Category}


def _category(name: str) -> Category | None:
    return CATEGORY_BY_NAME.get((name or "").strip().lower())


def content_pass(
    providers: list[Provider],
    resume: Resume,
    full_text: str,
    jd_text: str,
    deterministic: list[Finding],
    samples: int,
    temperature: float,
) -> ensemble.PassResult:
    """Substance, ownership, seniority fit, missing information, category scores."""
    summary = [f"{f.rule_id}: {f.message}" for f in deterministic]
    user = prompts.content_user(resume, full_text, jd_text, summary)

    jobs = []
    for provider in providers:
        for index in range(samples):
            temp = 0.0 if samples == 1 else temperature
            jobs.append(
                lambda p=provider, t=temp: (p.name, call(p, prompts.CONTENT_SYSTEM, user, t))
            )

    raw, errors = ensemble.gather(jobs)
    per_provider: dict[str, dict[str, float]] = {}
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()

    for provider_name, payload in raw:
        scores = {}
        for name, entry in (payload.get("categories") or {}).items():
            category = _category(name)
            if category and isinstance(entry, dict) and "score" in entry:
                try:
                    scores[category.value] = float(entry["score"])
                except (TypeError, ValueError):
                    continue
        if scores:
            existing = per_provider.setdefault(provider_name, {})
            for key, value in scores.items():
                existing[key] = (existing.get(key, value) + value) / 2 if key in existing else value

        for item in payload.get("findings") or []:
            evidence = (item.get("evidence") or "").strip()
            message = (item.get("message") or "").strip()
            if not evidence or not message:
                continue  # unevidenced claims are not checkable
            key = (message.lower()[:60], evidence.lower()[:60])
            if key in seen:
                continue
            seen.add(key)
            category = _category(item.get("category", "")) or Category.RELEVANCE
            findings.append(Finding(
                rule_id="llm/content",
                category=category,
                severity=Severity.MAJOR,
                message=message[:200],
                fix=(item.get("fix") or "").strip()[:200],
                evidence=evidence[:200],
                locator=(item.get("locator") or "").strip()[:40],
                provenance=Provenance.HEURISTIC,
                source=f"llm:{provider_name}",
            ))

    scores, meta = ensemble.combine_scores(per_provider) if per_provider else ({}, {})
    return ensemble.PassResult(
        data=findings,
        providers_used=sorted(per_provider),
        errors=errors,
        meta={"scores": scores, **meta, "samples_per_provider": samples},
    )


def slop_pass(
    providers: list[Provider],
    resume: Resume,
    caught: list[str],
    samples: int,
    vote_k: int,
    temperature: float,
) -> ensemble.PassResult:
    """Named slop patterns beyond regex reach. Never scores AI-likelihood."""
    user = prompts.slop_user(resume, caught)

    jobs = []
    for provider in providers:
        for _ in range(samples):
            temp = 0.0 if samples == 1 else temperature
            jobs.append(
                lambda p=provider, t=temp: (p.name, call(p, prompts.SLOP_SYSTEM, user, t))
            )

    raw, errors = ensemble.gather(jobs)
    per_provider: dict[str, list[list[dict]]] = {}
    for provider_name, payload in raw:
        items = [i for i in (payload.get("findings") or []) if isinstance(i, dict)]
        per_provider.setdefault(provider_name, []).append(items)

    combined, meta = ensemble.combine_slop(per_provider, vote_k) if per_provider else ([], {})
    resume_text = " ".join([resume.summary] + [b for _, b in resume.bullets])
    combined = ensemble.filter_slop(combined, resume_text)

    locator_by_text = {
        " ".join(text.split()).lower(): loc for loc, text in resume.bullets
    }

    findings = []
    for item in combined:
        quote = item["quoted_line"].strip()
        locator = "summary"
        needle = " ".join(quote.split()).lower()
        for text, loc in locator_by_text.items():
            if needle in text:
                locator = loc
                break
        findings.append(Finding(
            rule_id=f"slop/{(item.get('pattern') or 'pattern').strip().lower().replace(' ', '-')[:40]}",
            category=Category.WRITING,
            severity=Severity.MINOR,
            message=f"{item.get('pattern', 'slop pattern')}: “{quote[:90]}”",
            fix=(item.get("fix") or "Rewrite plainly.")[:160],
            evidence=quote[:200],
            locator=locator,
            provenance=Provenance.HEURISTIC,
            confidence=item.get("confidence", "medium"),
            source="llm:" + "+".join(item.get("providers", [])),
        ))

    return ensemble.PassResult(
        data=findings, providers_used=sorted(per_provider), errors=errors,
        meta={**meta, "samples_per_provider": samples},
    )


def rewrite_pass(
    providers: list[Provider],
    resume: Resume,
    findings: list[Finding],
    candidates_per_provider: int,
    margin: float,
    temperature: float,
) -> ensemble.PassResult:
    """Best-of-N over both providers, selected by the split verifier in ensemble."""
    by_locator: dict[str, list[Finding]] = {}
    for finding in findings:
        if finding.locator.startswith("exp["):
            by_locator.setdefault(finding.locator, []).append(finding)

    bullet_text = dict(resume.bullets)
    ranked = sorted(
        by_locator.items(),
        key=lambda kv: -sum(f.points or 1 for f in kv[1]),
    )[:MAX_REWRITE_TARGETS]

    targets = [
        {
            "locator": locator,
            "bullet": bullet_text.get(locator, ""),
            "defects": [f"{f.message} -> {f.fix}" for f in items][:5],
        }
        for locator, items in ranked
        if bullet_text.get(locator)
    ]
    if not targets:
        return ensemble.PassResult(meta={"reason": "no bullets needed rewriting"})

    user = prompts.rewrite_user(targets)
    jobs = []
    for provider in providers:
        for _ in range(candidates_per_provider):
            jobs.append(
                lambda p=provider: (p.name, call(p, prompts.REWRITE_SYSTEM, user, temperature))
            )

    raw, errors = ensemble.gather(jobs)

    by_target: dict[str, list[tuple[str, str, str]]] = {}
    for provider_name, payload in raw:
        for item in payload.get("rewrites") or []:
            locator = (item.get("locator") or "").strip()
            text = (item.get("rewritten") or "").strip()
            if locator and text:
                by_target.setdefault(locator, []).append(
                    (text, (item.get("what_changed") or "").strip()[:120], provider_name)
                )

    rewrites: list[Rewrite] = []
    selection_meta = []
    for target in targets:
        locator = target["locator"]
        chosen, meta = ensemble.select_rewrite(
            target["bullet"], locator, by_target.get(locator, []), margin
        )
        selection_meta.append(meta)
        if chosen:
            rewrites.append(chosen)

    hacks = [m for m in selection_meta if m.get("hack_detected")]
    return ensemble.PassResult(
        data=rewrites,
        providers_used=sorted({p for _, payload in raw for p in [payload and ""]} or set()),
        errors=errors,
        meta={
            "selections": selection_meta,
            "hack_detections": len(hacks),
            "candidates_per_provider": candidates_per_provider,
        },
    )
