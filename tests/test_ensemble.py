"""Ensembling, and the reward-hacking defences.

Pass 3 is the only place Goodhart pressure arises, because it is the only pass
whose output is generated in order to win a selection. The ranking/audit split is
what keeps best-of-N honest, so it is tested directly.
"""
import pytest

from ats.ensemble import (
    audit_score,
    combine_scores,
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


def test_score_band_appears_only_on_real_disagreement():
    agree, meta = combine_scores({"a": {"Writing quality": 70}, "b": {"Writing quality": 74}})
    assert meta["disagreements"] == []
    _, meta2 = combine_scores({"a": {"Writing quality": 40}, "b": {"Writing quality": 85}})
    assert meta2["disagreements"]


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
