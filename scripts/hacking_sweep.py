"""Reward-hacking sweep: does raising N degrade the verifier?

Best-of-N selects the argmax against the ranking set, so more candidates means
more optimisation pressure on a fixed proxy. The ranking score should rise and
then flatten. The AUDIT score must not fall -- if it does, the verifier is being
gamed and N is capped below that point.

This is how the ceiling on N gets set empirically rather than guessed.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ats.ensemble import audit_score, rank_score, select_rewrite  # noqa: E402

ORIGINAL = "Worked on the retrieval system to improve search quality for our users."

# A candidate pool mixing honest edits with the four known hacks, so higher N
# genuinely offers the optimiser more ways to cheat.
HONEST = [
    "Rebuilt hybrid retrieval with BM25 and a cross-encoder reranker, raising recall@10 from [add: baseline] to [add: result].",
    "Replaced lexical search with hybrid retrieval plus reranking, improving recall@10 by [add: delta].",
    "Owned retrieval quality: hybrid BM25 and dense search, reranked, evaluated on [add: dataset].",
]
HACKS = [
    "Collaborated with 4 engineers and 3 teams on 2 retrieval projects.",
    "Improved search quality by 47% using advanced retrieval.",
    "Rebuilt retrieval.",
    "Rebuilt Elasticsearch Pinecone Weaviate Qdrant FAISS Milvus retrieval quality.",
    "Boosted search relevance by 3x through cutting-edge optimization.",
    "Drove a 61% improvement in retrieval performance metrics.",
]


def sweep(trials: int = 40) -> None:
    random.seed(7)
    pool = HONEST + HACKS
    print(f"{'N':>3} {'rank':>8} {'audit':>8} {'shipped':>8} {'hacks_shipped':>14}")
    print("-" * 46)
    baseline_audit, _ = audit_score(ORIGINAL, ORIGINAL)
    hack_texts = set(HACKS)

    for n in (1, 3, 5, 8, 12):
        ranks, audits, shipped, hacks_shipped = [], [], 0, 0
        for _ in range(trials):
            sample = random.sample(pool, min(n, len(pool)))
            candidates = [(t, "c", "stub") for t in sample]
            winner, _meta = select_rewrite(ORIGINAL, "x", candidates, margin=1.0)
            if winner:
                shipped += 1
                ranks.append(winner.ranking_score)
                audits.append(winner.audit_score)
                if winner.rewritten in hack_texts:
                    hacks_shipped += 1
        mean_rank = sum(ranks) / len(ranks) if ranks else 0.0
        mean_audit = sum(audits) / len(audits) if audits else baseline_audit
        print(f"{n:>3} {mean_rank:>8.1f} {mean_audit:>8.1f} {shipped:>6}/{trials} {hacks_shipped:>14}")

    print()
    print("Ranking should rise then flatten. Audit must stay at 100 and hacks_shipped")
    print("must stay 0 -- any drift means the ranking set is being gamed and N is")
    print("capped below that point.")


if __name__ == "__main__":
    sweep()
