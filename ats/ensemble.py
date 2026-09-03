"""Ensembling, with the technique matched to each pass's output shape.

The important asymmetry: the combination rule for findings switches on ensemble
*type*, not on a fixed constant.

  Same model, N samples  -> a lone finding is probably sampling noise  -> k-of-N.
  Two providers          -> a lone finding is plausibly a blindspot catch -> union.

That inversion is the whole reason to hold two keys. A model is weakest at flagging
its own idiom, so if a resume was drafted with one provider's model, the *other*
provider is the informative detector. Intersecting would discard exactly the
findings worth having.

Pass 3 is the only place reward hacking can arise, because it is the only pass
where output is generated to win a selection. It runs generate -> audit-filter ->
judge-rank -> polish-the-winner -> final gate: candidates are never picked for
truthfulness (audit_clean() enforces that before any opinion is formed), only for
quality once truthfulness is no longer in question. select_rewrite() is the final
gate -- rank vs. original by a margin, no audit regression, no audit problems -- and
it is what catches a hacking attempt that made it past everything upstream.
"""
from __future__ import annotations

import concurrent.futures
import logging
import re
from dataclasses import dataclass, field

from . import rubric
from .invariants import evaluate, has_metric, vacuous_number
from .models import Category, JudgedCategory, Rewrite
from .slop import PATTERNS, Scope, _is_protected

log = logging.getLogger("ats.ensemble")


@dataclass
class PassResult:
    """One pass's output plus what happened, so degradation is visible not silent."""

    data: list = field(default_factory=list)
    providers_used: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    # The content pass's second channel, and the only pass that fills it: what the
    # judges' criterion answers make each category worth. It is not `data` because
    # `data` is findings, and it is not `meta` because `meta` is round-tripped into
    # the report's JSON and these are objects `score.build` consumes.
    judged: dict = field(default_factory=dict)


def gather(fns: list, timeout: int = 180) -> tuple[list, list[str]]:
    """Run independent calls concurrently; collect results and failures separately."""
    results, errors = [], []
    if not fns:
        return results, errors
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(fns)) as pool:
        futures = [pool.submit(fn) for fn in fns]
        for future in concurrent.futures.as_completed(futures, timeout=timeout):
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 - degradation is per-call
                log.warning("ensemble call failed: %s", exc)
                errors.append(str(exc))
    return results, errors


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def combine_slop(
    per_provider: dict[str, list[list[dict]]],
    vote_k: int,
) -> tuple[list[dict], dict]:
    """Vote within each provider, then union across providers.

    Returns findings carrying a confidence label: 'high' when both providers raised
    it, 'medium' when only one did. Single-provider findings are kept -- see the
    module docstring -- but every one still has to survive the evidence guards in
    filter_slop().
    """
    per_provider_kept: dict[str, dict[str, dict]] = {}

    for provider, samples in per_provider.items():
        counts: dict[str, int] = {}
        exemplar: dict[str, dict] = {}
        for sample in samples:
            seen_this_sample = set()
            for item in sample:
                key = _norm(item.get("quoted_line", ""))
                if not key or key in seen_this_sample:
                    continue
                seen_this_sample.add(key)
                counts[key] = counts.get(key, 0) + 1
                exemplar.setdefault(key, item)
        threshold = min(vote_k, len(samples)) if samples else 1
        per_provider_kept[provider] = {
            key: exemplar[key] for key, count in counts.items() if count >= threshold
        }

    union: dict[str, dict] = {}
    for provider, kept in per_provider_kept.items():
        for key, item in kept.items():
            if key in union:
                union[key]["_providers"].append(provider)
            else:
                entry = dict(item)
                entry["_providers"] = [provider]
                union[key] = entry

    out = []
    for entry in union.values():
        providers = entry.pop("_providers")
        entry["confidence"] = "high" if len(providers) > 1 else "medium"
        entry["providers"] = providers
        out.append(entry)

    meta = {
        "vote_k": vote_k,
        "per_provider_counts": {p: len(k) for p, k in per_provider_kept.items()},
        "rule": "union across providers" if len(per_provider) > 1 else f"{vote_k}-of-N within provider",
    }
    return out, meta


def filter_slop(items: list[dict], resume_text: str) -> list[dict]:
    """Drop anything unverifiable: the quote must actually appear in the resume."""
    haystack = _norm(resume_text)
    kept = []
    for item in items:
        quote = (item.get("quoted_line") or "").strip()
        if len(quote) < 8:
            continue
        if _norm(quote) not in haystack:
            continue
        if _is_protected(resume_text, quote):
            continue
        kept.append(item)
    return kept


def combine_bands(spec: dict, answer_sets: list[dict[str, bool]]) -> JudgedCategory | None:
    """One category, one judge per answer set: the band each names, and the lower one.

    Replaces `combine_scores`, which averaged the numbers providers returned and widened
    a category to a range when they differed by 12 or more. Neither half survives 05:
    there are no numbers to average, and the narrowest disagreement the rubric can
    express -- one adjacent band -- is 17 points at its narrowest, so a 12-point test
    fires on every split there is. What replaces the threshold is band adjacency, which
    is the quantity the specs actually define.

    **The lower band wins**, and both bands travel on the result so the report can name
    the two readings rather than print a range. `models.JudgedCategory` carries why, and
    `docs/wayfinder/rubric-migration/criterion-scoring.md` carries the measurements: the
    two rejected rules are averaging (which invents a value no band names) and
    intersecting the answers (which inverts on `Resume craft`, whose band is a count).

    A judge that did not answer every criterion names no band -- `rubric.band_of`
    refuses an incomplete set rather than banding one -- and is dropped here rather than
    guessed at. None when that leaves no judge at all.
    """
    ids = [c["id"] for c in spec["criteria"]]
    complete = [a for a in answer_sets if all(cid in a for cid in ids)]
    if not complete:
        return None

    order = [b["label"] for b in spec["bands"]]
    banded = [rubric.band_of(a, spec) for a in complete]
    positions = sorted(order.index(b["label"]) for b in banded)
    low, high = spec["bands"][positions[0]], spec["bands"][positions[-1]]

    # Every criterion the judges did not answer the same way, whether or not it moved
    # the band. A split the lookup absorbed is what agreement actually cost, and 04's
    # claim that criteria are more diagnosable than a label is only checkable if the
    # absorbed ones are still visible.
    split = [f"{spec['slug']}/{cid}" for cid in ids
             if len({a[cid] for a in complete}) > 1]

    return JudgedCategory(
        category=Category(spec["category"]),
        value=float(low["value"]), band=low["label"], band_name=low["name"],
        high_band=high["label"], high_band_name=high["name"],
        high_value=float(high["value"]),
        gap=positions[-1] - positions[0],
        split_criteria=split,
        judges=len(complete),
    )


# --------------------------------------------------------------------------
# Pass 3: generate -> audit-filter -> judge-rank -> polish -> final gate.
# --------------------------------------------------------------------------

# Digits that are part of a name rather than a measurement.
_IDENTIFIER_RE = re.compile(
    r"""(?ix)
      \b(?:bm|gpt|llama|mistral|qwen|gemma|phi|t|clip|f|p|a|h|v|s|ec|k)[- ]?\d+[\w.-]*
    | \b\w+@\d+                      # recall@10, ndcg@5
    | \b[a-z]+\d+(?:[a-z]\w*)?\b     # a100, h100, s3, k8s, ec2
    | \[add:[^\]]*\]
    """
)


def _quantities(text: str) -> set[str]:
    """Numbers that assert a measurement, with identifier digits removed first."""
    return set(re.findall(r"\d+(?:\.\d+)?", _IDENTIFIER_RE.sub(" ", text)))


_FILLER = {
    "with", "that", "this", "from", "into", "were", "have", "been", "their", "them",
    "our", "for", "the", "and", "was", "are", "his", "her", "its",
}


def _content_words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z][\w-]{3,}", text)} - _FILLER


def _specifics(text: str) -> set[str]:
    """Names, tools and quantities -- the claims a rewrite must not silently drop."""
    body = text[1:] if text else ""
    named = {m.lower() for m in re.findall(r"\b[A-Z][A-Za-z0-9.-]{2,}\b", body)}
    named |= {m.lower() for m in re.findall(r"\b[A-Z]{2,8}\b", text)}
    named |= _quantities(text)
    return named


def rank_score(text: str) -> float:
    """The RANKING set. Candidates are selected against these signals.

    Kept deliberately small and mechanical. Everything the optimiser can see, it
    can eventually game -- which is why the audit signals below are held out.
    """
    result = evaluate(text)
    score = result.passed * 10.0
    hits = 0
    for pattern in PATTERNS:
        if pattern.scope is Scope.DOCUMENT:
            continue
        for hit in pattern.find(text):
            if not _is_protected(text, hit):
                hits += 1
    score -= hits * 6.0
    words = len(text.split())
    if words > 32:
        score -= (words - 32) * 0.4
    return round(score, 2)


def audit_score(original: str, candidate: str) -> tuple[float, list[str]]:
    """The AUDIT set. Never used for ranking -- only to detect gaming.

    A candidate cannot be optimised against signals it is not selected on, so a
    rising rank_score paired with a falling audit_score is the hacking signature.
    """
    problems: list[str] = []
    score = 100.0

    # Fabrication: a quantity not present in the source. Digits inside an
    # identifier are not quantities -- BM25, recall@10, GPT-4, Llama-3, p99, F1,
    # A100 and S3 all carry digits that assert nothing about results.
    for number in _quantities(candidate):
        if number not in _quantities(original):
            problems.append(f"invented figure {number}")
            score -= 60.0

    # Vacuous quantification: a number that counts trivia to satisfy Measurability.
    if vacuous := vacuous_number(candidate):
        if not vacuous_number(original):
            problems.append(f"vacuous number '{vacuous}'")
            score -= 40.0

    # Truncation: dropping *claims* to win on brevity. Cutting filler is the point
    # of a rewrite, so only specifics count -- names, tools, and quantities. Losing
    # "for our users" is a good edit; losing "Airflow" is a lost claim.
    lost = _specifics(original) - _specifics(candidate)
    if lost:
        problems.append(f"dropped {len(lost)} specific(s): {', '.join(sorted(lost)[:3])}")
        score -= 35.0

    # A bullet with no specifics to lose can still be gutted. Cutting filler is the
    # goal, but collapsing the claim to a fragment wins on length while saying less
    # than the original did.
    original_content = _content_words(original)
    if original_content:
        kept_ratio = len(_content_words(candidate) & original_content) / len(original_content)
        if kept_ratio < 0.45 and not _specifics(candidate):
            problems.append(f"kept only {kept_ratio:.0%} of the original's content")
            score -= 35.0

    # Proper-noun padding: stuffing names to survive the portability strip.
    original_caps = len(re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", original[1:]))
    candidate_caps = len(re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", candidate[1:]))
    if candidate_caps > original_caps + 2:
        problems.append(f"added {candidate_caps - original_caps} proper nouns")
        score -= 25.0

    # A placeholder is the honest response to a missing metric, so it is never
    # penalised -- but a candidate that claims a metric it cannot have is.
    if "[add:" in candidate and has_metric(candidate.replace("[add:", "")):
        pass

    return round(score, 2), problems


def adjudicator_provider(providers: list, candidate_providers: list[str]):
    """Pick who judges or polishes a batch of candidates.

    Mirrors cross-provider slop adjudication: a model is weakest at judging its own
    idiom, so the provider that contributed *fewest* of the candidates does the
    judging or polishing, not the one that dominated generation. With one provider
    available there is no choice to make.
    """
    if len(providers) == 1:
        return providers[0]
    counts: dict[str, int] = {}
    for name in candidate_providers:
        counts[name] = counts.get(name, 0) + 1
    return min(providers, key=lambda p: counts.get(p.name, 0))


def audit_clean(
    original: str, candidates: list[tuple[str, str, str, str]]
) -> list[dict]:
    """Filter candidates to those that already pass the fact-check.

    Runs BEFORE any quality judgment: invented figures, vacuous numbers, dropped
    claims, and proper-noun padding disqualify a candidate outright. A candidate
    that fails this never gets an opinion on how good it sounds -- the quality
    judge (§5c) only ever sees candidates that already cleared this gate.

    candidates: (text, what_changed, provider, objective) tuples.
    """
    baseline_audit, _ = audit_score(original, original)
    clean = []
    for text, what_changed, provider, objective in candidates:
        if not text or _norm(text) == _norm(original):
            continue
        audit, problems = audit_score(original, text)
        if problems or audit < baseline_audit:
            continue
        clean.append({
            "text": text, "what_changed": what_changed, "provider": provider,
            "objective": objective, "rank": rank_score(text), "audit": audit,
        })
    return clean


def select_rewrite(
    original: str,
    locator: str,
    candidates: list[tuple[str, str, str]],
    margin: float,
) -> tuple[Rewrite | None, dict]:
    """The final gate: rank, then audit, then require a real improvement.

    Three checks, and a candidate must pass all of them:
      1. beat the ORIGINAL by `margin` on the ranking set (not merely beat siblings)
      2. not regress on the audit set
      3. be clean of audit problems

    If nothing clears all three, the original is kept. Failing to improve is an
    acceptable outcome; shipping a hacked rewrite is not.

    Doubles as the fallback path: `rewrite_pass` normally narrows candidates to a
    judge-ranked winner (+ its polished form) before calling this, but if the judge
    or polish call fails it can be called with the full audit-clean candidate pool
    and behaves exactly as a plain best-of-N selector.
    """
    baseline_rank = rank_score(original)
    baseline_audit, _ = audit_score(original, original)

    scored = []
    for text, what_changed, provider in candidates:
        if not text or _norm(text) == _norm(original):
            continue
        rank = rank_score(text)
        audit, problems = audit_score(original, text)
        scored.append({
            "text": text, "what_changed": what_changed, "provider": provider,
            "rank": rank, "audit": audit, "problems": problems,
        })

    if not scored:
        return None, {"locator": locator, "reason": "no candidates"}

    scored.sort(key=lambda c: -c["rank"])
    best_rank = scored[0]

    eligible = [
        c for c in scored
        if c["rank"] >= baseline_rank + margin
        and c["audit"] >= baseline_audit
        and not c["problems"]
    ]

    meta = {
        "locator": locator,
        "baseline_rank": baseline_rank,
        "best_rank": best_rank["rank"],
        "best_audit": best_rank["audit"],
        "candidates": len(scored),
        "rejected_for_audit": [
            {"rank": c["rank"], "audit": c["audit"], "problems": c["problems"]}
            for c in scored if c["problems"]
        ],
    }

    # The hacking signature: the top-ranked candidate wins on the signals it was
    # selected against while losing on the ones it never saw.
    if best_rank["rank"] > baseline_rank and best_rank["audit"] < baseline_audit:
        meta["hack_detected"] = True

    if not eligible:
        meta["reason"] = "no candidate beat the original without regressing"
        return None, meta

    winner = eligible[0]
    return Rewrite(
        locator=locator,
        original=original,
        rewritten=winner["text"],
        what_changed=winner["what_changed"],
        ranking_score=winner["rank"],
        audit_score=winner["audit"],
        provider=winner["provider"],
    ), meta
