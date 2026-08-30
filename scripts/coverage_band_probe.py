"""Ticket 05 probe: apply the Coverage bands to the fixtures and measure agreement.

This is not the agreement harness (ticket 06). It answers the narrower question 05
asks -- can a band definition be written tightly enough that two judges land within
5 points -- without waiting on the harness or on provider credentials.

It does that by splitting the question in two:

  1. How much of a Coverage score is *forced* by the resume? The deterministic judge
     below applies the bands using only facts a parser can check: does an alias of the
     requirement appear, is the appearance inside a role, does that bullet carry a
     metric. Every level it assigns comes with the span it read.

  2. How much can two judges differ even when both apply the bands correctly? That is
     arithmetic, not an experiment: with weighted requirements the point mass of one
     requirement is fixed, so the cost of one level-step disagreement is computable
     exactly. `--budget` prints it.

Recorded verdicts from other judges live in docs/wayfinder/rubric-grounding/coverage/
judgments/*.json and are compared pairwise against the deterministic judge.

    python scripts/coverage_band_probe.py            # score table + agreement
    python scripts/coverage_band_probe.py --budget   # the per-requirement point mass
    python scripts/coverage_band_probe.py --grid     # per-requirement levels, with evidence
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats.extract import extract  # noqa: E402
from ats.invariants import has_metric  # noqa: E402
from ats.sections import Resume, parse  # noqa: E402

COVERAGE_DIR = ROOT / "docs" / "wayfinder" / "rubric-grounding" / "coverage"
REQUIREMENTS_PATH = COVERAGE_DIR / "requirements.json"
JUDGMENTS_DIR = COVERAGE_DIR / "judgments"

# The two level schemes ticket 05 put on trial. A is the first draft; B is what the
# measured budget forced. See ../coverage-bands.md for why each boundary is where it is.
SCHEMES: dict[str, dict[str, float]] = {
    "A": {"L0": 0.00, "L1": 0.25, "L2": 0.60, "L3": 1.00},
    "B": {"L0": 0.00, "L1": 0.35, "L2": 1.00, "L3": 1.00},
}

# Coverage is a content category. Scoring it on a document the parser could not read
# manufactures a number out of nothing, so it is withheld rather than defaulted to 0.
# The test is the parser gate's own -- ats.extract sets has_text_layer -- rather than a
# second threshold that could disagree with it.


@dataclass
class Verdict:
    """One judge's reading of one resume: a level per requirement, with the span read."""

    judge: str
    levels: dict[str, str] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    note: str = ""


@dataclass
class Doc:
    """One fixture, and whether Coverage may be scored on it at all.

    Scorability is a property of the document, never of the judge. Both bands that
    matter -- "inside a role" and "named only in a skills list" -- are statements
    about resume structure, so on a document whose structure did not survive
    extraction the bands have nothing to bind to and every judge is reading a
    different resume. Withholding there is the finding; scoring it is a number
    invented from a parse failure.
    """

    text: str = ""
    resume: Resume | None = None
    scorable: bool = True
    note: str = ""


def load_requirements() -> list[dict]:
    return json.loads(REQUIREMENTS_PATH.read_text(encoding="utf-8"))["requirements"]


def _alias_pattern(alias: str) -> re.Pattern[str]:
    """Word-boundary match that tolerates aliases ending in punctuation (`recall@`)."""
    body = re.escape(alias)
    lead = r"(?<![A-Za-z0-9])" if alias[:1].isalnum() else ""
    tail = r"(?![A-Za-z0-9])" if alias[-1:].isalnum() else ""
    return re.compile(lead + body + tail, re.IGNORECASE)


def _first_hit(patterns: list[re.Pattern[str]], spans: list[str]) -> tuple[str, str] | None:
    """The first (span, matched alias) any of these aliases lands in."""
    for span in spans:
        for pattern in patterns:
            match = pattern.search(span)
            if match:
                return span, match.group(0)
    return None


def visible_text(pdf_path: Path) -> tuple[str, bool, str]:
    """The text a human sees, whether there was a text layer at all, and what was cut.

    White-on-white keyword injection is in `doc.text`. Counting it toward Coverage
    would make the rubric reward the one thing the parser gate calls fraud, so the
    hidden spans come out before any requirement is matched.
    """
    doc = extract(str(pdf_path))
    text = doc.text
    dropped = []
    for span in doc.hidden_text:
        if span and span in text:
            text = text.replace(span, " ")
            dropped.append(span)
    note = f"dropped {len(dropped)} hidden span(s)" if dropped else ""
    return text, doc.has_text_layer, note


def read(pdf_path: Path, score_degraded: bool = False) -> Doc:
    """Extract one fixture and decide whether its structure can carry the bands."""
    text, has_text_layer, note = visible_text(pdf_path)
    if not has_text_layer:
        return Doc(text=text, scorable=False, note="no text layer")
    resume = parse(text)
    if not resume.roles and not score_degraded:
        return Doc(text=text, resume=resume, scorable=False,
                   note="no role parsed; bands have no structure to bind to")
    return Doc(text=text, resume=resume, note=note)


def deterministic_verdict(doc: Doc, requirements: list[dict]) -> Verdict:
    """Levels assigned from parser-checkable facts alone -- the floor under any judge."""
    text, resume = doc.text, doc.resume
    in_role: list[str] = []
    with_metric: list[str] = []
    for role in resume.roles:
        in_role.append(role.heading)
        for bullet in role.bullets:
            in_role.append(bullet)
            if has_metric(bullet):
                with_metric.append(bullet)

    verdict = Verdict("deterministic", note=doc.note)
    for requirement in requirements:
        patterns = [_alias_pattern(a) for a in requirement["aliases"]]
        hit = _first_hit(patterns, with_metric)
        level = "L3"
        if hit is None:
            hit, level = _first_hit(patterns, in_role), "L2"
        if hit is None:
            hit, level = _first_hit(patterns, [text]), "L1"
        if hit is None:
            level = "L0"
            verdict.levels[requirement["id"]] = level
            verdict.evidence[requirement["id"]] = ""
            continue
        span, alias = hit
        verdict.levels[requirement["id"]] = level
        verdict.evidence[requirement["id"]] = f'{alias!r} in "{span.strip()[:110]}"'
    return verdict


def score(verdict: Verdict, requirements: list[dict], scheme: str) -> float:
    """Coverage = weighted mean of the per-requirement levels, on 0-100."""
    values = SCHEMES[scheme]
    earned = sum(r["doc_frequency"] * values[verdict.levels.get(r["id"], "L0")]
                 for r in requirements)
    possible = sum(r["doc_frequency"] for r in requirements)
    return round(100.0 * earned / possible, 1)


def load_recorded(requirements: list[dict]) -> dict[str, dict[str, Verdict]]:
    """Verdicts written down by judges the probe cannot call: {fixture: {judge: v}}."""
    known = {r["id"] for r in requirements}
    out: dict[str, dict[str, Verdict]] = {}
    if not JUDGMENTS_DIR.exists():
        return out
    for path in sorted(JUDGMENTS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        judge = payload["judge"]
        for fixture, body in payload["fixtures"].items():
            levels = body.get("levels", {})
            unknown = set(levels) - known
            if unknown:
                raise SystemExit(f"{path.name}: unknown requirement ids {sorted(unknown)}")
            missing = known - set(levels)
            if missing:
                raise SystemExit(f"{path.name}/{fixture}: no level for {sorted(missing)}")
            bad = set(levels.values()) - set(SCHEMES["A"])
            if bad:
                raise SystemExit(f"{path.name}/{fixture}: unknown levels {sorted(bad)}")
            out.setdefault(fixture, {})[judge] = Verdict(
                judge=judge,
                levels=levels,
                evidence=body.get("evidence", {}),
                note=body.get("note", ""),
            )
    return out


def headroom(requirements: list[dict], scheme: str) -> tuple[float, int, int]:
    """Worst-case cost of one level-step, and how many fit under the two thresholds.

    The acceptance test is stated in points, so this is the whole question in one
    line: how many times may two judges read one requirement differently before the
    rubric fails its own test.
    """
    steps = [cost for _, _, _, pairs in budget_rows(requirements, scheme)
             for _, cost in pairs]
    worst = max(steps)
    return worst, int(5 // worst), int(8 // worst)


def budget_rows(requirements: list[dict], scheme: str) -> list[tuple]:
    """What one level-step disagreement costs, per requirement. The whole question."""
    values = SCHEMES[scheme]
    possible = sum(r["doc_frequency"] for r in requirements)
    order = ["L0", "L1", "L2", "L3"]
    rows = []
    for requirement in requirements:
        mass = 100.0 * requirement["doc_frequency"] / possible
        steps = []
        for low, high in zip(order, order[1:]):
            delta = values[high] - values[low]
            if delta:
                steps.append((f"{low}->{high}", round(mass * delta, 1)))
        rows.append((requirement["id"], requirement["doc_frequency"], round(mass, 1), steps))
    return rows


def _fixtures() -> dict[str, Path]:
    from tests.make_fixtures import build_all

    return build_all()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scheme", choices=sorted(SCHEMES), default=None,
                        help="level scheme to report (default: both)")
    parser.add_argument("--budget", action="store_true",
                        help="print what one level-step disagreement costs per requirement")
    parser.add_argument("--grid", action="store_true",
                        help="print every requirement's level and the span it was read from")
    parser.add_argument("--score-degraded", action="store_true",
                        help="score fixtures whose roles did not parse, instead of "
                             "withholding them -- reproduces the failing measurement")
    args = parser.parse_args()

    requirements = load_requirements()
    schemes = [args.scheme] if args.scheme else sorted(SCHEMES)

    if args.budget:
        for scheme in schemes:
            print(f"\n=== scheme {scheme}: point mass and step cost "
                  f"({', '.join(f'{k}={v}' for k, v in SCHEMES[scheme].items())}) ===")
            print(f"{'requirement':<26}{'df':>3}{'pts':>7}   one-step disagreement costs")
            for rid, df, mass, steps in budget_rows(requirements, scheme):
                detail = "  ".join(f"{name} {cost:>4}" for name, cost in steps)
                print(f"{rid:<26}{df:>3}{mass:>7}   {detail}")
            worst, under_pass, under_fail = headroom(requirements, scheme)
            print(f"worst single step {worst} points -> {under_pass} such disagreement(s) "
                  f"fit under the 5-point target, {under_fail} under the 8-point failure line")
        return 0

    fixtures = _fixtures()
    recorded = load_recorded(requirements)

    docs: dict[str, Doc] = {}
    verdicts: dict[str, dict[str, Verdict]] = {}
    for name, path in fixtures.items():
        docs[name] = read(path, score_degraded=args.score_degraded)
        verdicts[name] = {}
        if docs[name].scorable:
            verdicts[name]["deterministic"] = deterministic_verdict(docs[name], requirements)
        verdicts[name].update(recorded.get(name, {}))

    for scheme in schemes:
        judges = sorted({j for per in verdicts.values() for j in per})
        print(f"\n=== scheme {scheme}: Coverage per fixture ===")
        print(f"{'fixture':<18}" + "".join(f"{j:>16}" for j in judges) + f"{'spread':>9}")
        for name in fixtures:
            if not docs[name].scorable:
                cells = ["withheld"] * len(judges)
                print(f"{name:<18}" + "".join(f"{c:>16}" for c in cells)
                      + f"{'-':>9}   {docs[name].note}")
                continue
            cells, scores = [], []
            for judge in judges:
                verdict = verdicts[name].get(judge)
                if verdict is None:
                    cells.append("-")
                    continue
                value = score(verdict, requirements, scheme)
                cells.append(f"{value:.1f}")
                scores.append(value)
            spread = f"{max(scores) - min(scores):.1f}" if len(scores) > 1 else "-"
            print(f"{name:<18}" + "".join(f"{c:>16}" for c in cells) + f"{spread:>9}")

        pairs = list(combinations(judges, 2))
        if pairs:
            print(f"\n--- pairwise agreement (scheme {scheme}) ---")
            for left, right in pairs:
                spreads, flips, compared = [], 0, 0
                for name in fixtures:
                    if not docs[name].scorable:
                        continue
                    a, b = verdicts[name].get(left), verdicts[name].get(right)
                    if not a or not b:
                        continue
                    x, y = score(a, requirements, scheme), score(b, requirements, scheme)
                    compared += 1
                    spreads.append(abs(x - y))
                    flips += sum(1 for r in requirements
                                 if a.levels.get(r["id"]) != b.levels.get(r["id"]))
                if not compared:
                    continue
                worst = max(spreads)
                gate = "PASS" if worst <= 5 else ("LOOK" if worst <= 8 else "FAIL")
                print(f"{left} vs {right}: {compared} scored fixtures, "
                      f"max spread {worst:.1f}, mean {sum(spreads) / len(spreads):.1f}, "
                      f"{flips} level disagreement{'' if flips == 1 else 's'} -> {gate}")

    if args.grid:
        print("\n=== levels, and the span each was read from ===")
        for name in fixtures:
            print(f"\n{name}")
            if not docs[name].scorable:
                print(f"  withheld -- {docs[name].note}")
            for judge, verdict in verdicts[name].items():
                note = f"  ({verdict.note})" if verdict.note else ""
                print(f"  {judge}{note}")
                for requirement in requirements:
                    rid = requirement["id"]
                    print(f"    {verdict.levels[rid]}  {rid:<26}"
                          f"{verdict.evidence.get(rid, '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
