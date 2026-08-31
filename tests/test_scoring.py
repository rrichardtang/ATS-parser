"""Scoring invariants.

These are the commitments the product rests on, so they are asserted rather than
left as intentions in a design doc.
"""
from pathlib import Path

import pytest

from ats import config
from ats.models import (
    DERIVED_CATEGORIES,
    JUDGED_CATEGORIES,
    Category,
    Finding,
    Provenance,
    Severity,
)
from ats.score import build, rule_shares


def _finding(rule_id="x/y", category=Category.STRUCTURE, severity=Severity.MINOR,
             provenance=Provenance.RECRUITER_EVIDENCE):
    return Finding(
        rule_id=rule_id, category=category, severity=severity,
        message="m", fix="f", evidence="e", locator="l", provenance=provenance,
    )


def test_clean_resume_scores_100():
    assert build([]).composite == 100.0


def test_no_hard_gate_single_finding():
    """A single non-fraud finding may never cost more than its category weight.

    The motivating case is real: a public checker returned 22/100 because the
    resume had no phone number. That measures one field and reports it as a
    verdict on the whole document.
    """
    weights = config.category_weights()
    for category in Category:
        for severity in Severity:
            report = build([_finding(category=category, severity=severity)])
            lost = 100.0 - report.composite
            assert lost <= weights[category] + 0.01, (
                f"{category} / {severity} cost {lost:.1f}, "
                f"above the category weight {weights[category]}"
            )


def test_missing_phone_costs_a_few_points_not_a_verdict():
    report = build([_finding(rule_id="contact/no-phone", severity=Severity.MINOR)])
    assert report.composite > 97.0, (
        f"missing phone dropped the score to {report.composite}; it is a 30-second fix"
    )


def test_heuristic_rules_are_capped_at_minor():
    """A rule resting on author judgment cannot sink a score."""
    capped = config.apply_provenance_cap(Severity.CRITICAL, Provenance.HEURISTIC)
    assert capped is Severity.MINOR
    assert config.apply_provenance_cap(
        Severity.CRITICAL, Provenance.PARSER_MECHANICS
    ) is Severity.CRITICAL


def test_hidden_text_caps_the_composite():
    """The one deliberate hard gate: a fraud-flag risk, not a style preference."""
    report = build([_finding(rule_id="parse/hidden-text",
                             category=Category.PARSEABILITY,
                             severity=Severity.CRITICAL,
                             provenance=Provenance.PARSER_MECHANICS)])
    assert report.composite <= config.scoring()["fraud_cap"]


def test_ledger_reconciles_to_composite():
    findings = [
        _finding(rule_id=f"r/{i}", category=c, severity=s)
        for i, (c, s) in enumerate(
            [(Category.PRODUCTION_OWNERSHIP, Severity.MAJOR), (Category.RESUME_CRAFT, Severity.MINOR),
             (Category.EVALUATION_RIGOUR, Severity.MAJOR), (Category.STRUCTURE, Severity.MINOR)]
        )
    ]
    report = build(findings)
    total = 100.0 + sum(row.points for row in report.ledger)
    assert abs(total - report.composite) < 0.05, (
        "the ledger must sum to the composite -- a score whose derivation does not "
        "reconcile cannot be disputed"
    )


def test_every_finding_reports_its_cost():
    report = build([_finding(rule_id=f"r/{i}") for i in range(3)])
    assert all(f.points > 0 for f in report.findings)


def test_unevidenced_findings_are_dropped():
    """A claim with nothing quoted is not checkable, so it does not ship."""
    bare = _finding()
    bare.evidence = ""
    bare.locator = "exp[0]"
    assert build([bare]).findings == []


def test_gate_subscores_are_independent():
    parser_only = build([_finding(category=Category.PARSEABILITY, severity=Severity.MAJOR,
                                  provenance=Provenance.PARSER_MECHANICS)])
    human_only = build([_finding(category=Category.PRODUCTION_OWNERSHIP, severity=Severity.MAJOR)])
    assert parser_only.parser_subscore < 100 and parser_only.human_subscore == 100
    assert human_only.human_subscore < 100 and human_only.parser_subscore == 100


def test_score_floors_at_zero():
    many = [_finding(rule_id=f"r/{i}", category=Category.PRODUCTION_OWNERSHIP, severity=Severity.CRITICAL,
                     provenance=Provenance.PARSER_MECHANICS) for i in range(60)]
    report = build(many)
    assert 0.0 <= report.composite <= 100.0


def test_card_and_ledger_quote_the_same_number():
    """A finding's reported cost must equal its ledger row, or the report lies."""
    findings = [_finding(rule_id="r/a", category=Category.PRODUCTION_OWNERSHIP, severity=Severity.MAJOR)
                for _ in range(4)]
    report = build(findings)
    row = next(r for r in report.ledger if r.rule_id == "r/a")
    card_total = sum(f.points for f in report.findings if f.rule_id == "r/a")
    assert abs(card_total + row.points) < 0.05


def test_points_never_exceed_what_was_actually_lost():
    """With a floored category, reported points must shrink to match reality."""
    many = [_finding(rule_id=f"r/{i}", category=Category.RESUME_CRAFT, severity=Severity.CRITICAL,
                     provenance=Provenance.PARSER_MECHANICS) for i in range(40)]
    report = build(many)
    assert abs(sum(f.points for f in report.findings) - (100 - report.composite)) < 0.5


def test_aggregated_ledger_row_keeps_its_count_visible():
    """A row standing for several findings must say so, whatever its label length.

    The count used to be appended before truncation, so a long first message cut
    it off and the row read as a single finding -- under that one finding's title.
    """
    long_message = (
        "The routing optimization reports fewer inference passes but does not show "
        "whether routing quality, answer quality, latency, or cost improved"
    )
    findings = []
    for index in range(7):
        finding = _finding(rule_id="llm/unverified-outcome", category=Category.PRODUCTION_OWNERSHIP,
                           severity=Severity.MAJOR)
        finding.message = f"{long_message} ({index})"
        findings.append(finding)

    row = next(r for r in build(findings).ledger if r.rule_id == "llm/unverified-outcome")
    assert row.label.endswith("(x7)")


def test_distinct_rule_ids_get_their_own_ledger_rows():
    """Two unrelated defects must not total under one row titled after either."""
    first = _finding(rule_id="llm/unverified-outcome", category=Category.PRODUCTION_OWNERSHIP,
                     severity=Severity.MAJOR)
    first.message = "No outcome is shown for the routing work"
    second = _finding(rule_id="llm/missing-scale", category=Category.PRODUCTION_OWNERSHIP,
                      severity=Severity.MAJOR)
    second.message = "No scale is given for the pipeline"

    labels = {r.rule_id: r.label for r in build([first, second]).ledger}
    assert labels["llm/unverified-outcome"] == first.message
    assert labels["llm/missing-scale"] == second.message


# --- The category set, and the two latent bugs 04 found before either had been hit ---


def test_the_weights_are_the_ones_02_chose():
    """Budget 50 split 6:6:5:3, authored block at today's numbers. Migration 02.

    The derived four carry no number in `weights.toml` at all -- they are computed from
    the corpus -- so this is also the check that the derivation reaches the categories.
    """
    weights = config.category_weights()
    assert sum(weights.values()) == pytest.approx(100.0, abs=0.01)
    assert weights[Category.PRODUCTION_OWNERSHIP] == 15.0
    assert weights[Category.AGENTIC_SYSTEMS] == 15.0
    assert weights[Category.EVALUATION_RIGOUR] == 12.5
    assert weights[Category.AI_ASSISTED_CODING] == 7.5
    assert weights[Category.RESUME_CRAFT] == 25.0
    assert weights[Category.PARSEABILITY] == 15.0


def test_no_derived_category_has_a_hand_written_weight():
    """The point of a derived block: adding a posting moves it and nobody edits a file.

    A number for one of the four in `[categories]` would be read as authored and would
    win, so it would sit there desynchronising from the corpus with nothing to catch it.
    """
    authored = set(config.load()["categories"])
    for category in DERIVED_CATEGORIES:
        assert category.value not in authored


def test_rule_share_above_zero_requires_a_rule_in_the_category():
    """07 §5's invariant, checked against the rule modules themselves.

    `score.build` starts every category's deductions at 0.0, so a category no rule can
    deduct from holds `rule_score = 100.0` forever. Blending that at rule_share 0.4
    would floor the category at 40 whatever a judge answered -- a constant wearing a
    channel's clothes. Hence `Agentic systems` and `AI-assisted coding fluency` at 0.

    Whether a category *has* a rule is a structural fact about the source, not
    something a run can observe, so this reads the source. The check is a biconditional
    in both directions: a share without a rule is the bug above, and a rule without a
    share is a deducting channel the blend ignores.
    """
    sources = "".join(
        (Path(__file__).resolve().parents[1] / "ats" / name).read_text(encoding="utf-8")
        for name in ("rules.py", "human.py", "keywords.py", "slop.py", "passes.py")
    )
    for category, share in rule_shares().items():
        has_rule = f"Category.{category.name}" in sources
        assert has_rule == (share > 0), (
            f"{category.value}: rule_share {share} but "
            f"{'no' if not has_rule else 'a'} rule files into it"
        )


def test_a_category_no_channel_reaches_is_not_scored_at_all():
    """The other half of the same bug: it must not ride into the composite at 100.

    With no judge and no rule, `Agentic systems` and `AI-assisted coding fluency` have
    nothing behind them. Scoring them 100 would say "nothing wrong here" about a
    question nobody asked, and would hand 22.5 points of the composite to a constant.
    """
    report = build([])
    unassessed = {c.category for c in report.categories if not c.assessed}
    assert unassessed == {Category.AGENTIC_SYSTEMS, Category.AI_ASSISTED_CODING}
    # A clean resume still scores 100: the excluded weight leaves the denominator too.
    assert report.composite == 100.0
    for row in report.categories:
        if not row.assessed:
            assert row.score == 0.0 and "not assessed" in row.note


def test_a_judged_category_the_judge_answered_is_scored():
    """And the exclusion lifts the moment a judge does answer it."""
    report = build([], llm_categories={Category.AGENTIC_SYSTEMS: (58.0, 58.0, 58.0)})
    row = next(c for c in report.categories if c.category is Category.AGENTIC_SYSTEMS)
    assert row.assessed
    # rule_share 0, so the judge's number is the whole of the score.
    assert row.score == 58.0


def test_a_provider_category_nobody_asked_about_is_dropped():
    """`Parseability`, `Structure` and `Title` are decided by rules alone.

    Nothing filters the provider's response today, and `score.build` blends whatever
    is present -- so a model returning a `Parseability` entry silently converts a
    deterministic category into a judged one at rule_share 0.7.
    """
    findings = [_finding(rule_id="parse/x", category=Category.PARSEABILITY,
                         severity=Severity.CRITICAL)]
    clean = build(list(findings))
    with_noise = build(list(findings), llm_categories={
        Category.PARSEABILITY: (100.0, 100.0, 100.0),
        Category.STRUCTURE: (100.0, 100.0, 100.0),
        Category.TITLE: (100.0, 100.0, 100.0),
    })
    assert with_noise.composite == clean.composite
    for row in with_noise.categories:
        assert row.note == "" or "not assessed" in row.note


def test_the_prompt_and_the_response_parser_name_the_same_categories():
    """A name the prompt asks for that the parser cannot resolve is a silently
    discarded answer; one the parser accepts but the prompt never asked for is
    latent bug 2 arriving from the other side."""
    from ats import passes, prompts

    assert set(prompts.CATEGORY_NAMES) == {c.value for c in JUDGED_CATEGORIES}
    assert set(passes.CATEGORY_BY_NAME) == {c.value.lower() for c in JUDGED_CATEGORIES}
