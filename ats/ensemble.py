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
where output is generated to win a selection. See verify() for the ranking/audit
split that keeps best-of-N honest.
"""
from __future__ import annotations

import concurrent.futures
import logging
import re
from dataclasses import dataclass, field

from .invariants import evaluate, has_metric, vacuous_number
from .models import Rewrite
from .slop import PATTERNS, Scope, _is_protected

log = logging.getLogger("ats.ensemble")

BAND_THRESHOLD = 12.0


@dataclass
class PassResult:
    """One pass's output plus what happened, so degradation is visible not silent."""

    data: list = field(default_factory=list)
    providers_used: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


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


def combine_scores(
    per_provider: dict[str, dict[str, float]],
) -> tuple[dict[str, tuple[float, float, float]], dict]:
    """Average category scores across providers; band them where they disagree.

    Averaging across providers reduces systematic provider bias, which resampling a
    single model cannot. Wide disagreement is information -- it means the resume is
    genuinely ambiguous on that dimension -- so it is shown as a range rather than
    hidden behind a falsely precise midpoint.
    """
    categories: dict[str, list[float]] = {}
    for scores in per_provider.values():
        for name, value in scores.items():
            categories.setdefault(name, []).append(float(value))

    out: dict[str, tuple[float, float, float]] = {}
    disagreements = []
    for name, values in categories.items():
        low, high = min(values), max(values)
        out[name] = (sum(values) / len(values), low, high)
        if high - low >= BAND_THRESHOLD:
            disagreements.append(f"{name}: {low:.0f}-{high:.0f}")
    return out, {"providers": list(per_provider), "disagreements": disagreements}


# --------------------------------------------------------------------------
# Pass 3: best-of-N with a split verifier.
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


def select_rewrite(
    original: str,
    locator: str,
    candidates: list[tuple[str, str, str]],
    margin: float,
) -> tuple[Rewrite | None, dict]:
    """Best-of-N: rank, then audit, then require a real improvement.

    Three gates, and a candidate must pass all of them:
      1. beat the ORIGINAL by `margin` on the ranking set (not merely beat siblings)
      2. not regress on the audit set
      3. be clean of audit problems

    If nothing clears all three, the original is kept. Failing to improve is an
    acceptable outcome; shipping a hacked rewrite is not.
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
