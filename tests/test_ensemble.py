"""Ensembling, and the reward-hacking defences.

Pass 3 is the only place Goodhart pressure arises, because it is the only pass
whose output is generated in order to win a selection. The ranking/audit split is
what keeps best-of-N honest, so it is tested directly.
"""
import pytest

from ats.rubric import load_spec
from ats.ensemble import (
    audit_clean,
    audit_score,
    combine_bands,
    combine_slop,
    filter_slop,
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


def test_best_of_n_picks_the_honest_candidate():
    candidates = [(HONEST, "named the mechanism", "anthropic")] + [
        (text, "changed", "openai") for text in HACKS.values()
    ]
    winner, meta = select_rewrite(ORIGINAL, "exp[0].bullet[0]", candidates, margin=1.0)
    assert winner is not None
    assert winner.rewritten == HONEST
    assert len(meta["rejected_for_audit"]) >= 3


def test_hacked_candidates_alone_produce_no_rewrite():
    """If nothing beats the original honestly, the original is kept.

    Failing to improve is acceptable. Shipping a hacked rewrite is not.
    """
    candidates = [(t, "c", "openai") for t in HACKS.values()]
    winner, meta = select_rewrite(ORIGINAL, "exp[0].bullet[0]", candidates, margin=1.0)
    assert winner is None
    assert "reason" in meta


def test_hacking_signature_is_detected_and_recorded():
    """Rising ranking score with falling audit score is the signature."""
    hacked = "Improved search quality by 47% using advanced retrieval."
    assert rank_score(hacked) > rank_score(ORIGINAL)
    assert audit_score(ORIGINAL, hacked)[0] < 100.0
    _, meta = select_rewrite(ORIGINAL, "x", [(hacked, "c", "openai")], margin=1.0)
    assert meta.get("hack_detected") is True


def test_margin_requires_beating_the_original_not_just_siblings():
    weak = "Worked on the retrieval system to improve search quality for users."
    winner, _ = select_rewrite(ORIGINAL, "x", [(weak, "c", "openai")], margin=5.0)
    assert winner is None


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
    """The empirical ceiling check, in miniature.

    More candidates means more optimisation pressure on a fixed proxy. Shipping
    rate may rise; hacks shipped must stay at zero.
    """
    import random

    from ats.ensemble import select_rewrite

    random.seed(11)
    honest = HONEST
    pool = [honest] + list(HACKS.values())
    for n in (1, 3, 6):
        for _ in range(25):
            sample = random.sample(pool, min(n, len(pool)))
            winner, _ = select_rewrite(
                ORIGINAL, "x", [(t, "c", "stub") for t in sample], margin=1.0
            )
            if winner:
                assert winner.rewritten not in HACKS.values(), (
                    f"a hacked candidate shipped at N={n}"
                )
                assert winner.audit_score == 100.0
