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
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats.models import DERIVED_CATEGORIES  # noqa: E402
from ats.invariants import SPECIFIC_TOKEN_RE  # noqa: E402
from ats.rubric import SLUGS, band_of, load_spec, slug_by_category  # noqa: E402
from scripts.criteria_probe import (  # noqa: E402
    NUMBER_RE, Doc, _find, _patterns, deterministic_verdict, owned, read_probe,
)
from scripts.make_acceptance_set import SET_DIR, documents  # noqa: E402

MIN_PER_BAND = 3
MAX_BAND_SHARE = 0.40
# The behaviour categories are the corpus-derived ones, so a fifth one derived later
# is checked here without anybody remembering to add it.
BEHAVIOUR = tuple(slug_by_category()[c.value] for c in DERIVED_CATEGORIES)


def anywhere(doc: Doc, criterion: dict) -> bool | None:
    """The same predicate, asked of the whole document instead of one bullet.

    An anchored criterion is answered inside the bullet that settled its anchor, which
    is right for the rubric and severe as a floor: a resume that names its system in
    the next bullet answers `no` here and `yes` from any reader. The gap between the
    two columns is how much of a thin band is the anchor conjunction rather than the
    documents -- the question this set cannot answer for itself, and 09 can.

    None for a criterion that is not anchored, which has no second column.
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
        return any(owned(b) for b in bullets)
    return None


@dataclass
class Tally:
    """One category's deterministic answers over the set, counted once."""

    met: Counter = field(default_factory=Counter)
    answered: Counter = field(default_factory=Counter)
    anywhere: dict[str, int] = field(default_factory=dict)
    bands: dict[str, str] = field(default_factory=dict)   # document -> band, or "-"

    def constants(self) -> dict[str, bool]:
        """Criteria answered the same way on every document, and which way."""
        return {cid: bool(self.met[cid]) for cid, seen in self.answered.items()
                if self.met[cid] in (0, seen)}


def tally(docs: dict[str, Doc], spec: dict) -> Tally:
    """Every parsed document through the deterministic judge, for one category."""
    ids = [c["id"] for c in spec["criteria"]]
    out = Tally()
    for name, doc in docs.items():
        if not doc.answerable:
            continue
        verdict = deterministic_verdict(doc, spec)
        for criterion in spec["criteria"]:
            cid = criterion["id"]
            if cid in verdict.answers:
                out.answered[cid] += 1
                out.met[cid] += bool(verdict.answers[cid])
            hit = anywhere(doc, criterion)
            if hit is not None:
                out.anywhere[cid] = out.anywhere.get(cid, 0) + hit
        out.bands[name] = (band_of(verdict.answers, spec)["label"]
                           if verdict.complete(ids) else "-")
    return out


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

    failures = [f"{n}: {docs[n].note}" for n in unparsed]
    notes: list[str] = []
    for slug in SLUGS:
        spec = load_spec(slug)
        order = [b["label"] for b in spec["bands"]]
        counts = tally(docs, spec)
        bands = Counter(label for label in counts.bands.values() if label != "-")

        total = sum(bands.values())
        print(f"\n=== {spec['category']} ===")
        if not total:
            print("  no band: the deterministic judge abstains on this category "
                  "(no rule channel), so its spread is 09's to measure")
        else:
            spread = "  ".join(f"{label} {bands[label]}" for label in order)
            print(f"  bands over {total} documents:  {spread}")
            thin = [label for label in order if bands[label] < MIN_PER_BAND]
            if thin:
                notes.append(f"{spec['category']}: band(s) "
                             f"{', '.join(thin)} under {MIN_PER_BAND} documents "
                             "on the floor")
            top, count = bands.most_common(1)[0]
            if count / total > MAX_BAND_SHARE:
                notes.append(f"{spec['category']}: band {top} holds "
                             f"{count}/{total} documents on the floor, over "
                             f"{MAX_BAND_SHARE:.0%}")
        constants = counts.constants()
        for criterion in spec["criteria"]:
            cid = criterion["id"]
            seen = counts.answered[cid]
            if not seen:
                print(f"  {cid} {criterion['name']:<34} unanswerable by rule")
                continue
            extra = (f"   anywhere {counts.anywhere[cid]}/{seen}"
                     if cid in counts.anywhere else "")
            print(f"  {cid} {criterion['name']:<34} "
                  f"met on {counts.met[cid]}/{seen}{extra}")
            if cid in constants:
                line = (f"{spec['category']}/{cid}: constant at "
                        f"{'yes' if constants[cid] else 'no'} across all {seen} documents")
                (failures if slug in BEHAVIOUR else notes).append(line)
        if args.documents:
            for name in sorted(counts.bands):
                print(f"    {name:<38}{counts.bands[name]}")

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
