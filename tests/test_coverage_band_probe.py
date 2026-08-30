"""The Coverage band probe (ticket 05).

What is worth pinning here is not the fixture scores -- those move whenever the
provisional requirement set does -- but the four rules the measurement rests on:
alias matching does not fire on substrings, injected white-on-white text never
counts toward Coverage, a document whose structure did not parse is withheld
rather than scored, and the point mass per requirement is the number the
acceptance test is really about.
"""
import pytest

from scripts.coverage_band_probe import (
    SCHEMES,
    Verdict,
    _alias_pattern,
    budget_rows,
    deterministic_verdict,
    headroom,
    load_recorded,
    load_requirements,
    read,
    score,
)

REQUIREMENTS = load_requirements()


def test_aliases_match_whole_words_only():
    assert _alias_pattern("rag").search("built a RAG pipeline")
    assert not _alias_pattern("rag").search("object storage tier")
    assert not _alias_pattern("eval").search("evaluation harness")
    # Aliases ending in punctuation still match; a trailing \b would never fire.
    assert _alias_pattern("recall@").search("recall@10 rose to 0.82")


def test_score_is_the_document_frequency_weighted_mean_of_levels():
    all_absent = Verdict("t", levels={r["id"]: "L0" for r in REQUIREMENTS})
    all_demonstrated = Verdict("t", levels={r["id"]: "L3" for r in REQUIREMENTS})
    assert score(all_absent, REQUIREMENTS, "A") == 0.0
    assert score(all_demonstrated, REQUIREMENTS, "A") == 100.0

    heaviest = max(REQUIREMENTS, key=lambda r: r["doc_frequency"])
    one_up = Verdict("t", levels={r["id"]: ("L1" if r["id"] == heaviest["id"] else "L0")
                                  for r in REQUIREMENTS})
    total = sum(r["doc_frequency"] for r in REQUIREMENTS)
    expected = 100 * heaviest["doc_frequency"] * SCHEMES["A"]["L1"] / total
    assert score(one_up, REQUIREMENTS, "A") == pytest.approx(expected, abs=0.05)


def test_injected_hidden_text_never_reaches_a_band(fixtures):
    """The parser gate calls white-on-white injection fraud; Coverage must not pay for it."""
    doc = read(fixtures["hidden_text"], score_degraded=True)
    assert "principal AI researcher" not in doc.text
    verdict = deterministic_verdict(doc, REQUIREMENTS)
    # The injected span names ML, seniority and research and nothing else in this
    # fixture does -- so if it were read, these would not all be absent.
    assert verdict.levels["agents-tool-use"] == "L0"
    assert verdict.levels["evaluation"] == "L0"


def test_coverage_is_withheld_when_the_structure_did_not_survive(fixtures):
    assert read(fixtures["scanned"]).scorable is False
    assert read(fixtures["two_column"]).scorable is False
    assert read(fixtures["strong"]).scorable is True
    # Withholding is a property of the document, so opting out scores it again.
    assert read(fixtures["two_column"], score_degraded=True).scorable is True


def test_a_skills_list_mention_bands_below_the_same_word_inside_a_role(fixtures):
    slop = deterministic_verdict(read(fixtures["slop"]), REQUIREMENTS)
    strong = deterministic_verdict(read(fixtures["strong"]), REQUIREMENTS)
    assert slop.levels["retrieval-rag"] == "L1"   # "RAG" in the skills line
    assert strong.levels["retrieval-rag"] == "L3"  # "RAG pipeline", with the numbers
    assert strong.evidence["retrieval-rag"]


def test_one_level_step_on_the_heaviest_requirement_exhausts_the_tolerance():
    """The finding ticket 05 exists to produce, stated as an assertion.

    The acceptance test allows 5 points between judges. Scheme A's worst single
    level-step costs more than that, so the rubric has no headroom for even one
    requirement two judges read differently.
    """
    worst, under_target, _ = headroom(REQUIREMENTS, "A")
    assert worst > 5.0
    assert under_target == 0


def test_fewer_levels_makes_each_disagreement_more_expensive_not_less():
    assert headroom(REQUIREMENTS, "B")[0] > headroom(REQUIREMENTS, "A")[0]


def test_budget_rows_cover_every_requirement():
    assert {row[0] for row in budget_rows(REQUIREMENTS, "A")} == {r["id"] for r in REQUIREMENTS}


def test_recorded_verdicts_are_complete_and_use_known_ids():
    recorded = load_recorded(REQUIREMENTS)  # raises on an unknown id or a missing level
    assert recorded, "no judge verdicts recorded"
    for per_judge in recorded.values():
        for verdict in per_judge.values():
            assert set(verdict.levels) == {r["id"] for r in REQUIREMENTS}


def test_every_requirement_quotes_one_posting_per_document_it_is_counted_in():
    """doc_frequency is the weight, so an unquoted count is an unweighted opinion."""
    for requirement in REQUIREMENTS:
        assert len(requirement["quotes"]) == requirement["doc_frequency"], requirement["id"]
        assert requirement["aliases"]
