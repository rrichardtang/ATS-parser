"""What the acceptance set actually covers, measured rather than intended.

08 fixed the rule that makes this set worth anything: **bands are observed, never
targeted**. Nothing about a document is written toward a band, so the only way to know
what the set reaches is to read it afterwards -- which is this.

The judge here is the deterministic one from `scripts/criteria_probe.py`: regexes over
parsed bullets, no provider, no credentials. It is a floor and not a verdict. Two things
follow, and both are the point rather than a limitation to apologise for:

  * where a criterion has no rule channel the judge abstains, so `AI-assisted coding
    fluency` names no band here at all. Per-criterion counts are printed for every
    category for that reason -- they survive an abstention, a band does not.
  * a floor undercounts. A criterion the regexes miss is a criterion a model judge may
    still answer `yes`, so the real spread is at least this wide.

The quotas it checks are 08's:

  * every band reached by at least 3 documents, in every category that can be banded;
  * no band holding more than 40% of the set;
  * no criterion constant across the set -- the failure 02 found on the seven fixtures,
    where `Agentic systems` and `AI-assisted coding fluency` were band E on all of them
    and 22.5 composite points carried no information.

    python scripts/acceptance_coverage.py
    python scripts/acceptance_coverage.py --documents   # per document, per category
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats.rubric import SLUGS, band_of, load_spec  # noqa: E402
from ats.invariants import (  # noqa: E402
    SPECIFIC_TOKEN_RE, TEAM_ANYWHERE_RE, TEAM_SUBJECT_RE,
)
from scripts.criteria_probe import (  # noqa: E402
    HEDGE_RE, NUMBER_RE, _find, _patterns, deterministic_verdict, read_probe,
)

SET_DIR = ROOT / "corpus" / "resumes" / "synthetic"
MIN_PER_BAND = 3
MAX_BAND_SHARE = 0.40
BEHAVIOUR = ("production-ownership", "agentic-systems", "evaluation-rigour",
             "ai-assisted-coding-fluency")
ANCHORED = ("alias_in_anchor", "named_in", "number_in", "unhedged_in")


def anywhere(doc, criterion) -> bool:
    """The same predicate, asked of the whole document instead of one bullet.

    An anchored criterion is answered inside the bullet that settled its anchor, which
    is right for the rubric and severe as a floor: a resume that names its system in
    the next bullet answers `no` here and `yes` from any reader. The gap between the
    two columns is how much of a thin band is the anchor conjunction rather than the
    documents -- the question this set cannot answer for itself, and 09 can.
    """
    bullets = [b for role in doc.resume.roles for b in role.bullets]
    kind = criterion.get("deterministic", {}).get("kind")
    if kind == "alias_in_anchor":
        return bool(_find(_patterns(criterion), bullets))
    if kind == "named_in":
        return any(SPECIFIC_TOKEN_RE.search(b) for b in bullets)
    if kind == "number_in":
        return any(NUMBER_RE.search(b) for b in bullets)
    if kind == "unhedged_in":
        return any(not HEDGE_RE.search(b) and not TEAM_SUBJECT_RE.search(b)
                   and not TEAM_ANYWHERE_RE.search(b) for b in bullets)
    return False


def documents() -> dict[str, Path]:
    return {p.stem: p for p in sorted(SET_DIR.glob("*.txt"))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--documents", action="store_true",
                    help="print the band each document lands in, per category")
    args = ap.parse_args()

    paths = documents()
    if not paths:
        raise SystemExit(f"no documents in {SET_DIR.relative_to(ROOT)}")
    docs = {name: read_probe(path) for name, path in paths.items()}

    unparsed = [n for n, d in docs.items() if not d.answerable]
    print(f"{len(docs)} documents in {SET_DIR.relative_to(ROOT)}; "
          f"{len(docs) - len(unparsed)} parse to at least one role")
    for name in unparsed:
        print(f"  ! {name}: {docs[name].note}")

    failures: list[str] = list(unparsed and
                               [f"{n}: {docs[n].note}" for n in unparsed] or [])
    notes: list[str] = []
    for slug in SLUGS:
        spec = load_spec(slug)
        ids = [c["id"] for c in spec["criteria"]]
        order = [b["label"] for b in spec["bands"]]
        bands: Counter[str] = Counter()
        met: Counter[str] = Counter()
        loose: Counter[str] = Counter()
        answered: Counter[str] = Counter()
        per_doc: dict[str, str] = {}
        for name, doc in docs.items():
            if not doc.answerable:
                continue
            verdict = deterministic_verdict(doc, spec)
            for criterion in spec["criteria"]:
                cid = criterion["id"]
                if cid in verdict.answers:
                    answered[cid] += 1
                    met[cid] += bool(verdict.answers[cid])
                if criterion.get("deterministic", {}).get("kind") in ANCHORED:
                    loose[cid] += anywhere(doc, criterion)
            if verdict.complete(ids):
                label = band_of(verdict.answers, spec)["label"]
                bands[label] += 1
                per_doc[name] = label
            else:
                per_doc[name] = "-"

        total = sum(bands.values())
        print(f"\n=== {spec['category']} ===")
        if not total:
            print("  no band: the deterministic judge abstains on this category "
                  "(no rule channel), so its spread is 09's to measure")
        else:
            spread = "  ".join(f"{label} {bands.get(label, 0)}" for label in order)
            print(f"  bands over {total} documents:  {spread}")
            thin = [label for label in order if bands.get(label, 0) < MIN_PER_BAND]
            if thin:
                notes.append(f"{spec['category']}: band(s) "
                             f"{', '.join(thin)} under {MIN_PER_BAND} documents "
                             "on the floor")
            top, count = bands.most_common(1)[0]
            if count / total > MAX_BAND_SHARE:
                notes.append(f"{spec['category']}: band {top} holds "
                             f"{count}/{total} documents on the floor, over "
                             f"{MAX_BAND_SHARE:.0%}")
        for criterion in spec["criteria"]:
            cid = criterion["id"]
            seen = answered[cid]
            if not seen:
                print(f"  {cid} {criterion['name']:<34} unanswerable by rule")
                continue
            extra = (f"   anywhere {loose[cid]}/{seen}"
                     if criterion.get("deterministic", {}).get("kind") in ANCHORED
                     else "")
            print(f"  {cid} {criterion['name']:<34} met on {met[cid]}/{seen}{extra}")
            if met[cid] in (0, seen):
                line = (f"{spec['category']}/{cid}: constant at "
                        f"{'yes' if met[cid] else 'no'} across all {seen} documents")
                (failures if slug in BEHAVIOUR else notes).append(line)
        if args.documents:
            for name in sorted(per_doc):
                print(f"    {name:<38}{per_doc[name]}")

    print()
    if notes:
        print("notes -- what the floor cannot certify, for 09 to settle:")
        for line in notes:
            print(f"  - {line}")
    if failures:
        print("\nfailures -- draw more briefs, never edit a document:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("\nno criterion is constant in any behaviour category")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
