"""The criteria probes: Production ownership (05) and the other three (11).

Pinned here are the properties the measurement rests on, not the band each document
lands in -- those move whenever the criteria are revised. The band lookup must be
total and monotone, injected text must never answer a criterion, a document whose
roles did not parse must be withheld rather than answered, and the recorded judge
verdicts must be complete binary answers over the declared criteria.

Every property is parametrised over all four categories. A category added later gets
the whole suite by appearing in `SLUGS`, which is the point: 05 measured the format on
one category, and the properties are what has to hold for the next one.
"""
from itertools import product

import pytest

from scripts.criteria_probe import (
    SLUGS,
    band_of,
    deterministic_verdict,
    leverage,
    load_recorded,
    load_spec,
    read,
    read_probe,
    _probes,
)

SPECS = {slug: load_spec(slug) for slug in SLUGS}
ALL = pytest.mark.parametrize("slug", SLUGS)


def _ids(spec):
    return [c["id"] for c in spec["criteria"]]


def _order(spec):
    return [b["label"] for b in spec["bands"]]


def _answers(spec, **overrides):
    base = {cid: False for cid in _ids(spec)}
    base.update(overrides)
    return base


@ALL
def test_the_band_lookup_is_total(slug):
    """Every combination of answers lands in a declared band -- no judge falls off it."""
    spec = SPECS[slug]
    ids, order = _ids(spec), _order(spec)
    for combo in product([False, True], repeat=len(ids)):
        assert band_of(dict(zip(ids, combo)), spec)["label"] in order


@ALL
def test_the_band_lookup_is_monotone_in_evidence(slug):
    """Meeting one more criterion may never move a resume down a band.

    A rubric where finding extra evidence lowers the score is not a rubric, and the
    lookup is declared as ordered rules, which is exactly where that gets in.
    """
    spec = SPECS[slug]
    ids = _ids(spec)
    rank = {band["label"]: band["value"] for band in spec["bands"]}
    for combo in product([False, True], repeat=len(ids)):
        answers = dict(zip(ids, combo))
        here = rank[band_of(answers, spec)["label"]]
        for cid in ids:
            if answers[cid]:
                continue
            better = rank[band_of(dict(answers, **{cid: True}), spec)["label"]]
            assert better >= here, (slug, answers, cid)


@ALL
def test_band_values_rise_with_the_band(slug):
    """Bands are declared worst-first, so their values must ascend in that order."""
    values = [b["value"] for b in SPECS[slug]["bands"]]
    assert values == sorted(values)
    assert len(set(values)) == len(values)


@ALL
def test_the_gate_criterion_is_the_floor_whatever_else_is_met(slug):
    """C1 unmet is the bottom band in every category, by construction."""
    spec = SPECS[slug]
    everything_but_c1 = _answers(spec, **{cid: True for cid in _ids(spec)[1:]})
    assert band_of(everything_but_c1, spec)["label"] == _order(spec)[0]


@ALL
def test_the_gate_is_c1_and_it_moves_the_band_from_anywhere(slug):
    """05's leverage finding, made a property.

    A category's agreement is its gate criterion's agreement, so the gate has to be
    the question the wording budget was spent on. It is C1 in all four, which is why
    the criteria are declared gate-first.
    """
    spec = SPECS[slug]
    moves = {cid: count for cid, count, _ in leverage(spec)}
    assert moves["C1"] == 2 ** len(_ids(spec))
    assert moves["C1"] == max(moves.values())


@ALL
def test_the_least_reliable_criterion_sits_in_the_cheapest_position(slug):
    """C5 is the judgment call in every set, so it must cost at most one band.

    05: 'a category whose gate is its hardest question will not converge however well
    it is worded.' This is the other end of the same table.
    """
    spec = SPECS[slug]
    widest = {cid: reach for cid, _, reach in leverage(spec)}
    moves = {cid: count for cid, count, _ in leverage(spec)}
    assert widest["C5"] == 1
    assert moves["C5"] == min(moves.values())


@ALL
def test_every_criterion_declares_both_sides_of_its_question(slug):
    for criterion in SPECS[slug]["criteria"]:
        assert criterion["question"].endswith("?")
        assert criterion["yes_requires"]
        assert criterion["no_looks_like"]


@ALL
def test_every_band_states_the_rule_that_reaches_it(slug):
    for band in SPECS[slug]["bands"]:
        assert band["rule"] and band["reads"] and band["when"]


@ALL
def test_recorded_verdicts_are_complete_binary_answers(slug):
    spec = SPECS[slug]
    recorded = load_recorded(spec)  # raises on a missing or non-boolean answer
    assert recorded, f"no judge verdicts recorded for {slug}"
    for per_judge in recorded.values():
        for verdict in per_judge.values():
            assert set(verdict.answers) == set(_ids(spec))


@ALL
def test_every_band_probe_parses_and_they_span_the_ladder(slug):
    """The probes exist because the PDF fixtures reach only two of the five bands."""
    spec = SPECS[slug]
    docs = {name: read_probe(path) for name, path in _probes(slug).items()}
    assert docs, f"no band probes found for {slug}"
    reached = set()
    for name, doc in docs.items():
        assert doc.answerable, f"{slug}/{name}: {doc.note}"
        verdict = deterministic_verdict(doc, spec)
        if verdict.complete(_ids(spec)):
            reached.add(band_of(verdict.answers, spec)["label"])
    recorded = load_recorded(spec)
    for name in docs:
        for verdict in recorded.get(name, {}).values():
            reached.add(band_of(verdict.answers, spec)["label"])
    assert len(reached) >= 4, f"{slug} probes only reach {sorted(reached)}"


@ALL
def test_the_deterministic_judge_answers_with_a_span_or_abstains(slug, fixtures):
    """Every `yes` carries the text behind it; a criterion with no rule channel abstains.

    The abstention is `AI-assisted coding fluency`'s C5. 04 set that category's
    rule_share to 0; answering `no` there would make an absent channel look like a
    judge that read the resume and found nothing.
    """
    spec = SPECS[slug]
    verdict = deterministic_verdict(read(fixtures["strong"]), spec)
    for criterion in spec["criteria"]:
        cid = criterion["id"]
        if criterion.get("deterministic", {}).get("kind") == "none":
            assert cid not in verdict.answers
            assert "unanswerable" in verdict.evidence[cid]
        else:
            assert cid in verdict.answers
            assert not verdict.answers[cid] or verdict.evidence[cid]


@ALL
def test_injected_hidden_text_never_answers_a_criterion(slug, fixtures):
    doc = read(fixtures["hidden_text"], score_degraded=True)
    assert "principal AI researcher" not in doc.text


@ALL
def test_documents_whose_roles_did_not_parse_are_withheld(slug, fixtures):
    assert read(fixtures["scanned"]).answerable is False
    assert read(fixtures["two_column"]).answerable is False
    assert read(fixtures["strong"]).answerable is True
    assert read(fixtures["two_column"], score_degraded=True).answerable is True


def test_ownership_separates_the_top_two_bands_and_nothing_else():
    """05's worked example, pinned where it was written."""
    spec = SPECS["production-ownership"]
    full = _answers(spec, C1=True, C2=True, C3=True, C4=True)
    assert band_of(full, spec)["label"] == "B"
    assert band_of(dict(full, C5=True), spec)["label"] == "A"


def test_the_ai_coding_category_has_no_rule_channel_for_its_top_criterion():
    """04's rule_share 0, as a property of the spec rather than a number beside it."""
    spec = SPECS["ai-assisted-coding-fluency"]
    assert spec["rule_share"] == 0
    c5 = next(c for c in spec["criteria"] if c["id"] == "C5")
    assert c5["deterministic"]["kind"] == "none"
