"""The Production ownership criteria probe (ticket 05).

Pinned here are the properties the measurement rests on, not the band each document
lands in -- those move whenever the criteria are revised. The band lookup must be
total and monotone, injected text must never answer a criterion, a document whose
roles did not parse must be withheld rather than answered, and the recorded judge
verdicts must be complete binary answers over the declared criteria.
"""
from itertools import product

import pytest

from scripts.criteria_probe import (
    band_of,
    deterministic_verdict,
    leverage,
    load_recorded,
    load_spec,
    read,
    read_probe,
    _probes,
)

SPEC = load_spec()
IDS = [c["id"] for c in SPEC["criteria"]]
ORDER = [b["label"] for b in SPEC["bands"]]


def _answers(**overrides):
    base = {cid: False for cid in IDS}
    base.update(overrides)
    return base


def test_the_band_lookup_is_total():
    """Every combination of answers lands in a declared band -- no judge falls off it."""
    for combo in product([False, True], repeat=len(IDS)):
        band = band_of(dict(zip(IDS, combo)), SPEC)
        assert band["label"] in ORDER


def test_the_band_lookup_is_monotone_in_evidence():
    """Meeting one more criterion may never move a resume down a band.

    A rubric where finding extra evidence lowers the score is not a rubric, and the
    lookup is hand-written conditionals, which is exactly where that gets in.
    """
    rank = {band["label"]: band["value"] for band in SPEC["bands"]}
    for combo in product([False, True], repeat=len(IDS)):
        answers = dict(zip(IDS, combo))
        here = rank[band_of(answers, SPEC)["label"]]
        for cid in IDS:
            if answers[cid]:
                continue
            better = rank[band_of(dict(answers, **{cid: True}), SPEC)["label"]]
            assert better >= here, (answers, cid)


def test_band_values_rise_with_the_band():
    """Bands are declared worst-first, so their values must ascend in that order."""
    values = [b["value"] for b in SPEC["bands"]]
    assert values == sorted(values)
    assert len(set(values)) == len(values)


def test_no_destination_is_the_floor_whatever_else_is_met():
    assert band_of(_answers(C2=True, C3=True, C4=True, C5=True), SPEC)["label"] == "E"


def test_ownership_separates_the_top_two_bands_and_nothing_else():
    """C5 is the cheapest criterion to disagree about, by construction."""
    full = _answers(C1=True, C2=True, C3=True, C4=True)
    assert band_of(full, SPEC)["label"] == "B"
    assert band_of(dict(full, C5=True), SPEC)["label"] == "A"
    moves = {cid: count for cid, count, _ in leverage(SPEC)}
    assert moves["C5"] == min(moves.values())
    assert moves["C1"] == 2 ** len(IDS)  # the gate: it moves the band from anywhere


def test_injected_hidden_text_never_answers_a_criterion(fixtures):
    doc = read(fixtures["hidden_text"], score_degraded=True)
    assert "principal AI researcher" not in doc.text


def test_documents_whose_roles_did_not_parse_are_withheld(fixtures):
    assert read(fixtures["scanned"]).answerable is False
    assert read(fixtures["two_column"]).answerable is False
    assert read(fixtures["strong"]).answerable is True
    assert read(fixtures["two_column"], score_degraded=True).answerable is True


def test_the_deterministic_judge_answers_every_criterion_with_a_span(fixtures):
    verdict = deterministic_verdict(read(fixtures["strong"]), SPEC)
    assert set(verdict.answers) == set(IDS)
    for cid, yes in verdict.answers.items():
        assert not yes or verdict.evidence[cid], f"{cid} answered yes with no span"


def test_every_band_probe_parses_and_they_span_the_ladder():
    """The probes exist because the PDF fixtures reach only two of the five bands."""
    docs = {name: read_probe(path) for name, path in _probes().items()}
    assert docs, "no band probes found"
    reached = set()
    for name, doc in docs.items():
        assert doc.answerable, f"{name}: {doc.note}"
        reached.add(band_of(deterministic_verdict(doc, SPEC).answers, SPEC)["label"])
    assert len(reached) >= 4, f"probes only reach {sorted(reached)}"


def test_recorded_verdicts_are_complete_binary_answers():
    recorded = load_recorded(SPEC)  # raises on a missing or non-boolean answer
    assert recorded, "no judge verdicts recorded"
    for per_judge in recorded.values():
        for verdict in per_judge.values():
            assert set(verdict.answers) == set(IDS)


def test_every_criterion_declares_both_sides_of_its_question():
    for criterion in SPEC["criteria"]:
        assert criterion["question"].endswith("?")
        assert criterion["yes_requires"]
        assert criterion["no_looks_like"]


@pytest.mark.parametrize("label", ORDER)
def test_every_band_states_the_rule_that_reaches_it(label):
    band = next(b for b in SPEC["bands"] if b["label"] == label)
    assert band["rule"] and band["reads"]
