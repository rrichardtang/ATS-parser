"""The tolerance measurement, and that it reads the program rather than a copy of it.

Before ticket 03, `scripts/weight_budget.py` carried its own mapping of rules to
categories, its own weight sets and its own composite arithmetic, because none of them
existed in `ats/` yet. They do now, so what has to hold is that the script reads them:
a second copy would drift, and the number it prints would stop being about the rubric
that runs.
"""
import pytest

from ats import config
from ats.models import DERIVED_CATEGORIES, JUDGED_CATEGORIES, Category
from ats.score import rule_shares
from scripts import weight_budget


def test_the_script_reads_the_programs_weights_not_its_own():
    weights = config.category_weights()
    assert sum(weights.values()) == pytest.approx(100.0, abs=0.01)
    assert not hasattr(weight_budget, "CANDIDATES"), (
        "the candidate weight sets were 02's, before the program had any")
    assert not hasattr(weight_budget, "REFILED"), (
        "the rule mapping belongs to ats/rules.py and friends, not to a script")


def test_the_bar_is_the_inherited_acceptance_test():
    assert (weight_budget.TOLERANCE, weight_budget.FAIL) == (5.0, 8.0)


def test_both_tables_run_and_name_every_category(capsys):
    weight_budget.weight_table()
    printed = capsys.readouterr().out
    for category in Category:
        assert category.value in printed
    # Where each weight comes from is the point of the table.
    assert "authored" in printed and "df 6/6" in printed

    weight_budget.tolerance_table()
    printed = capsys.readouterr().out
    for category in JUDGED_CATEGORIES:
        assert category.value in printed
    for category in Category:
        if category not in JUDGED_CATEGORIES:
            assert f"\n{category.value}" not in printed


def test_a_category_with_no_rule_channel_is_the_exposed_one():
    """The finding 02 raised, as a property rather than a number in a document.

    At `rule_share` 0 nothing averages a disagreement down, so the whole band move
    reaches the composite. That is why `Agentic systems` -- rule_share 0 on the joint
    largest weight -- costs more per split than any category with a rule channel.
    """
    weights = config.category_weights()
    shares = rule_shares()
    exposure = {c: (1 - shares[c]) * weights[c] for c in JUDGED_CATEGORIES}
    assert max(exposure, key=exposure.get) is Category.AGENTIC_SYSTEMS
    for category in JUDGED_CATEGORIES:
        if shares[category] > 0:
            assert exposure[category] < exposure[Category.AGENTIC_SYSTEMS]


def test_the_derived_weights_follow_the_corpus():
    """Change the counts and the weights move, with nothing edited."""
    counts, postings = config.derived_document_frequency()
    assert postings == 6
    assert counts["Production ownership"] == 6
    assert counts["AI-assisted coding fluency"] == 3

    from ats.jd_dimensions import derived_weights
    even = derived_weights({c.value: 1 for c in DERIVED_CATEGORIES}, 1, 50.0)
    assert set(even.values()) == {12.5}, "equal document frequency, equal weight"
