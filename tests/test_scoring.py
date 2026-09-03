"""Scoring invariants.

These are the commitments the product rests on, so they are asserted rather than
left as intentions in a design doc.
"""
from pathlib import Path

import pytest
from pydantic import ValidationError

from ats import config
from ats.models import (
    DERIVED_CATEGORIES,
    JUDGED_CATEGORIES,
    Category,
    Finding,
    Gate,
    JudgedCategory,
    Provenance,
    Severity,
)
from ats.score import build, rule_shares


def _judged(category, band, value, high=None, high_value=None):
    """One category's judged half, as `passes.judge_categories` would hand it over."""
    return JudgedCategory(
        category=category, value=value, band=band, band_name=band,
        high_band=high or band, high_band_name=high or band,
        high_value=high_value if high_value is not None else value,
        gap=1 if high else 0, judges=2 if high else 1,
    )


def _finding(rule_id="x/y", category=Category.STRUCTURE, severity=Severity.MINOR,
             provenance=Provenance.RECRUITER_EVIDENCE, **extra):
    # `Resume craft` findings must name a gate, so supply one wherever a test reaches
    # for an arbitrary category and lands on that one.
    if category is Category.RESUME_CRAFT:
        extra.setdefault("gate", Gate.MANAGER)
    return Finding(
        rule_id=rule_id, category=category, severity=severity,
        message="m", fix="f", evidence="e", locator="l", provenance=provenance, **extra,
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
    report = build([], llm_categories={Category.AGENTIC_SYSTEMS: _judged(
        Category.AGENTIC_SYSTEMS, "C", 58.0)})
    row = next(c for c in report.categories if c.category is Category.AGENTIC_SYSTEMS)
    assert row.assessed
    # rule_share 0, so the judge's number is the whole of the score.
    assert row.score == 58.0


def test_a_contested_category_scores_the_lower_band_and_names_the_other():
    """06's rule, and what the reader is told about it.

    `Production ownership` at rule_share 0.4 and a clean rule channel: the score is the
    blend of the LOW band, and the high one rides beside it in words rather than
    replacing the score with a range.
    """
    judged = _judged(Category.PRODUCTION_OWNERSHIP, "D", 35.0,
                     high="C", high_value=58.0)
    judged.band_name, judged.high_band_name = "Built, not operated", "Shipped"
    judged.split_criteria = ["production-ownership/C3"]
    report = build([], llm_categories={Category.PRODUCTION_OWNERSHIP: judged})

    row = next(c for c in report.categories
               if c.category is Category.PRODUCTION_OWNERSHIP)
    assert row.contested
    assert row.score == 61.0, "100 * 0.4 + 35 * 0.6 -- the lower band, blended"
    assert (row.low, row.high) == (61.0, 74.8)
    assert "Built, not operated" in row.note and "Shipped" in row.note
    assert "production-ownership/C3" in row.note
    assert "range" not in row.note, "two band names, not two numbers"


def test_judges_that_agree_contest_nothing():
    judged = _judged(Category.PRODUCTION_OWNERSHIP, "C", 58.0)
    report = build([], llm_categories={Category.PRODUCTION_OWNERSHIP: judged})
    row = next(c for c in report.categories
               if c.category is Category.PRODUCTION_OWNERSHIP)
    assert not row.contested and row.note == "" and row.low is None


def test_a_withheld_category_neither_inflates_nor_deflates_the_composite():
    """The bug 06 names, and its fix.

    On a document whose roles did not parse, `content_pass` withholds all five judged
    categories before spending a call. Told nothing, `build` floated the three with a
    rule channel at 100 -- 52.5 of the composite's points manufactured out of checks
    that never ran. Withheld categories are left out instead, and the composite
    renormalises over the 25 points the parser gate actually assessed.
    """
    reason = "withheld -- no roles survived extraction"
    withheld = {c: reason for c in JUDGED_CATEGORIES}
    findings = [_finding(rule_id="parse/multi-column",
                         category=Category.PARSEABILITY, severity=Severity.CRITICAL)]

    told = build(list(findings), withheld=withheld)
    untold = build(list(findings))

    rows = {c.category: c for c in told.categories}
    for category in JUDGED_CATEGORIES:
        assert not rows[category].assessed
        assert rows[category].score == 0.0
        assert rows[category].note == reason
    assert told.composite < untold.composite, "the 100s are gone"
    # The composite is exactly the parser gate's three categories, renormalised.
    scored = [c for c in told.categories if c.assessed]
    assert {c.category for c in scored} == {
        Category.PARSEABILITY, Category.STRUCTURE, Category.TITLE}
    assert sum(c.weight for c in scored) == 25.0


def test_a_withheld_category_is_not_rescued_by_a_deduction():
    """`assessed`'s self-correcting clause must not reach a withheld category.

    A slop finding still fires on a two-column document, and it does not make the
    craft criteria answerable -- they have no bullets to be about. The finding still
    prints; it costs the composite nothing, and says so rather than quoting points the
    score never lost.
    """
    slop = _finding(rule_id="slop/x", category=Category.RESUME_CRAFT,
                    severity=Severity.MAJOR, gate=Gate.MANAGER)
    report = build([slop], withheld={Category.RESUME_CRAFT: "withheld -- no roles"})

    row = next(c for c in report.categories if c.category is Category.RESUME_CRAFT)
    assert not row.assessed
    assert report.findings[0].points == 0.0
    assert not [r for r in report.ledger if r.rule_id == "slop/x"]


def test_a_withheld_category_cannot_also_carry_a_judged_value():
    """Withholding happens before the call, so this cannot arise from the pipeline --
    but a caller that passes both must not get a blended score out of a category the
    report is about to print as unassessable."""
    report = build(
        [],
        llm_categories={Category.PRODUCTION_OWNERSHIP:
                        _judged(Category.PRODUCTION_OWNERSHIP, "A", 95.0)},
        withheld={Category.PRODUCTION_OWNERSHIP: "withheld -- no roles"},
    )
    row = next(c for c in report.categories
               if c.category is Category.PRODUCTION_OWNERSHIP)
    assert not row.assessed and row.score == 0.0


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
        c: _judged(c, "A", 100.0)
        for c in (Category.PARSEABILITY, Category.STRUCTURE, Category.TITLE)
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


# --- Advice-only findings, and findings that carry their own gate (migration 04) -----

# The whole of tool coverage -- one `kw/thin-*` per taxonomy group, plus
# `kw/unsupported-skills` and the three `jd/missing-*` (07 §2) -- with 07 §3.1's
# collision loser and 12's two rulings. Fourteen rules; the ticket's "eleven" counts
# tool coverage alone.
import json as _json
from ats.keywords import TAXONOMY_PATH

_GROUPS = sorted({key.split("/")[0] for key in
                  _json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))["terms"]})
ADVICE_RULES = (
    {f"kw/thin-{group.replace('_', '-')}" for group in _GROUPS}
    | {"kw/unsupported-skills", "jd/missing-core", "jd/missing-secondary",
       "jd/missing-named-tools", "cred/notebook-only", "content/quantification",
       "cred/unlinked-projects"}
)


def _advice(rule_id="kw/thin-core-ml", gate=Gate.RECRUITER, severity=Severity.MAJOR):
    return Finding(
        rule_id=rule_id, category=None, gate=gate, advice_only=True,
        severity=severity, message="m", fix="f", evidence="e", locator="l",
    )


def test_an_advice_only_finding_costs_nothing_however_severe():
    """07 §2's whole point: it fires, it prints its fix, it moves no number."""
    for severity in Severity:
        report = build([_advice(severity=severity)])
        assert report.composite == 100.0
        assert report.findings[0].points == 0.0


def test_an_advice_only_finding_has_no_ledger_row():
    """The ledger is a ledger of costs. A row reading -0.0 is not a cost."""
    report = build([_advice(), _finding(category=Category.STRUCTURE)])
    assert [row.rule_id for row in report.ledger if row.rule_id.startswith("kw/")] == []
    assert any(row.rule_id == "x/y" for row in report.ledger)


def test_advice_never_dilutes_what_a_real_finding_cost():
    """Adding advice to a report must not move the composite by any amount."""
    real = [_finding(category=Category.STRUCTURE, severity=Severity.CRITICAL)]
    alone = build(list(real)).composite
    with_advice = build(real + [_advice() for _ in range(20)]).composite
    assert alone == with_advice


def test_an_advice_only_finding_still_prints_under_a_gate():
    report = build([_advice(gate=Gate.RECRUITER)])
    assert [f.rule_id for f in report.by_gate(Gate.RECRUITER)] == ["kw/thin-core-ml"]
    assert report.by_gate(Gate.MANAGER) == []


def test_the_eleven_rules_07_and_12_named_deduct_nothing(fixtures):
    """The dispositions, on documents rather than in a table.

    Seven `kw/thin-*`, three `jd/missing-*` and `kw/unsupported-skills` are the whole
    of tool coverage (07 §2); `cred/notebook-only` is 07 §3.1's collision loser; and
    `content/quantification` and `cred/unlinked-projects` are 12's two rulings.
    """
    from ats.extract import extract
    from ats.pipeline import deterministic
    from ats.sections import parse

    seen = set()
    for path in fixtures.values():
        doc = extract(str(path))
        for finding in deterministic(doc, parse(doc.text), "", "AI Engineer"):
            if finding.rule_id in ADVICE_RULES:
                seen.add(finding.rule_id)
                assert finding.advice_only, finding.rule_id
                assert finding.category is None, finding.rule_id
                assert finding.fix, f"{finding.rule_id} advises nothing"
            else:
                assert not finding.advice_only, finding.rule_id
    assert seen, "no advice-only rule fired on any fixture"
    assert len(ADVICE_RULES) == len(_GROUPS) + 7


def test_a_finding_carries_its_own_gate_rather_than_borrowing_the_categorys():
    """`Resume craft` holds both kinds, which is why the category cannot supply it.

    12 chose `Gate.RECRUITER` for the category and called the choice provisional for
    exactly this reason. A `scan/*` finding is what the first reader meets in six
    seconds; a `slop/*` finding is in prose only the second reader reaches.
    """
    scan = Finding(rule_id="scan/no-summary", category=Category.RESUME_CRAFT,
                   gate=Gate.RECRUITER, severity=Severity.MINOR,
                   message="m", fix="f", evidence="e")
    slop = Finding(rule_id="slop/portable", category=Category.RESUME_CRAFT,
                   gate=Gate.MANAGER, severity=Severity.MINOR,
                   message="m", fix="f", evidence="e")
    assert scan.gate is Gate.RECRUITER and slop.gate is Gate.MANAGER
    assert scan.category is slop.category
    report = build([scan, slop])
    assert [f.rule_id for f in report.by_gate(Gate.RECRUITER)] == ["scan/no-summary"]
    assert [f.rule_id for f in report.by_gate(Gate.MANAGER)] == ["slop/portable"]


def test_a_finding_in_resume_craft_must_name_its_gate():
    """The one category where defaulting from `CATEGORY_GATE` would guess wrong."""
    with pytest.raises(ValidationError):
        Finding(rule_id="x/y", category=Category.RESUME_CRAFT, severity=Severity.MINOR,
                message="m", fix="f", evidence="e")
    # Everywhere else the category still settles it.
    assert Finding(rule_id="x/y", category=Category.PARSEABILITY,
                   severity=Severity.MINOR, message="m", fix="f",
                   evidence="e").gate is Gate.PARSER


def test_an_advice_only_finding_may_not_carry_a_category():
    """A category is where a cost goes, and this one has no cost."""
    with pytest.raises(ValidationError):
        Finding(rule_id="x/y", category=Category.RESUME_CRAFT, gate=Gate.MANAGER,
                advice_only=True, severity=Severity.MINOR, message="m", fix="f",
                evidence="e")


def test_a_finding_with_neither_a_category_nor_a_gate_cannot_be_printed():
    with pytest.raises(ValidationError):
        Finding(rule_id="x/y", severity=Severity.MINOR, message="m", fix="f",
                evidence="e")


def test_the_craft_categorys_own_gate_moves_nothing(monkeypatch):
    """12's finding, still true after findings took their gates with them.

    12 expected `CATEGORY_GATE[Resume craft]` to be read by nothing once findings
    carried a gate. `score._subscore` still reads it -- but with the set
    {RECRUITER, MANAGER}, so craft lands in the same bucket either way. The entry is
    required and inert, and if that ever stops being true this fails rather than
    silently moving somebody's score.
    """
    from ats import models

    findings = [
        Finding(rule_id="scan/no-summary", category=Category.RESUME_CRAFT,
                gate=Gate.RECRUITER, severity=Severity.MAJOR,
                message="m", fix="f", evidence="e"),
        Finding(rule_id="slop/portable", category=Category.RESUME_CRAFT,
                gate=Gate.MANAGER, severity=Severity.MAJOR,
                message="m", fix="f", evidence="e"),
    ]
    before = build(list(findings))
    monkeypatch.setitem(models.CATEGORY_GATE, Category.RESUME_CRAFT, Gate.MANAGER)
    after = build(list(findings))
    assert (before.composite, before.parser_subscore, before.human_subscore) == (
        after.composite, after.parser_subscore, after.human_subscore)
    # And the findings stayed where they put themselves, not where the category is.
    assert len(after.by_gate(Gate.RECRUITER)) == 1
    assert len(after.by_gate(Gate.MANAGER)) == 1
