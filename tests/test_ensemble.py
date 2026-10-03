"""Ensembling, and the reward-hacking defences.

Pass 3 is the only place Goodhart pressure arises, because it is the only pass
whose output is generated in order to win a selection. The ranking/audit split is
what keeps best-of-N honest, so it is tested directly.
"""
import concurrent.futures

import pytest

from ats import config, ensemble
from ats.rubric import load_spec
from ats.sections import Resume, Role
from ats.ensemble import (
    audit_clean,
    audit_score,
    combine_bands,
    combine_slop,
    filter_slop,
    gather,
    rank_score,
    select_rewrite,
)

ORIGINAL = "Worked on the retrieval system to improve search quality for our users."

HONEST = (
    "Rebuilt hybrid retrieval with BM25 plus a cross-encoder reranker, raising "
    "recall@10 from [add: baseline] to [add: result]."
)

HACKS = {
    "vacuous number": "Collaborated with 4 engineers and 3 teams on 2 retrieval projects.",
    "invented figure": "Improved search quality by 47% using advanced retrieval.",
    "truncation": "Rebuilt retrieval.",
    "proper-noun padding": "Rebuilt Elasticsearch Pinecone Weaviate Qdrant FAISS retrieval quality.",
}


@pytest.mark.parametrize("label,text", sorted(HACKS.items()))
def test_each_hack_trips_an_audit_signal(label, text):
    score, problems = audit_score(ORIGINAL, text)
    assert problems, f"{label} passed the audit undetected"


def test_honest_rewrite_passes_the_audit_cleanly():
    """Placeholders are the correct response to a missing metric, not a defect."""
    score, problems = audit_score(ORIGINAL, HONEST)
    assert problems == []
    assert score == 100.0


def test_identifier_digits_are_not_invented_figures():
    """BM25 and recall@10 carry digits that assert nothing about results."""
    _, problems = audit_score("Built retrieval.", "Built BM25 retrieval with recall@10 and GPT-4o.")
    assert problems == []


LOC = "exp[0].bullet[0]"


def _resume(bullet=ORIGINAL):
    return Resume(roles=[Role(heading="Eng", bullets=[bullet])])


def _select(candidates, bullet=ORIGINAL, judged=False):
    return select_rewrite(_resume(bullet), LOC, [(t, "c", "openai") for t in candidates], judged)


# ORIGINAL fires content/no-outcome, content/weak-opener and slop/portable.
KEEPS_EVERY_DEFECT = "Worked on the retrieval system to improve search quality for all our users."
FIXES_ONE = "Rebuilt the retrieval system to improve search quality for our users."
FIXES_TWO = "Rebuilt the retrieval system and improved search quality for our users."
FIXES_ONE_ADDS_ONE = "Rebuilt the retrieval system and I improved search quality for our users."


def test_best_of_n_picks_the_honest_candidate():
    winner, meta = _select([HONEST, *HACKS.values()])
    assert winner.rewritten == HONEST
    assert meta["rejections"] == {"audit rejected": len(HACKS)}


def test_hacked_candidates_alone_produce_no_rewrite():
    """Failing to improve is acceptable. Shipping a hacked rewrite is not."""
    winner, meta = _select(list(HACKS.values()))
    assert winner is None
    assert meta["reason"] == "audit rejected"


def test_hacking_signature_is_detected_and_recorded():
    """A defect fixed with a falling audit score is the signature."""
    _, meta = _select(["Improved search quality by 47% using advanced retrieval."])
    assert meta.get("hack_detected") is True


def test_a_candidate_that_keeps_every_deterministic_defect_is_blocked():
    winner, meta = _select([KEEPS_EVERY_DEFECT])
    assert winner is None and meta["reason"] == "fixed nothing"


def test_a_candidate_that_fixes_one_defect_but_adds_another_is_blocked():
    winner, meta = _select([FIXES_ONE_ADDS_ONE])
    assert winner is None and meta["reason"] == "new defect"


def test_fixing_one_of_several_defects_is_enough_to_ship():
    winner, _ = _select([FIXES_ONE])
    assert winner.rewritten == FIXES_ONE


def test_a_content_only_target_ships_the_judges_top_clean_candidate_without_a_margin():
    """No deterministic defect fires on this bullet, so the judge's order decides,
    even for a candidate that scores no better than the original on rank_score."""
    original = "Cut p99 latency 40% by moving ranking to a BM25 plus cross-encoder pipeline."
    top = "Cut p99 latency 40% by moving ranking onto a BM25 plus cross-encoder pipeline."
    runner_up = "Cut p99 latency 40% by moving ranking to a BM25 and cross-encoder pipeline."
    assert ensemble.bullet_defects(_resume(original), LOC) == set()
    assert rank_score(top) <= rank_score(original)
    winner, _ = _select([top, runner_up], original, judged=True)
    assert winner.rewritten == top


def test_without_the_judge_the_candidate_fixing_most_defects_wins():
    winner, _ = _select([FIXES_ONE, FIXES_TWO, HONEST])
    assert winner.rewritten == HONEST


def test_the_judges_order_beats_defects_fixed():
    winner, _ = _select([FIXES_ONE, HONEST], judged=True)
    assert winner.rewritten == FIXES_ONE


@pytest.mark.parametrize("mode", ["economy", "default", "thorough"])
def test_no_mode_carries_a_rewrite_margin(mode):
    assert "rewrite_margin" not in config.ensemble_settings(mode)


# --- audit_clean: the fact-check filter that runs before any quality judgment ---

def test_audit_clean_keeps_the_honest_candidate_and_drops_every_hack():
    candidates = [(HONEST, "named the mechanism", "anthropic", "mechanism")] + [
        (text, "changed", "openai", "outcome") for text in HACKS.values()
    ]
    clean = audit_clean(ORIGINAL, candidates)
    assert [c["text"] for c in clean] == [HONEST]


def test_audit_clean_returns_empty_when_nothing_passes():
    candidates = [(t, "c", "openai", "outcome") for t in HACKS.values()]
    assert audit_clean(ORIGINAL, candidates) == []


def test_audit_clean_drops_a_candidate_identical_to_the_original():
    assert audit_clean(ORIGINAL, [(ORIGINAL, "c", "openai", "outcome")]) == []


# --- combination rules -----------------------------------------------------

def _item(quote, pattern="puffery"):
    return {"pattern": pattern, "quoted_line": quote, "fix": "cut it"}


def test_same_model_voting_drops_a_lone_finding():
    """One model, N samples: a finding seen once is probably sampling noise."""
    per_provider = {"openai": [[_item("alpha")], [_item("alpha")], [_item("beta")]]}
    kept, meta = combine_slop(per_provider, vote_k=2)
    quotes = {k["quoted_line"] for k in kept}
    assert "alpha" in quotes and "beta" not in quotes


def test_cross_provider_keeps_single_model_findings():
    """Two providers: a lone finding is plausibly a blindspot catch, so union.

    A model is weakest at flagging its own idiom. Intersecting would discard
    exactly the findings that make holding two keys worthwhile.
    """
    per_provider = {
        "anthropic": [[_item("alpha")], [_item("alpha")]],
        "openai": [[_item("gamma")], [_item("gamma")]],
    }
    kept, meta = combine_slop(per_provider, vote_k=2)
    quotes = {k["quoted_line"]: k["confidence"] for k in kept}
    assert quotes == {"alpha": "medium", "gamma": "medium"}
    assert meta["rule"] == "union across providers"


def test_agreement_across_providers_is_high_confidence():
    per_provider = {
        "anthropic": [[_item("alpha")]],
        "openai": [[_item("alpha")]],
    }
    kept, _ = combine_slop(per_provider, vote_k=1)
    assert kept[0]["confidence"] == "high"
    assert sorted(kept[0]["providers"]) == ["anthropic", "openai"]


def test_unquotable_findings_are_discarded():
    resume = "Cut p99 latency 380ms to 95ms with vLLM."
    items = [_item("Cut p99 latency 380ms"), _item("a line that is not in the resume")]
    assert len(filter_slop(items, resume)) == 1


def _po(*met):
    return {f"C{i}": f"C{i}" in met for i in range(1, 6)}


def test_one_judge_names_a_band_and_contests_nothing():
    judged = combine_bands(load_spec("production-ownership"), [_po("C1", "C2", "C3")])
    assert (judged.band, judged.value) == ("C", 58.0)
    assert not judged.contested and judged.split_criteria == []


def test_the_lower_band_wins_and_the_higher_one_is_still_named():
    """06's rule. C3 is the only split, and it is the one that crosses a boundary."""
    judged = combine_bands(load_spec("production-ownership"),
                           [_po("C1", "C2", "C3"), _po("C1", "C2")])
    assert (judged.band, judged.value) == ("D", 35.0)
    assert (judged.high_band, judged.high_value) == ("C", 58.0)
    assert judged.contested and judged.gap == 1
    assert judged.split_criteria == ["production-ownership/C3"]
    assert "Built, not operated" in judged.reads_as()
    assert "Shipped" in judged.reads_as()


def test_a_split_the_lookup_absorbs_is_recorded_but_not_contested():
    """04's claim, in one assertion: only a split that crosses a rule boundary costs a
    band. C5 does not move a resume that is already below band B."""
    judged = combine_bands(load_spec("production-ownership"),
                           [_po("C1", "C2", "C5"), _po("C1", "C2")])
    assert not judged.contested and judged.gap == 0
    assert judged.split_criteria == ["production-ownership/C5"]
    assert judged.reads_as() == ""


def test_the_merge_never_lands_below_a_band_both_judges_agreed_on():
    """The measured case against intersecting the answers instead of the bands.

    Both judges met three of `Resume craft`'s five criteria -- band C either way -- but
    not the same three. Intersecting gives two criteria, which is band D: a markdown
    for a disagreement neither judge reported.
    """
    craft = load_spec("resume-craft")
    left = {"C1": True, "C2": True, "C3": True, "C4": False, "C5": False}
    right = {"C1": True, "C2": True, "C3": False, "C4": False, "C5": True}
    judged = combine_bands(craft, [left, right])
    assert judged.band == "C" and not judged.contested
    intersected = {cid: left[cid] and right[cid] for cid in left}
    from ats.rubric import band_of
    assert band_of(intersected, craft)["label"] == "D"


def test_an_incomplete_answer_set_names_no_band():
    """`band_of` refuses to band an abstention, so a judge that abstained is dropped
    rather than read as having answered `no`."""
    partial = {"C1": True, "C2": True}
    assert combine_bands(load_spec("production-ownership"), [partial]) is None
    judged = combine_bands(load_spec("production-ownership"),
                           [partial, _po("C1", "C2", "C3")])
    assert judged.judges == 1 and judged.band == "C" and not judged.contested


def test_degrades_when_a_provider_returns_nothing():
    kept, _ = combine_slop({"anthropic": [[_item("alpha")], [_item("alpha")]], "openai": []}, 2)
    assert [k["quoted_line"] for k in kept] == ["alpha"]


def test_raising_n_never_ships_a_hack():
    """The empirical ceiling check, run on scripts/hacking_sweep.py's own core.

    More candidates means more chances for a cheat to clear the gate. Shipping
    rate may rise; hacks shipped must stay at zero.
    """
    import random

    from scripts import hacking_sweep

    rng = random.Random(11)
    for n in hacking_sweep.NS:
        winners = hacking_sweep.shipped(n, 25, rng)
        assert winners, f"nothing shipped at N={n}"
        assert not {w.rewritten for w in winners} & set(hacking_sweep.HACKS)
        assert {w.audit_score for w in winners} == {100.0}


def test_a_call_past_the_timeout_is_a_failed_call_not_a_crash():
    """`as_completed` raised TimeoutError out of the pool, which then waited for the
    slow call anyway and lost every result already in hand."""
    import threading
    import time

    from ats.ensemble import gather

    release = threading.Event()
    started = time.monotonic()
    results, errors = gather([lambda: "fast", lambda: release.wait(5)], timeout=1)
    release.set()
    assert results == ["fast"]
    assert errors == ["timed out after 1s"]
    assert time.monotonic() - started < 3, "gather waited for the slow call"


def test_a_future_finishing_between_the_take_loop_and_the_late_count_is_classified(monkeypatch):
    """A future still running when the deadline branch looks at it, but done by the
    time the late calls are counted, must land in results or errors, not neither."""
    class FinishesAfterFirstLook:
        looks = 0

        def done(self):
            self.looks += 1
            return self.looks > 1

    class Pool:
        def __init__(self, max_workers):
            pass

        def submit(self, fn, *args):
            return FinishesAfterFirstLook()

        def shutdown(self, wait, cancel_futures):
            pass

    def deadline(fs, timeout=None):
        raise concurrent.futures.TimeoutError

    monkeypatch.setattr(ensemble.concurrent.futures, "ThreadPoolExecutor", Pool)
    monkeypatch.setattr(ensemble.concurrent.futures, "as_completed", deadline)

    assert gather([lambda: 1], timeout=1) == ([], ["timed out after 1s"])


@pytest.mark.parametrize("answers, voted", [
    ([True, True, False], True),
    ([False, False, True], False),
    ([True, False, None], False),
    ([True, None, None], True),
    ([True, None], True),
    ([True, True, None], True),
    ([False, None, None], False),
    ([None, None, None], None),
    ([True], True),
    ([False], False),
    ([None], None),
])
def test_tries_vote_by_majority_of_those_that_answered_and_a_tie_is_no(answers, voted):
    assert ensemble.vote(answers) is voted
