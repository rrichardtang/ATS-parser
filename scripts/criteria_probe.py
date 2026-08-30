"""Ticket 05 probe: answer one category's criteria on the fixtures, two ways.

04 decided the judge answers **criteria** -- binary, individually quotable evidence
questions -- and that the band is a lookup from which ones are met. That moves the
agreement question somewhere new: two judges no longer have to agree about a
category, they have to agree about five yes/no questions, and the band follows.

This probe measures that, for `Production ownership`, without the harness or
provider credentials:

  * `deterministic` answers each criterion from parser-checkable facts alone, using
    the repo's existing regexes where one already exists. It is the floor under any
    judge, and it is also what a `rule_share` channel could ever contribute.
  * recorded judges live in docs/wayfinder/rubric-grounding/criteria/judgments/ and
    are compared against it criterion by criterion.

The band lookup is shared, so a criterion disagreement is only a band disagreement
when it crosses a rule boundary -- which is the property 04 wanted and the thing
worth measuring.

    python scripts/criteria_probe.py           # criteria, bands, agreement
    python scripts/criteria_probe.py --grid    # every answer with the span behind it
    python scripts/criteria_probe.py --leverage  # which criteria can move the band
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from itertools import combinations, product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats.extract import extract  # noqa: E402
from ats.invariants import SPECIFIC_TOKEN_RE, TEAM_ANYWHERE_RE, TEAM_SUBJECT_RE  # noqa: E402
from ats.sections import Resume, parse  # noqa: E402

CRITERIA_DIR = ROOT / "docs" / "wayfinder" / "rubric-grounding" / "criteria"
SPEC_PATH = CRITERIA_DIR / "production-ownership.json"
JUDGMENTS_DIR = CRITERIA_DIR / "judgments"
PROBES_DIR = CRITERIA_DIR / "probes"

# C5's "your part, not the team's". ats.invariants already owns the team-subject half;
# this is the hedge half -- a verb that concedes the work was someone else's.
HEDGE_RE = re.compile(
    r"(?i)^\s*(helped|assisted|contributed|participated|supported|worked|involved|"
    r"collaborated|aided|took part)\b"
)


@dataclass
class Verdict:
    """One judge's answers for one resume, each with the span that settles it."""

    judge: str
    answers: dict[str, bool] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    note: str = ""


@dataclass
class Doc:
    """One fixture, and whether the criteria can be answered on it at all.

    Answerability is a property of the document, never of the judge. Every criterion
    is a question about a bullet inside a role, so on a document whose roles did not
    survive extraction the judges are not reading the same resume -- and the parser
    gate has already found and charged for that defect. Withholding is the honest
    reading; scoring is a second charge for one fault.
    """

    text: str = ""
    resume: Resume | None = None
    answerable: bool = True
    note: str = ""


def load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _alias_pattern(alias: str) -> re.Pattern[str]:
    """Word-boundary match that tolerates aliases ending in punctuation (`req/min`)."""
    body = re.escape(alias)
    lead = r"(?<![A-Za-z0-9])" if alias[:1].isalnum() else ""
    tail = r"(?![A-Za-z0-9])" if alias[-1:].isalnum() else ""
    return re.compile(lead + body + tail, re.IGNORECASE)


def _find(aliases: list[str], bullets: list[str]) -> tuple[str, str] | None:
    patterns = [_alias_pattern(a) for a in aliases]
    for bullet in bullets:
        for pattern in patterns:
            match = pattern.search(bullet)
            if match:
                return bullet, match.group(0)
    return None


def visible_text(pdf_path: Path) -> tuple[str, bool, str]:
    """The text a human sees, whether a text layer existed, and what was cut.

    White-on-white injection is in `doc.text` -- `ats.extract` records the spans but
    does not remove them. A criterion answered off injected text would let the rubric
    reward the one thing the parser gate calls fraud, so it comes out first.
    """
    doc = extract(str(pdf_path))
    text = doc.text
    dropped = 0
    for span in doc.hidden_text:
        if span and span in text:
            text = text.replace(span, " ")
            dropped += 1
    return text, doc.has_text_layer, f"dropped {dropped} hidden span(s)" if dropped else ""


def read_probe(txt_path: Path) -> Doc:
    """A band probe: already-readable text, so a disagreement is about the criterion.

    The seven PDF fixtures test extraction; these test the rubric. Sending them
    through `visible_text` would put a parser between the judges and the sentences
    the criteria ask about, which is the one variable this measurement removes.
    """
    text = txt_path.read_text(encoding="utf-8")
    resume = parse(text)
    if not resume.roles:
        return Doc(text=text, resume=resume, answerable=False,
                   note="probe did not parse; fix the probe, not the rubric")
    return Doc(text=text, resume=resume)


def read(pdf_path: Path, score_degraded: bool = False) -> Doc:
    text, has_text_layer, note = visible_text(pdf_path)
    if not has_text_layer:
        return Doc(text=text, answerable=False, note="no text layer")
    resume = parse(text)
    if not resume.roles and not score_degraded:
        return Doc(text=text, resume=resume, answerable=False,
                   note="no role parsed; the criteria have no bullets to read")
    return Doc(text=text, resume=resume, note=note)


def deterministic_verdict(doc: Doc, spec: dict) -> Verdict:
    """Each criterion answered from what a regex can see. The floor, not the ceiling."""
    bullets = [b for role in doc.resume.roles for b in role.bullets]
    by_id = {c["id"]: c for c in spec["criteria"]}
    verdict = Verdict("deterministic", note=doc.note)

    def record(cid: str, hit: tuple[str, str] | None) -> str | None:
        verdict.answers[cid] = hit is not None
        verdict.evidence[cid] = "" if hit is None else f'{hit[1]!r} in "{hit[0][:100]}"'
        return None if hit is None else hit[0]

    destination = record("C1", _find(by_id["C1"]["aliases"], bullets))
    record("C3", _find(by_id["C3"]["aliases"], bullets))
    record("C4", _find(by_id["C4"]["aliases"], bullets))

    # C2 and C5 are questions about the destination bullet, so they are unanswerable
    # -- and false -- when there is no destination bullet to ask them about.
    named = SPECIFIC_TOKEN_RE.search(destination) if destination else None
    verdict.answers["C2"] = bool(named)
    verdict.evidence["C2"] = f"{named.group(0)!r} names the shipped thing" if named else ""

    owned = bool(
        destination
        and not HEDGE_RE.search(destination)
        and not TEAM_SUBJECT_RE.search(destination)
        and not TEAM_ANYWHERE_RE.search(destination)
    )
    verdict.answers["C5"] = owned
    verdict.evidence["C5"] = (
        f'subject is the candidate in "{destination[:70]}"' if owned
        else ("hedged or team-attributed" if destination else "")
    )
    return verdict


def band_of(answers: dict[str, bool], spec: dict) -> dict:
    """The band lookup. Shared by every judge, so only crossings cost agreement."""
    met = {cid for cid, yes in answers.items() if yes}
    after = len({"C3", "C4"} & met)
    by_label = {b["label"]: b for b in spec["bands"]}
    if "C1" not in met:
        return by_label["E"]
    if "C2" not in met or after == 0:
        return by_label["D"]
    if after == 1:
        return by_label["C"]
    return by_label["A"] if "C5" in met else by_label["B"]


def load_recorded(spec: dict) -> dict[str, dict[str, Verdict]]:
    known = {c["id"] for c in spec["criteria"]}
    out: dict[str, dict[str, Verdict]] = {}
    if not JUDGMENTS_DIR.exists():
        return out
    for path in sorted(JUDGMENTS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        judge = payload["judge"]
        for fixture, body in payload["fixtures"].items():
            answers = body.get("answers", {})
            if set(answers) != known:
                raise SystemExit(
                    f"{path.name}/{fixture}: answers must cover exactly {sorted(known)}")
            if any(not isinstance(v, bool) for v in answers.values()):
                raise SystemExit(f"{path.name}/{fixture}: every answer must be true or false")
            out.setdefault(fixture, {})[judge] = Verdict(
                judge=judge, answers=answers,
                evidence=body.get("evidence", {}), note=body.get("note", ""))
    return out


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


def _fixtures() -> dict[str, Path]:
    from tests.make_fixtures import build_all

    return build_all()


def _probes() -> dict[str, Path]:
    return {p.stem: p for p in sorted(PROBES_DIR.glob("*.txt"))}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--grid", action="store_true",
                        help="print every answer with the span behind it")
    parser.add_argument("--leverage", action="store_true",
                        help="print how often each criterion can move the band")
    parser.add_argument("--only", choices=("fixtures", "probes"), default=None,
                        help="restrict to the PDF fixtures or the band probes")
    parser.add_argument("--score-degraded", action="store_true",
                        help="answer criteria on fixtures whose roles did not parse, "
                             "instead of withholding them")
    args = parser.parse_args()

    spec = load_spec()
    ids = [c["id"] for c in spec["criteria"]]

    if args.leverage:
        combos = 2 ** len(ids)
        print(f"=== how much each criterion can move the band ({combos} answer sets) ===")
        print(f"{'criterion':<12}{'name':<24}{'flips the band':>16}{'widest move':>14}")
        for cid, moves, widest in leverage(spec):
            name = next(c["name"] for c in spec["criteria"] if c["id"] == cid)
            print(f"{cid:<12}{name:<24}{f'{moves}/{combos}':>16}{f'{widest} band(s)':>14}")
        return 0

    recorded = load_recorded(spec)
    docs: dict[str, Doc] = {}
    if args.only != "probes":
        docs.update({n: read(p, score_degraded=args.score_degraded)
                     for n, p in _fixtures().items()})
    if args.only != "fixtures":
        docs.update({n: read_probe(p) for n, p in _probes().items()})
    fixtures = list(docs)

    verdicts: dict[str, dict[str, Verdict]] = {}
    for name in fixtures:
        verdicts[name] = {}
        if docs[name].answerable:
            verdicts[name]["deterministic"] = deterministic_verdict(docs[name], spec)
        verdicts[name].update(recorded.get(name, {}))

    judges = sorted({j for per in verdicts.values() for j in per})
    print("=== Production ownership: band per document ===")
    print(f"{'document':<26}" + "".join(f"{j:>26}" for j in judges) + "   agree")
    for name in fixtures:
        if not docs[name].answerable:
            print(f"{name:<26}" + "".join(f"{'withheld':>26}" for _ in judges)
                  + f"   -   {docs[name].note}")
            continue
        cells, labels = [], []
        for judge in judges:
            verdict = verdicts[name].get(judge)
            if verdict is None:
                cells.append("-")
                continue
            band = band_of(verdict.answers, spec)
            cells.append(f"{band['label']} {band['name']} ({band['value']})")
            labels.append(band["label"])
        agree = "yes" if len(set(labels)) == 1 else "NO"
        print(f"{name:<26}" + "".join(f"{c:>26}" for c in cells) + f"   {agree}")

    order = [b["label"] for b in spec["bands"]]
    for left, right in combinations(judges, 2):
        rows, splits, exact, adjacent, far = 0, [], 0, 0, 0
        for name in fixtures:
            if not docs[name].answerable:
                continue
            a, b = verdicts[name].get(left), verdicts[name].get(right)
            if not a or not b:
                continue
            rows += 1
            split = [cid for cid in ids if a.answers[cid] != b.answers[cid]]
            splits.extend(f"{name}/{cid}" for cid in split)
            gap = abs(order.index(band_of(a.answers, spec)["label"])
                      - order.index(band_of(b.answers, spec)["label"]))
            exact += gap == 0
            adjacent += gap == 1
            far += gap > 1
        if not rows:
            continue
        total = rows * len(ids)
        gate = "FAIL" if far or adjacent > 1 else ("LOOK" if adjacent else "PASS")
        print(f"\n--- {left} vs {right} ---")
        print(f"criteria: {total - len(splits)}/{total} answered the same"
              + (f"; split on {', '.join(splits)}" if splits else ""))
        print(f"bands: {exact} exact, {adjacent} adjacent, {far} far, over {rows} "
              f"documents -> {gate}")

    if args.grid:
        print("\n=== every answer, and the span behind it ===")
        for name in fixtures:
            print(f"\n{name}")
            if not docs[name].answerable:
                print(f"  withheld -- {docs[name].note}")
            for judge, verdict in verdicts[name].items():
                note = f"  ({verdict.note})" if verdict.note else ""
                band = band_of(verdict.answers, spec)
                print(f"  {judge}{note} -> band {band['label']} ({band['value']})")
                for criterion in spec["criteria"]:
                    cid = criterion["id"]
                    mark = "yes" if verdict.answers[cid] else " no"
                    print(f"    {cid} {mark}  {criterion['name']:<24}"
                          f"{verdict.evidence.get(cid, '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
