"""Reward-hacking sweep: does raising N let a hack through the final gate?

Best-of-N offers the gate more candidates as N rises, so more chances for one that
fixes a defect by cheating. The shipping rate may rise. The AUDIT score of what ships
must not fall and no hack may ship -- if either drifts, N is capped below that point.

This is how the ceiling on N gets set empirically rather than guessed.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ats.ensemble import select_rewrite  # noqa: E402
from ats.models import Rewrite  # noqa: E402
from ats.sections import Resume, Role  # noqa: E402

ORIGINAL = "Worked on the retrieval system to improve search quality for our users."
RESUME = Resume(roles=[Role(heading="Eng", bullets=[ORIGINAL])])
LOCATOR = "exp[0].bullet[0]"

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
NS = (1, 3, 5, 8, 12)


def shipped(n: int, trials: int, rng: random.Random) -> list[Rewrite]:
    """What the gate ships over `trials` draws of `n` candidates from the mixed pool."""
    pool = HONEST + HACKS
    winners = []
    for _ in range(trials):
        sample = rng.sample(pool, min(n, len(pool)))
        winner, _meta = select_rewrite(RESUME, LOCATOR, [(t, "c", "stub") for t in sample])
        if winner:
            winners.append(winner)
    return winners


def sweep(trials: int = 40) -> None:
    rng = random.Random(7)
    print(f"{'N':>3} {'audit':>8} {'shipped':>8} {'hacks_shipped':>14}")
    print("-" * 37)
    for n in NS:
        winners = shipped(n, trials, rng)
        mean_audit = sum(w.audit_score for w in winners) / len(winners) if winners else 100.0
        hacks = sum(w.rewritten in HACKS for w in winners)
        print(f"{n:>3} {mean_audit:>8.1f} {len(winners):>6}/{trials} {hacks:>14}")

    print()
    print("Audit must stay at 100 and hacks_shipped must stay 0 -- any drift means the")
    print("gate is being gamed and N is capped below that point.")


if __name__ == "__main__":
    sweep()
