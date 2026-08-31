"""The weight-budget measurement: the properties its numbers rest on.

02 chose a budget from this script's tables, so what has to hold is that the tables
are the thing they claim to be -- the rules that run today, refiled by 07 and 12, and
the composite computed by the same arithmetic `score.py` uses. The composites
themselves are not pinned: they move whenever a rule or a criterion is revised, and
the decision they justified is recorded in `weight-budget.md`, not here.
"""
import pytest

from ats.models import Category, Finding, Severity
from scripts.weight_budget import (
    CANDIDATES,
    CRAFT,
    DERIVED,
    FIXED_AUTHORED,
    SLUG_OF,
    _deducts,
    _new_category,
    floored,
    proportional,
    weights_for,
)

ALL_RULES = [
    "parse/hidden-text", "parse/no-text-layer", "parse/multi-column", "parse/tables",
    "parse/edge-band", "parse/exotic-bullets", "parse/page-count", "parse/font-sprawl",
    "struct/missing-dates", "struct/thin-role", "struct/bloated-role",
    "struct/not-reverse-chron", "struct/employment-gap",
    "contact/no-email", "contact/no-phone", "contact/no-linkedin", "contact/no-github",
    "title/off-domain", "title/seniority-mismatch",
    "content/passive-voice", "content/first-person", "content/long-bullet",
    "content/duplicate-bullet", "content/weak-opener", "content/ownership",
    "content/bullet-invariants", "content/quantification",
    "cred/no-production", "cred/notebook-only", "cred/no-evaluation",
    "cred/no-named-models", "cred/unlinked-projects",
    "scan/no-identity-above-fold", "scan/no-evidence-above-fold", "scan/no-summary",
    "scan/experience-outranked", "scan/unexplained-pivot",
    "kw/over-repetition", "kw/skills-dump", "kw/soft-skill-padding",
    "kw/unsupported-skills", "kw/thin-core-ml",
    "jd/missing-core", "jd/missing-secondary", "jd/missing-named-tools",
    "slop/portable", "slop/robotic-rhythm", "slop/synonym-cycling", "slop/banned-word",
]

# The old category each rule carries today, for the ones the mapping resolves by
# carry-over rather than by name.
OLD = {
    "parse/": Category.PARSEABILITY,
    "struct/": Category.STRUCTURE,
    "contact/": Category.STRUCTURE,
    "title/": Category.TITLE,
    "slop/": Category.WRITING,
    "scan/": Category.RECRUITER_SCAN,
    "content/": Category.WRITING,
    "cred/": Category.CREDIBILITY,
    "kw/": Category.RELEVANCE,
    "jd/": Category.RELEVANCE,
}


def _finding(rule_id: str) -> Finding:
    old = next(cat for prefix, cat in OLD.items() if rule_id.startswith(prefix))
    return Finding(rule_id=rule_id, category=old, severity=Severity.MINOR,
                   message="m", fix="f", evidence="e", locator="document")


NEW_CATEGORIES = set(FIXED_AUTHORED) | {CRAFT} | set(DERIVED)


@pytest.mark.parametrize("rule_id", ALL_RULES)
def test_every_rule_lands_somewhere_nameable(rule_id):
    """No rule falls through the mapping. `_new_category` raises rather than guessing,
    so the whole test is that it does not raise and returns a name that exists."""
    where = _new_category(_finding(rule_id))
    assert where in NEW_CATEGORIES | {"(advice-only)", "(retired)"}, where


@pytest.mark.parametrize("rule_id", ALL_RULES)
def test_a_rule_that_deducts_lands_in_a_real_category(rule_id):
    """The other side of it: advice-only and retired rules have no category, and a
    rule that still deducts has to have one, or its points go nowhere."""
    where = _new_category(_finding(rule_id))
    assert _deducts(rule_id) == (where in NEW_CATEGORIES)


def test_the_old_categories_that_04_retired_have_no_rules_left():
    """`Impact`, `AI/ML relevance`, `Credibility`, `Recruiter scan` and `Writing
    quality` are gone, so nothing may still file into them."""
    retired = {c.value for c in (Category.IMPACT, Category.RELEVANCE,
                                Category.CREDIBILITY, Category.RECRUITER_SCAN,
                                Category.WRITING)}
    for rule_id in ALL_RULES:
        assert _new_category(_finding(rule_id)) not in retired


@pytest.mark.parametrize("label,budget,split", CANDIDATES)
def test_every_candidate_spends_exactly_one_hundred_points(label, budget, split):
    weights = weights_for(budget, split)
    assert set(weights) == NEW_CATEGORIES
    assert sum(weights.values()) == pytest.approx(100.0, abs=0.05)


@pytest.mark.parametrize("label,budget,split", CANDIDATES)
def test_the_derived_block_gets_the_budget_and_craft_gets_the_rest(label, budget, split):
    weights = weights_for(budget, split)
    assert sum(weights[c] for c in DERIVED) == pytest.approx(budget, abs=0.05)
    assert weights[CRAFT] == pytest.approx(100 - budget - 25, abs=0.05)
    for category, value in FIXED_AUTHORED.items():
        assert weights[category] == value


def test_the_chosen_weights_are_04s_illustration():
    """02's answer: budget 50, split in proportion to document frequency."""
    assert proportional(50.0) == {
        "Production ownership": 15.0,
        "Agentic systems": 15.0,
        "Evaluation rigour": 12.5,
        "AI-assisted coding fluency": 7.5,
    }


def test_proportional_tracks_the_corpus_and_floored_compresses_it():
    """The two splits differ only in the bottom category, which is the whole argument."""
    prop, floor = proportional(50.0), floored(50.0)
    assert prop["Agentic systems"] > prop["AI-assisted coding fluency"] * 1.9
    assert floor["Agentic systems"] < floor["AI-assisted coding fluency"] * 1.6
    # Both still rank the four the way the corpus does.
    for split in (prop, floor):
        assert split["Production ownership"] >= split["Evaluation rigour"]
        assert split["Evaluation rigour"] >= split["AI-assisted coding fluency"]


def test_every_judged_category_has_a_spec_to_read_its_band_from():
    from ats.rubric import SLUGS
    assert set(SLUG_OF.values()) == set(SLUGS)
    assert set(SLUG_OF) == set(DERIVED) | {CRAFT}
