"""Answer a category's criteria on the fixtures and band probes, two ways.

04 decided the judge answers **criteria** -- binary, individually quotable evidence
questions -- and that the band is a lookup from which ones are met. That moves the
agreement question somewhere new: two judges no longer have to agree about a
category, they have to agree about five yes/no questions, and the band follows.

This probe measures that, per category, without the harness or provider
credentials:

  * `deterministic` answers each criterion from parser-checkable facts alone, using
    the repo's existing regexes where one already exists. It is the floor under any
    judge, and it is also what a `rule_share` channel could ever contribute. Where no
    rule channel can exist it abstains rather than answering `no`, and then names no
    band -- see `Verdict.complete`.
  * recorded judges live in docs/wayfinder/rubric-grounding/criteria/judgments/<slug>/
    and are compared against it criterion by criterion.

The band lookup is shared, so a criterion disagreement is only a band disagreement
when it crosses a rule boundary -- which is the property 04 wanted and the thing
worth measuring.

Ticket 05 wrote `Production ownership`; ticket 11 added the other three behaviour
categories. The band lookup is data (`when` clauses in the spec) rather than code, so
adding a category adds no branches here.

    python scripts/criteria_probe.py                       # every category
    python scripts/criteria_probe.py -c evaluation-rigour  # one of them
    python scripts/criteria_probe.py --grid       # every answer with the span behind it
    python scripts/criteria_probe.py --leverage   # which criteria can move the band
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
JUDGMENTS_DIR = CRITERIA_DIR / "judgments"
PROBES_DIR = CRITERIA_DIR / "probes"

# Declaration order is the order the categories were written, which is also 05's and
# 11's reading order: the worked example first, then the model-owned category whose
# only agreement is criterion agreement, then the two that transfer from it.
SLUGS = (
    "production-ownership",
    "ai-assisted-coding-fluency",
    "evaluation-rigour",
    "agentic-systems",
)

NUMBER_RE = re.compile(r"\d")

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

    def complete(self, ids: list[str]) -> bool:
        """A judge that cannot answer every criterion cannot name a band.

        `AI-assisted coding fluency` is why this exists. 04 set its `rule_share` to 0
        because no rule channel can answer its questions; C5 is the criterion where
        that bites, so the deterministic judge declares it unanswerable rather than
        voting `no`. A judge that abstains and a judge that answers `no` look the same
        in a band, and they are not the same thing.
        """
        return all(cid in self.answers for cid in ids)


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


def _alias_pattern(alias: str) -> re.Pattern[str]:
    """Word-boundary match that tolerates aliases ending in punctuation (`req/min`)."""
    body = re.escape(alias)
    lead = r"(?<![A-Za-z0-9])" if alias[:1].isalnum() else ""
    tail = r"(?![A-Za-z0-9])" if alias[-1:].isalnum() else ""
    return re.compile(lead + body + tail, re.IGNORECASE)


def _patterns(criterion: dict) -> list[re.Pattern[str]]:
    """A criterion's vocabulary: word-boundary aliases, plus any raw patterns.

    `alias_patterns` exists for phrasings no word list reaches. The case that forced
    it: "raised groundedness from 71% to 88%" is the commonest way a resume states a
    comparison, and its only fixed tokens are `from` and `to`, which as aliases would
    fire on every bullet in every resume.
    """
    return ([_alias_pattern(a) for a in criterion.get("aliases", [])]
            + [re.compile(p, re.IGNORECASE) for p in criterion.get("alias_patterns", [])])


def _find(patterns: list[re.Pattern[str]], bullets: list[str]) -> tuple[str, str] | None:
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
    """Each criterion answered from what a regex can see. The floor, not the ceiling.

    Each criterion declares how it is answered in its `deterministic` block, so a new
    category adds data rather than a branch. Five kinds, and the last four all exist
    because a criterion asks about the *same bullet* another criterion was answered on:

      none             -- no rule channel exists; always `no`, and says so
      alias            -- any bullet matching this criterion's aliases
      alias_in_anchor  -- this criterion's aliases, inside the anchor's bullet
      number_in        -- a digit inside the anchor's bullet
      named_in         -- `SPECIFIC_TOKEN_RE` inside the anchor's bullet
      unhedged_in      -- the anchor's bullet is not hedged or team-attributed

    An anchored criterion whose anchor was answered `no` has no bullet to read, so it
    is `no` too. That is a fact about the questions, not a scoring choice: "is the
    shipped thing named" has no answer when nothing shipped.
    """
    bullets = [b for role in doc.resume.roles for b in role.bullets]
    verdict = Verdict("deterministic", note=doc.note)
    anchors: dict[str, str | None] = {}

    for criterion in spec["criteria"]:
        cid = criterion["id"]
        how = criterion.get("deterministic", {"kind": "alias"})
        kind = how["kind"]
        anchor = anchors.get(how.get("anchor", ""))
        yes, evidence = False, ""

        # A criterion that presupposes another one has no subject when that one is
        # unmet: "what could the agent reach" is not a question about a resume with
        # no agent in it. Without this the alias families answer yes off any bullet.
        required = how.get("requires")
        if required and not verdict.answers.get(required):
            verdict.answers[cid] = False
            verdict.evidence[cid] = f"no {required} to ask about"
            anchors[cid] = None
            continue

        if kind == "none":
            verdict.evidence[cid] = "unanswerable: no rule channel exists here"
            anchors[cid] = None
            continue
        elif kind == "alias":
            hit = _find(_patterns(criterion), bullets)
            if hit:
                yes, evidence = True, f'{hit[1]!r} in "{hit[0][:100]}"'
                anchors[cid] = hit[0]
        elif kind == "alias_in_anchor":
            hit = _find(_patterns(criterion), [anchor]) if anchor else None
            if hit:
                yes, evidence = True, f'{hit[1]!r} in the {how["anchor"]} bullet'
                anchors[cid] = hit[0]
        elif kind == "number_in":
            match = NUMBER_RE.search(anchor) if anchor else None
            if match:
                yes, evidence = True, f'a number in "{anchor[:80]}"'
                anchors[cid] = anchor
        elif kind == "named_in":
            match = SPECIFIC_TOKEN_RE.search(anchor) if anchor else None
            if match:
                yes, evidence = True, f"{match.group(0)!r} names the thing"
                anchors[cid] = anchor
        elif kind == "unhedged_in":
            owned = bool(
                anchor
                and not HEDGE_RE.search(anchor)
                and not TEAM_SUBJECT_RE.search(anchor)
                and not TEAM_ANYWHERE_RE.search(anchor)
            )
            if owned:
                yes, evidence = True, f'subject is the candidate in "{anchor[:70]}"'
                anchors[cid] = anchor
            elif anchor:
                evidence = "hedged or team-attributed"
        else:
            raise SystemExit(f"{spec['slug']}/{cid}: unknown deterministic kind {kind!r}")

        verdict.answers[cid] = yes
        verdict.evidence[cid] = evidence
        anchors.setdefault(cid, None)
    return verdict


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

    Shared by every judge, so only crossings cost agreement. The clauses are data in
    the spec rather than conditionals here -- 05 wrote the rules as prose beside a
    hand-written lookup, and a second, third and fourth category would have made that
    four hand-written lookups whose totality nobody could check by reading.
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


def load_recorded(spec: dict) -> dict[str, dict[str, Verdict]]:
    known = {c["id"] for c in spec["criteria"]}
    out: dict[str, dict[str, Verdict]] = {}
    directory = JUDGMENTS_DIR / spec["slug"]
    if not directory.exists():
        return out
    for path in sorted(directory.glob("*.json")):
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


def _probes(slug: str) -> dict[str, Path]:
    return {p.stem: p for p in sorted((PROBES_DIR / slug).glob("*.txt"))}


def report(spec: dict, fixture_paths: dict[str, Path], args) -> None:
    """One category: bands per document, criterion agreement, and the gate."""
    ids = [c["id"] for c in spec["criteria"]]
    docs: dict[str, Doc] = {}
    if args.only != "probes":
        docs.update({n: read(p, score_degraded=args.score_degraded)
                     for n, p in fixture_paths.items()})
    if args.only != "fixtures":
        docs.update({n: read_probe(p) for n, p in _probes(spec["slug"]).items()})
    fixtures = list(docs)

    recorded = load_recorded(spec)
    verdicts: dict[str, dict[str, Verdict]] = {}
    for name in fixtures:
        verdicts[name] = {}
        if docs[name].answerable:
            verdicts[name]["deterministic"] = deterministic_verdict(docs[name], spec)
        verdicts[name].update(recorded.get(name, {}))

    judges = sorted({j for per in verdicts.values() for j in per})
    print(f"=== {spec['category']}: band per document ===")
    print(f"{'document':<26}" + "".join(f"{j:>30}" for j in judges) + "   agree")
    for name in fixtures:
        if not docs[name].answerable:
            print(f"{name:<26}" + "".join(f"{'withheld':>30}" for _ in judges)
                  + f"   -   {docs[name].note}")
            continue
        cells, labels = [], []
        for judge in judges:
            verdict = verdicts[name].get(judge)
            if verdict is None:
                cells.append("-")
                continue
            if not verdict.complete(ids):
                cells.append("no band (abstains)")
                continue
            band = band_of(verdict.answers, spec)
            cells.append(f"{band['label']} {band['name']} ({band['value']})")
            labels.append(band["label"])
        agree = "yes" if len(set(labels)) == 1 else "NO"
        if len(labels) < 2:
            agree = "-"
        print(f"{name:<26}" + "".join(f"{c:>30}" for c in cells) + f"   {agree}")

    order = [b["label"] for b in spec["bands"]]
    for left, right in combinations(judges, 2):
        rows, splits, exact, adjacent, far = 0, [], 0, 0, 0
        compared, banded, abstained = 0, 0, set()
        for name in fixtures:
            if not docs[name].answerable:
                continue
            a, b = verdicts[name].get(left), verdicts[name].get(right)
            if not a or not b:
                continue
            rows += 1
            shared = [cid for cid in ids if cid in a.answers and cid in b.answers]
            compared += len(shared)
            abstained.update(cid for cid in ids if cid not in shared)
            splits.extend(f"{name}/{cid}" for cid in shared
                          if a.answers[cid] != b.answers[cid])
            if not (a.complete(ids) and b.complete(ids)):
                continue
            banded += 1
            gap = abs(order.index(band_of(a.answers, spec)["label"])
                      - order.index(band_of(b.answers, spec)["label"]))
            exact += gap == 0
            adjacent += gap == 1
            far += gap > 1
        if not rows:
            continue
        print(f"\n--- {left} vs {right} ---")
        print(f"criteria: {compared - len(splits)}/{compared} answered the same"
              + (f"; split on {', '.join(splits)}" if splits else ""))
        if abstained:
            print(f"          {', '.join(sorted(abstained))} not compared -- one judge "
                  f"declares it unanswerable, over {rows} documents")
        if not banded:
            print("bands: not comparable -- no document has two complete answer sets")
            continue
        gate = "FAIL" if far or adjacent > 1 else ("LOOK" if adjacent else "PASS")
        print(f"bands: {exact} exact, {adjacent} adjacent, {far} far, over {banded} "
              f"documents -> {gate}")

    if args.grid:
        print("\n=== every answer, and the span behind it ===")
        for name in fixtures:
            print(f"\n{name}")
            if not docs[name].answerable:
                print(f"  withheld -- {docs[name].note}")
            for judge, verdict in verdicts[name].items():
                note = f"  ({verdict.note})" if verdict.note else ""
                if verdict.complete(ids):
                    band = band_of(verdict.answers, spec)
                    where = f"band {band['label']} ({band['value']})"
                else:
                    where = "no band -- abstains on a criterion"
                print(f"  {judge}{note} -> {where}")
                for criterion in spec["criteria"]:
                    cid = criterion["id"]
                    mark = ("yes" if verdict.answers[cid] else " no") \
                        if cid in verdict.answers else "  -"
                    print(f"    {cid} {mark}  {criterion['name']:<38}"
                          f"{verdict.evidence.get(cid, '')}")


def print_leverage(spec: dict) -> None:
    ids = [c["id"] for c in spec["criteria"]]
    combos = 2 ** len(ids)
    print(f"=== {spec['category']}: how much each criterion can move the band "
          f"({combos} answer sets) ===")
    print(f"{'criterion':<12}{'name':<38}{'flips the band':>16}"
          f"{'widest move':>14}")
    for cid, moves, widest in leverage(spec):
        name = next(c["name"] for c in spec["criteria"] if c["id"] == cid)
        print(f"{cid:<12}{name:<38}{f'{moves}/{combos}':>16}{f'{widest} band(s)':>14}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-c", "--category", choices=SLUGS, action="append", default=None,
                        help="restrict to one category (repeatable); default is all")
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

    specs = [load_spec(slug) for slug in (args.category or SLUGS)]

    if args.leverage:
        for index, spec in enumerate(specs):
            if index:
                print()
            print_leverage(spec)
        return 0

    fixture_paths = {} if args.only == "probes" else _fixtures()
    for index, spec in enumerate(specs):
        if index:
            print()
        report(spec, fixture_paths, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
