"""The rubric in `ats.rubric`: the five specs, and the band their answers buy.

Pinned here are the properties the rubric rests on, not the band each document lands
in -- those move whenever the criteria are revised, and they belong to the measurement
in `tests/test_criteria_probe.py`. The lookup must be total and monotone, band values
must ascend, and each of the two lookup shapes has to keep the cost structure the
ticket that chose it argued for.

Every property is parametrised over all five categories. A category added later gets
the whole suite by appearing in `SLUGS`, which is the point: 05 measured the format on
one category, and the properties are what has to hold for the next one.
"""
from itertools import product

import pytest

from ats.rubric import SLUGS, band_of, leverage, load_spec, load_specs, spec_path

SPECS = {slug: load_spec(slug) for slug in SLUGS}
ALL = pytest.mark.parametrize("slug", SLUGS)

# Two lookup shapes, and which one a category has is not a style choice (ticket 12).
# `gated` categories ask whether evidence exists at all, so C1 unmet is the floor and a
# criterion's cost is its position. `count` categories are properties of a whole
# document -- craft is never *absent* -- so the band is a defect count, there is no
# gate, and every criterion costs exactly one band.
GATED = [s for s in SLUGS if SPECS[s].get("shape", "gated") == "gated"]
COUNTED = [s for s in SLUGS if SPECS[s].get("shape", "gated") == "count"]
GATE = pytest.mark.parametrize("slug", GATED)
COUNT = pytest.mark.parametrize("slug", COUNTED)


def _ids(spec):
    return [c["id"] for c in spec["criteria"]]


def _order(spec):
    return [b["label"] for b in spec["bands"]]


def _answers(spec, **overrides):
    base = {cid: False for cid in _ids(spec)}
    base.update(overrides)
    return base


@ALL
def test_the_spec_is_package_data_the_program_can_load(slug):
    """The specs ship inside `ats/`, not in a docs folder the program cannot see."""
    path = spec_path(slug)
    assert path.exists(), path
    assert path.parent.parent.name == "ats", path
    assert SPECS[slug]["slug"] == slug


def test_load_specs_returns_all_five_in_declared_order():
    assert [spec["slug"] for spec in load_specs()] == list(SLUGS)


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
def test_an_incomplete_answer_set_names_no_band(slug):
    """A judge that abstains on a criterion is not a judge that answered it `no`."""
    spec = SPECS[slug]
    partial = _answers(spec)
    partial.pop(_ids(spec)[-1])
    with pytest.raises(SystemExit):
        band_of(partial, spec)


@ALL
def test_band_values_rise_with_the_band(slug):
    """Bands are declared worst-first, so their values must ascend in that order."""
    values = [b["value"] for b in SPECS[slug]["bands"]]
    assert values == sorted(values)
    assert len(set(values)) == len(values)


@GATE
def test_the_gate_criterion_is_the_floor_whatever_else_is_met(slug):
    """C1 unmet is the bottom band in every category, by construction."""
    spec = SPECS[slug]
    everything_but_c1 = _answers(spec, **{cid: True for cid in _ids(spec)[1:]})
    assert band_of(everything_but_c1, spec)["label"] == _order(spec)[0]


@GATE
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


@GATE
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


@COUNT
def test_a_counted_category_has_no_gate_and_no_cheap_seats(slug):
    """The count shape's defining property, and the whole of its cost.

    Every criterion moves the band from the same number of answer sets and none moves
    it by more than one, so there is nowhere cheap to disagree. That is why a category
    with this shape has to answer *more* criteria identically than a gated one to reach
    the same verdict: one split is one adjacent band, always.
    """
    spec = SPECS[slug]
    rows = leverage(spec)
    moves = {cid: count for cid, count, _ in rows}
    widest = {cid: reach for cid, _, reach in rows}
    assert len(set(moves.values())) == 1, moves
    assert set(widest.values()) == {1}, widest
    assert moves["C1"] < 2 ** len(_ids(spec)), "a counted category must have no gate"


@COUNT
def test_a_counted_band_is_the_number_of_criteria_met(slug):
    spec = SPECS[slug]
    ids = _ids(spec)
    order = _order(spec)
    for combo in product([False, True], repeat=len(ids)):
        answers = dict(zip(ids, combo))
        met = sum(answers.values())
        # 0 and 1 share the bottom band; above that each count is its own band.
        expected = order[max(0, met - 1)]
        assert band_of(answers, spec)["label"] == expected, (answers, met)


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
