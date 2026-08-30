# JD corpus

Skill-taxonomy weights are derived from these documents by `scripts/build_taxonomy.py`
rather than hand-asserted, so a weight the corpus does not support is visibly wrong.

## Provenance — read this before trusting the weights

These files are **synthesized composites**, not verbatim job postings. The session that
built this tool could not reach careers sites (blocked by network egress policy), and
republishing full posting text raises copyright questions in any case. Each file states
its own provenance in a header.

The composites are grounded in published 2026 hiring analyses, not invention — notably
that RAG appears in ~65% of applied-LLM listings, that evaluation design (golden
datasets, LLM-as-judge, recall@k before generation eval) is the most consistently
requested and least commonly demonstrated skill, and that deployment capability
(FastAPI, Docker, cloud) separates mid-level candidates from notebook-only ones.

**To ground this properly**: drop real postings into this directory as `.txt` files with
the header format below and re-run `python scripts/build_taxonomy.py`. Real postings
replace composites cleanly — nothing else needs to change. That is the intended path;
what ships here is a defensible starting point, not a substitute.

## Header format

    # source: <url or "composite">
    # retrieved: <YYYY-MM-DD>
    # title: <posting title>
    # level: <junior|mid|senior>

## A different, better path: your own personal corpus

Rather than editing this directory, prefer `corpus/jds/user/` (see its README) --
postings *you* pasted for roles *you're* targeting, added with
`scripts/add_jd.py` and built with `scripts/build_user_corpus.py`. That corpus
replaces this one's taxonomy for your runs entirely once it has any postings in
it, and additionally grounds `ats/jd_digest.json` (target titles, section-aware
requirement weighting, dimension signals) -- this directory and
`scripts/build_taxonomy.py` only ever produce the generic taxonomy.
