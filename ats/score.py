"""Turns findings into a score you can argue with.

Two commitments enforced here rather than merely intended:

1. No hard gates. A single non-fraud finding may not cost more than its category's
   weight. Public checkers wire one binary check to dominate the composite -- a real
   observed case scored 22/100 for a missing phone number, which measures one field
   and reports it as a verdict. Severity is proportional to the fix.

2. Every point is traceable. The ledger lists each deduction with the finding that
   caused it, and the rows sum to the composite. A score whose derivation is hidden
   cannot be disputed, which is exactly why scores from different tools diverge with
   no way to reconcile them.
"""
from __future__ import annotations

import functools

from . import config, rubric
from .models import (
    JUDGED_CATEGORIES,
    Category,
    CategoryScore,
    Finding,
    Gate,
    LedgerRow,
    Report,
    Severity,
)

@functools.lru_cache(maxsize=1)
def rule_shares() -> dict[Category, float]:
    """How much of a judged category's score the deterministic channel carries.

    Per-category data, read from the category's own spec in `ats/criteria/`, not a set
    literal here: 07 §5 gives `Production ownership` 0.4, `Evaluation rigour` 0.4,
    `Resume craft` 0.7, and **0** to `Agentic systems` and `AI-assisted coding
    fluency`.

    Those two zeroes are load-bearing rather than tidy. `deductions` below starts every
    category at 0.0, so a category no rule ever deducts from holds `rule_score = 100.0`
    permanently -- not a 40% rule channel but a constant, and one that would floor the
    category at 40 whatever a judge answered. Hence the invariant, which
    `tests/test_scoring.py` checks against the rule modules themselves:

        rule_share > 0 requires at least one deducting rule in the category.
    """
    return {Category(name): float(rubric.load_spec(slug)["rule_share"])
            for name, slug in rubric.slug_by_category().items()}


FRAUD_RULES = {"parse/hidden-text"}
# When there is no text layer, nothing downstream ran -- so every other category
# sits at its default 100 and the composite comes out near-perfect for a file no
# ATS can read at all. Reporting that as a score would be worse than useless, so
# an unreadable document is capped and explicitly marked unassessed.
UNREADABLE_RULES = {"parse/no-text-layer"}
UNREADABLE_CAP = 15.0
# Beyond this the rail scrolls past the composite, which is the one number the
# reader came for.
LEDGER_VISIBLE_ROWS = 11
GRADES = [(90, "A"), (80, "B"), (70, "C"), (60, "D"), (0, "F")]


def _truncate(text: str, limit: int) -> str:
    """Trim at a word boundary -- a label cut mid-word reads as a rendering bug."""
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-") + "\u2026"


def _grade(value: float) -> str:
    for threshold, letter in GRADES:
        if value >= threshold:
            return letter
    return "F"


def _cost(finding: Finding, weights: dict[Category, float], points: dict[Severity, float]) -> float:
    """Severity cost, clamped so no single non-fraud finding can dominate.

    The clamp is the anti-hard-gate invariant: a finding's cost is capped at its
    category's weight, so a missing phone number costs a few points rather than
    most of the score. That cap is applied AFTER any JD-derived dimension
    multiplier (config.dimension_multiplier), so a rule a user's target postings
    emphasize heavily still can't move the composite by more than its category's
    weight -- amplifying by target-role signal never reopens the hard-gate risk
    this clamp exists to close.
    """
    raw = points[finding.severity] * config.dimension_multiplier(finding.rule_id)
    if finding.rule_id in FRAUD_RULES:
        return raw
    ceiling = weights[finding.category] * config.scoring()["max_single_finding_share"]
    return min(raw, ceiling)


def build(
    findings: list[Finding],
    llm_categories: dict[Category, tuple[float, float, float]] | None = None,
    partial: bool = False,
    notes: list[str] | None = None,
    run_meta: dict | None = None,
) -> Report:
    """llm_categories maps a category to (mean, low, high) from the content judge."""
    weights = config.category_weights()
    points = config.severity_points()
    # Only the five judged categories may be blended. `Parseability`, `Structure` and
    # `Title` are decided by rules alone and are never asked of a model, so a provider
    # returning an entry for one of them is answering a question nobody put to it --
    # and without this line it would be accepted and blended, silently converting a
    # deterministic category into a judged one.
    shares = rule_shares()
    llm_categories = {category: value
                      for category, value in (llm_categories or {}).items()
                      if category in JUDGED_CATEGORIES}

    # Drop unevidenced findings: a claim with nothing quoted is not checkable.
    findings = [f for f in findings if f.evidence.strip() or f.locator == "document"]

    deductions: dict[Category, float] = {c: 0.0 for c in weights}
    ledger: list[LedgerRow] = []

    for finding in findings:
        cost = _cost(finding, weights, points)
        finding._raw_cost = cost
        deductions[finding.category] += cost

    # Which categories anything actually assessed. A judged category with no judge
    # answer, no rule channel (07 §5 gives `Agentic systems` and `AI-assisted coding
    # fluency` rule_share 0) and nothing deducted is a question nobody asked: with
    # `deductions` starting every category at 0.0 it would otherwise hold a permanent
    # 100 and carry its full weight, manufacturing a result from a check that never
    # ran. It is printed and left out of the arithmetic instead. The last clause keeps
    # that self-correcting -- if a finding does deduct there, the category is assessed
    # after all and its deduction counts.
    assessed = {
        category: (category not in JUDGED_CATEGORIES
                   or category in llm_categories
                   or shares[category] > 0
                   or deductions[category] > 0)
        for category in weights
    }

    # Points are reported in COMPOSITE space -- what the finding actually cost the
    # headline number -- so a card and its ledger row never disagree. Category-space
    # cost would show "-96" beside a ledger row reading "-16" for the same defect.
    # The denominator is the assessed weight, the same one the composite divides by.
    total_weight = sum(w for c, w in weights.items() if assessed[c])
    for finding in findings:
        raw_total = deductions[finding.category]
        # A category floors at zero, so deductions past 100 cost nothing. Scaling
        # by that keeps the reported points equal to what was actually lost.
        floor_scale = (min(raw_total, 100.0) / raw_total) if raw_total > 0 else 0.0
        share = (weights[finding.category] / total_weight) if total_weight else 0.0
        finding.points = round(finding._raw_cost * share * floor_scale, 2)

    unreadable = any(f.rule_id in UNREADABLE_RULES for f in findings)

    categories: list[CategoryScore] = []
    for category, weight in weights.items():
        rule_score = max(0.0, 100.0 - deductions[category])
        if unreadable:
            # Nothing was assessed. Leaving other categories at their default 100
            # would manufacture a result from checks that never ran.
            rule_score = 0.0
        low = high = None
        note = ""
        if category in llm_categories:
            mean, band_low, band_high = llm_categories[category]
            # Rules are authoritative on mechanics; the model is better on substance.
            rule_share = shares[category]
            blended = rule_score * rule_share + mean * (1 - rule_share)
            if band_high - band_low >= 12:
                low = round(rule_score * rule_share + band_low * (1 - rule_share), 1)
                high = round(rule_score * rule_share + band_high * (1 - rule_share), 1)
                note = "providers disagreed; shown as a range"
            rule_score = blended
        if not assessed[category]:
            rule_score, low, high = 0.0, None, None
            note = "not assessed -- no judge answered it and no rule reaches it"
        categories.append(CategoryScore(
            category=category, score=round(rule_score, 1), weight=weight,
            low=low, high=high, note=note, assessed=assessed[category],
        ))

    scored = [c for c in categories if c.assessed]
    composite = (sum(c.score * c.weight for c in scored) / total_weight) if total_weight else 0.0

    # Caps are recorded rather than silently applied, so the ledger can show them
    # as their own line instead of burying them in a rounding row.
    caps: list[tuple[str, float]] = []
    fraud = [f for f in findings if f.rule_id in FRAUD_RULES]
    if fraud:
        cap = float(config.scoring()["fraud_cap"])
        if composite > cap:
            caps.append((f"Hidden text found: capped at {cap:.0f}", cap))
        composite = min(composite, cap)

    if unreadable:
        composite = min(composite, UNREADABLE_CAP)

    composite = round(max(0.0, min(100.0, composite)), 1)

    if unreadable:
        caps.append(("Nothing else could be assessed", composite))

    ledger = _build_ledger(
        findings, categories, weights, caps, composite,
        blended=bool(llm_categories),
    )

    parser_sub = _subscore(categories, Gate.PARSER, weights)
    human_sub = _subscore(categories, {Gate.RECRUITER, Gate.MANAGER}, weights)
    if unreadable:
        # Nothing about the content was assessed, so claiming a human-gate score
        # would be inventing a result.
        human_sub = 0.0
        notes = list(notes or [])
        notes.insert(0, "No text could be extracted, so nothing beyond the file "
                        "itself was assessed. Fix the export and run this again.")

    return Report(
        composite=composite,
        grade=_grade(composite),
        parser_subscore=parser_sub,
        human_subscore=human_sub,
        categories=categories,
        findings=sorted(
            findings,
            key=lambda f: ({Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2}[f.severity], -f.points),
        ),
        ledger=ledger,
        partial=partial,
        notes=notes or [],
        run_meta=run_meta or {},
    )


def _subscore(categories: list[CategoryScore], gate, weights: dict[Category, float]) -> float:
    gates = gate if isinstance(gate, set) else {gate}
    from .models import CATEGORY_GATE
    rows = [c for c in categories if CATEGORY_GATE[c.category] in gates and c.assessed]
    total = sum(c.weight for c in rows)
    if not total:
        return 100.0
    return round(sum(c.score * c.weight for c in rows) / total, 1)


def _build_ledger(
    findings: list[Finding],
    categories: list[CategoryScore],
    weights: dict[Category, float],
    caps: list[tuple[str, float]],
    composite: float,
    blended: bool,
) -> list[LedgerRow]:
    """One row per rule, showing what it actually cost the composite.

    Two corrections keep the rows honest rather than merely indicative:

    1. A category floors at zero, so deductions past 100 cost nothing. Rows are
       scaled by the category's *effective* deduction, otherwise a badly failing
       category would show phantom points the score never lost.
    2. Where the model's scores were blended in, that adjustment gets its own row,
       because it moved the composite and hiding it would break the arithmetic.
    """
    grouped: dict[tuple[str, Category], list[Finding]] = {}
    for f in findings:
        grouped.setdefault((f.rule_id, f.category), []).append(f)

    rows: list[LedgerRow] = []
    for (rule_id, category), items in grouped.items():
        # Findings already carry composite-space points, so a ledger row is just
        # the sum of its cards.
        cost = sum(i.points for i in items)
        if cost < 0.05:
            continue
        # One finding speaks for itself. Several do not: naming the row after any
        # one of them presents a group under a single member's title. Truncate
        # first so the count cannot be cut off, which is what hid the aggregation.
        label = _truncate(items[0].message, 74)
        if len(items) > 1:
            label = f"{_truncate(items[0].message.split(':')[0], 62)} (x{len(items)})"
        rows.append(LedgerRow(
            label=label, points=-round(cost, 1),
            rule_id=rule_id, category=category,
        ))
    rows.sort(key=lambda r: r.points)

    # The total is the payoff, so it must stay on screen. Rows past the cap are
    # aggregated rather than dropped -- the arithmetic still reconciles, and the
    # full list is in the findings stream and both exports.
    if len(rows) > LEDGER_VISIBLE_ROWS:
        tail = rows[LEDGER_VISIBLE_ROWS:]
        rows = rows[:LEDGER_VISIBLE_ROWS]
        rows.append(LedgerRow(
            label=f"{len(tail)} smaller deductions",
            points=round(sum(r.points for r in tail), 1),
            rule_id="ledger/tail",
        ))

    # A cap is a real, explainable movement of the score, so it gets its own row.
    for label, _value in caps:
        running = 100.0 + sum(r.points for r in rows)
        rows.append(LedgerRow(
            label=label, points=round(composite - running, 1), rule_id="score/cap",
        ))

    # Reconcile: anything the model's blended scores added or removed gets its own
    # row, so 100 + sum(rows) == composite exactly.
    drift = composite - (100.0 + sum(r.points for r in rows))
    if abs(drift) >= 0.05:
        # Name it for what it actually is. With no model in the run this row is
        # rounding, and calling it judgement would be a small lie in the one place
        # the report is claiming to be fully auditable.
        if blended:
            label = "Model judgement of substance" if drift < 0 else "Model judgement (credit)"
        else:
            label = "Rounding"
        rows.append(LedgerRow(label=label, points=round(drift, 1),
                              rule_id="llm/blend" if blended else "ledger/rounding"))

    return rows
