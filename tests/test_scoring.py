"""Scoring invariants.

These are the commitments the product rests on, so they are asserted rather than
left as intentions in a design doc.
"""
import pytest

from ats import config
from ats.models import Category, Finding, Provenance, Severity
from ats.score import build


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
            [(Category.IMPACT, Severity.MAJOR), (Category.WRITING, Severity.MINOR),
             (Category.RELEVANCE, Severity.MAJOR), (Category.STRUCTURE, Severity.MINOR)]
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
    human_only = build([_finding(category=Category.IMPACT, severity=Severity.MAJOR)])
    assert parser_only.parser_subscore < 100 and parser_only.human_subscore == 100
    assert human_only.human_subscore < 100 and human_only.parser_subscore == 100


def test_score_floors_at_zero():
    many = [_finding(rule_id=f"r/{i}", category=Category.IMPACT, severity=Severity.CRITICAL,
                     provenance=Provenance.PARSER_MECHANICS) for i in range(60)]
    report = build(many)
    assert 0.0 <= report.composite <= 100.0


def test_card_and_ledger_quote_the_same_number():
    """A finding's reported cost must equal its ledger row, or the report lies."""
    findings = [_finding(rule_id="r/a", category=Category.IMPACT, severity=Severity.MAJOR)
                for _ in range(4)]
    report = build(findings)
    row = next(r for r in report.ledger if r.rule_id == "r/a")
    card_total = sum(f.points for f in report.findings if f.rule_id == "r/a")
    assert abs(card_total + row.points) < 0.05


def test_points_never_exceed_what_was_actually_lost():
    """With a floored category, reported points must shrink to match reality."""
    many = [_finding(rule_id=f"r/{i}", category=Category.WRITING, severity=Severity.CRITICAL,
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
        finding = _finding(rule_id="llm/unverified-outcome", category=Category.CREDIBILITY,
                           severity=Severity.MAJOR)
        finding.message = f"{long_message} ({index})"
        findings.append(finding)

    row = next(r for r in build(findings).ledger if r.rule_id == "llm/unverified-outcome")
    assert row.label.endswith("(x7)")


def test_distinct_rule_ids_get_their_own_ledger_rows():
    """Two unrelated defects must not total under one row titled after either."""
    first = _finding(rule_id="llm/unverified-outcome", category=Category.CREDIBILITY,
                     severity=Severity.MAJOR)
    first.message = "No outcome is shown for the routing work"
    second = _finding(rule_id="llm/missing-scale", category=Category.CREDIBILITY,
                      severity=Severity.MAJOR)
    second.message = "No scale is given for the pipeline"

    labels = {r.rule_id: r.label for r in build([first, second]).ledger}
    assert labels["llm/unverified-outcome"] == first.message
    assert labels["llm/missing-scale"] == second.message
