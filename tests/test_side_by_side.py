"""The old-versus-new comparison: that it runs, and that it compares the right things.

What is pinned here is not a score. Scores move whenever the rubric moves, and the
whole point of 07 is to see them move. What must not move without somebody noticing is
the *scaffolding*: that the old rubric still runs from the commit the baseline was
recorded against, that the recorded judgements on both sides still load and still cover
the fixtures, and that the rename and retirement the diff would otherwise misreport are
still true of the two trees.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats.models import JUDGED_CATEGORIES, Category  # noqa: E402
from scripts import side_by_side as sbs  # noqa: E402

# The old tree is frozen, so its category set is a literal on purpose.
OLD_CATEGORIES = {
    "Parseability", "Recruiter scan", "Impact & quantification",
    "AI/ML relevance & depth", "Credibility & verifiability", "Writing quality",
    "Structure & formatting", "Title & seniority alignment",
}
NEW_CATEGORIES = {c.value for c in Category}
JUDGED = {c.value for c in JUDGED_CATEGORIES}


@pytest.fixture(scope="module")
def strong(fixtures) -> Path:
    return fixtures["strong"]


@pytest.fixture(scope="module")
def old_strong(strong) -> dict:
    """The old rubric on `strong` with its recorded judges -- one subprocess, shared."""
    return sbs.run_old(strong, sbs.old_recorded().get("strong"))


@pytest.fixture(scope="module")
def two_column(fixtures) -> Path:
    return fixtures["two_column"]


def test_the_old_rubric_still_runs_from_the_pinned_commit(old_strong):
    old = old_strong
    assert {c["category"] for c in old["categories"]} == OLD_CATEGORIES
    assert 0.0 <= old["composite"] <= 100.0
    assert old["findings"], "the old rubric found nothing, which it never did"


def test_the_new_rubric_runs_the_same_document(strong):
    new = sbs.run_new(strong, sbs.new_recorded().get("strong"))
    assert {c["category"] for c in new["categories"]} == NEW_CATEGORIES
    assert set(new["judged"]) == JUDGED


def test_the_recorded_judgements_cover_the_fixtures_on_both_sides():
    old, new = sbs.old_recorded(), sbs.new_recorded()
    judged = {"strong", "slop", "buried_evidence", "no_phone"}
    assert judged <= set(old), "the 30 August baseline no longer covers the fixtures"
    assert judged <= set(new), "the recorded criterion answers no longer cover them"
    for name in judged:
        assert len(old[name]) == 2, f"{name}: the baseline had two providers"


def test_a_withheld_document_is_not_given_a_band(two_column):
    """05 withholds before the call, so recorded answers for such a document are not
    used -- the comparison must show n/a rather than a band computed and then dropped."""
    new = sbs.run_new(two_column, sbs.new_recorded().get("two_column"))
    assert new["withheld"]
    assert new["withheld_but_recorded"]
    assert not new["judged"]
    judged_rows = [c for c in new["categories"] if c["category"] in JUDGED]
    assert all(not c["assessed"] for c in judged_rows)


def test_a_gate_with_no_score_prints_n_a(two_column):
    """A gate holding a withheld category reports None, not a number (score._subscore);
    the comparison has to print that rather than fail formatting it."""
    old = sbs.run_old(two_column, None)
    new = sbs.run_new(two_column, None)
    assert new["human_subscore"] is None
    human = next(line for line in sbs.render("two_column", old, new, "rules-only")
                 if line.startswith("human gate"))
    assert human.split()[-2:] == ["n/a", "n/a"]


def test_the_rename_and_the_retirement_are_still_true(strong, two_column, tmp_path):
    """A raw rule-id diff reads a rename as a disappearance. Both entries are claims
    about the two trees, so they are checked against the two trees -- on documents
    long enough to fire the rules in question, which the fixtures are not."""
    from scripts.make_acceptance_set import SET_DIR, render

    source = SET_DIR / "19-academic-terse-mid.txt"
    wordy = tmp_path / "wordy.pdf"
    render(source.stem, source.read_text(encoding="utf-8"), wordy)

    paths = (strong, two_column, wordy)
    olds = sbs.run_old_many([{"pdf": str(p), "per_provider": {}} for p in paths])
    old_ids = {f["rule_id"] for old in olds for f in old["findings"]}
    new_ids = {f["rule_id"] for p in paths for f in sbs.run_new(p, None)["findings"]}
    for was, now in sbs.RENAMED.items():
        assert was in old_ids and was not in new_ids, f"{was} is not gone from the new tree"
        assert now in new_ids, f"{now} does not fire in the new tree"
    for rule_id in sbs.RETIRED:
        assert rule_id not in new_ids, f"{rule_id} was retired and still fires"


def test_the_comparison_answers_the_four_things_07_asked_for(strong, old_strong):
    text = "\n".join(sbs.render(
        "strong", old_strong,
        sbs.run_new(strong, sbs.new_recorded().get("strong")), "recorded"))
    assert "composite" in text                       # composite, old and new
    assert "why each judged category landed there" in text   # what moved and why
    assert "unmet:" in text
    assert "findings that stopped deducting" in text         # advice-only
    assert "retired, and what replaced them" in text


def test_a_document_nobody_judged_still_compares(fixtures):
    """The owner's resume, and every document in 08's set: no recorded judgement on
    either side, so the comparison is the deterministic layer and says so."""
    path = fixtures["no_phone"]
    old, new = sbs.run_old(path, None), sbs.run_new(path, None)
    assert not new["judged"]
    assert old["composite"] > 0 and new["composite"] > 0
