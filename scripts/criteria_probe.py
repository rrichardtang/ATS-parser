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

The specs and the band lookup are the rubric itself and live in `ats.rubric`; what is
here is the measurement scaffolding around them. The lookup being shared is what makes
a criterion disagreement a band disagreement only when it crosses a rule boundary --
the property 04 wanted and the thing worth measuring.

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
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats.extract import extract  # noqa: E402
from ats.human import ROLE_IDENTITY_RE  # noqa: E402
from ats.invariants import (  # noqa: E402
    SPECIFIC_TOKEN_RE,
    TEAM_ANYWHERE_RE,
    TEAM_SUBJECT_RE,
    evaluate,
    has_metric,
    portability,
)
from ats.rubric import SLUGS, band_of, leverage, load_spec  # noqa: E402,F401
from ats.sections import Resume, parse  # noqa: E402
from ats.slop import PORTABILITY_LIMIT  # noqa: E402

MEASUREMENT_DIR = ROOT / "docs" / "wayfinder" / "rubric-grounding" / "criteria"
JUDGMENTS_DIR = MEASUREMENT_DIR / "judgments"
PROBES_DIR = MEASUREMENT_DIR / "probes"

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

    plus four that ask about the whole document rather than one bullet, each reusing
    the predicate of the rule that already answers it -- `identity`, `outcome_per_role`,
    `roles_differ`, `unportable`. `Resume craft` needs them because craft is a property
    of a document, not a claim a document does or does not contain.

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

        if kind in DOCUMENT_KINDS:
            yes, evidence = DOCUMENT_KINDS[kind](doc)
            verdict.answers[cid] = yes
            verdict.evidence[cid] = evidence
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


def _says_what_it_is(doc: Doc) -> tuple[bool, str]:
    """`Resume craft` C1, answered where the probe can see it.

    `scan/no-identity-above-fold` runs `ROLE_IDENTITY_RE` over the top third of page
    one, measured from real word boxes. The band probes are text with no geometry, so
    the same regex runs over the summary and everything above the first role -- the
    text a fold would contain.
    """
    resume = doc.resume
    header = resume.summary or ""
    if resume.roles:
        head = doc.text.split(resume.roles[0].heading)[0]
        header = f"{header} {head}"
    match = ROLE_IDENTITY_RE.search(header)
    return (True, f"{match.group(0)!r} above the first role") if match else (False, "")


def _outcome_in_every_role(doc: Doc) -> tuple[bool, str]:
    """`Resume craft` C2: `invariants.evaluate(...).outcome`, per role rather than per
    bullet. 07 left `outcome` to this category after pricing the bundle's other three
    predicates elsewhere."""
    roles = doc.resume.roles
    if not roles:
        return False, ""
    for role in roles:
        if not any(evaluate(b).outcome for b in role.bullets):
            return False, f"no bullet in {role.heading[:40]!r} names a change"
    return True, f"every one of {len(roles)} role(s) has a bullet that names a change"


def _roles_read_differently(doc: Doc) -> tuple[bool, str]:
    """`Resume craft` C4: `_duplicate_bullets`' token overlap, raised to the role.

    The rule compares bullets; two roles can be the same job told twice without any
    single pair crossing 0.8, which is the gap a reader sees and the rule does not.
    """
    roles = doc.resume.roles
    blobs = [({w.lower() for w in re.findall(r"\w+", " ".join(r.bullets)) if len(w) > 3},
              r.heading) for r in roles]
    for i, (left, left_name) in enumerate(blobs):
        for right, right_name in blobs[i + 1:]:
            if not left or not right:
                continue
            if len(left & right) / max(len(left), len(right)) > 0.8:
                return False, f"{left_name[:30]!r} and {right_name[:30]!r} say the same thing"
    return True, f"{len(blobs)} role(s), none a retelling of another"


def _nothing_portable(doc: Doc) -> tuple[bool, str]:
    """`Resume craft` C5: `slop/portable`'s own predicate, as a document-level yes/no."""
    for role in doc.resume.roles:
        for bullet in role.bullets:
            score = portability(bullet)
            if score > PORTABILITY_LIMIT and len(bullet.split()) >= 8 and not has_metric(bullet):
                return False, f"{score:.0%} of \"{bullet[:70]}\" would fit anyone"
    return True, "no bullet survives stripping every name, number and tool"


DOCUMENT_KINDS = {
    "identity": _says_what_it_is,
    "outcome_per_role": _outcome_in_every_role,
    "roles_differ": _roles_read_differently,
    "unportable": _nothing_portable,
}


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
