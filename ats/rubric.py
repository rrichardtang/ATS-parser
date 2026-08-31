"""The rubric: the five category specs, and the band a set of criterion answers buys.

A judge answers **criteria** -- binary, individually quotable evidence questions -- and
the **band** follows from which ones are met. That lookup is the thing this module owns,
and it is data rather than code: each band declares a `when` clause in its spec and
`band_of` evaluates them in declared order, so a sixth category adds a JSON file and no
branches. Ticket 05 wrote the first spec beside a hand-written lookup; four categories
later, four hand-written lookups would have been a totality nobody could check by
reading.

The specs live beside this module in `ats/criteria/`, as package data like
`taxonomy.json` and `weights.toml`. They were written by the `rubric-grounding` map,
whose prose half -- one `*-criteria.md` per category, plus the agreement writeups --
stays in `docs/wayfinder/rubric-grounding/`, and so do the recorded judgments and band
probes that measure them.

What is deliberately *not* here: the deterministic judge in `scripts/criteria_probe.py`
that answers criteria from regexes. It exists to measure criterion agreement, not to
score a resume, and moving it in would put a second, unwired rule channel beside the
real one in `ats/rules.py`.
"""
from __future__ import annotations

import json
from itertools import product
from pathlib import Path

CRITERIA_DIR = Path(__file__).with_name("criteria")

# Declaration order is the order the categories were written, which is also 05's and
# 11's reading order: the worked example first, then the model-owned category whose
# only agreement is criterion agreement, then the two that transfer from it.
SLUGS = (
    "production-ownership",
    "ai-assisted-coding-fluency",
    "evaluation-rigour",
    "agentic-systems",
    "resume-craft",
)


def spec_path(slug: str) -> Path:
    return CRITERIA_DIR / f"{slug}.json"


def load_spec(slug: str = "production-ownership") -> dict:
    spec = json.loads(spec_path(slug).read_text(encoding="utf-8"))
    if spec.get("slug", slug) != slug:
        raise SystemExit(f"{slug}.json declares slug {spec['slug']!r}")
    spec.setdefault("slug", slug)
    return spec


def load_specs() -> list[dict]:
    return [load_spec(slug) for slug in SLUGS]


def slug_by_category() -> dict[str, str]:
    """Category display name -> spec slug, taken from the specs themselves.

    Each spec names its own category, and those names are exactly `models.Category`'s
    values. Deriving the map rather than writing it here keeps this module free of any
    import from the rest of the package -- the specs are the only thing it reads --
    and means a sixth category is reachable by adding a file and a slug.
    """
    return {load_spec(slug)["category"]: slug for slug in SLUGS}


def _clause(clause: dict, met: set[str]) -> bool:
    """One `when` clause: met/unmet/count/any, all of which must hold together."""
    if any(cid not in met for cid in clause.get("met", [])):
        return False
    if any(cid in met for cid in clause.get("unmet", [])):
        return False
    count = clause.get("count")
    if count:
        hits = len([cid for cid in count["of"] if cid in met])
        if "eq" in count and hits != count["eq"]:
            return False
        if "min" in count and hits < count["min"]:
            return False
        if "max" in count and hits > count["max"]:
            return False
    alternatives = clause.get("any")
    if alternatives and not any(_clause(alt, met) for alt in alternatives):
        return False
    return True


def band_of(answers: dict[str, bool], spec: dict) -> dict:
    """The band lookup: first `when` that matches, in declared order.

    Shared by every judge, so only crossings cost agreement. An incomplete answer set
    names no band at all -- a judge that abstains on a criterion and a judge that
    answered it `no` are not the same thing, and a band would hide the difference.
    """
    ids = [c["id"] for c in spec["criteria"]]
    missing = [cid for cid in ids if cid not in answers]
    if missing:
        raise SystemExit(
            f"{spec['slug']}: no band for an incomplete answer set (missing {missing})")
    met = {cid for cid, yes in answers.items() if yes}
    for band in spec["bands"]:
        if _clause(band["when"], met):
            return band
    raise SystemExit(
        f"{spec['slug']}: no band matches {sorted(met)} -- the lookup is not total")


def leverage(spec: dict) -> list[tuple[str, int, int]]:
    """Per criterion: over how many of the 32 answer sets does flipping it move the band?

    04's claim is that criteria are more diagnosable than a band label. This is the
    other half of that claim -- a criterion that almost never moves the band is cheap
    to disagree about, and one that almost always does is where agreement is spent.
    """
    ids = [c["id"] for c in spec["criteria"]]
    order = [b["label"] for b in spec["bands"]]
    rows = []
    for target in ids:
        moves = 0
        combos = list(product([False, True], repeat=len(ids)))
        for combo in combos:
            answers = dict(zip(ids, combo))
            flipped = dict(answers, **{target: not answers[target]})
            if band_of(answers, spec)["label"] != band_of(flipped, spec)["label"]:
                moves += 1
        widest = max(
            abs(order.index(band_of(dict(zip(ids, c)), spec)["label"])
                - order.index(band_of(dict(dict(zip(ids, c)),
                                           **{target: not dict(zip(ids, c))[target]}),
                                      spec)["label"]))
            for c in combos
        )
        rows.append((target, moves, widest))
    return rows
