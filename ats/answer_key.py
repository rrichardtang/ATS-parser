"""A judge scored against the owner's answers rather than against another judge.

Ticket 15, 28 September: two judges that each agree with themselves but not with each
other cannot be settled by agreement, so the owner labelled the disagreements. An entry
names a document, a criterion and the owner's answer; a scoped criterion's entry also
names a place, and is compared with the judge's answer at that place (the `places` list
`passes.derive_scoped` keeps on the item), not with the derived answer.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import passes
from .agreement import HarnessRun

KEY = Path(__file__).resolve().parents[1] / "corpus" / "resumes" / "answer_key.json"
MISSING = "missing"


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["entries"]


@dataclass
class Score:
    judge: str
    matched: int = 0
    mismatches: list[tuple[dict, str]] = field(default_factory=list)

    @property
    def scored(self) -> int:
        return self.matched + len(self.mismatches)


def _item(categories: dict, entry: dict) -> dict | None:
    for name, body in categories.items():
        category = passes._category(name)
        if not category or passes.criteria_index()[category][0] != entry["category"]:
            continue
        items = body.get("criteria") if isinstance(body, dict) else None
        return next((i for i in items or [] if isinstance(i, dict)
                     and str(i.get("id") or "").strip().upper() == entry["criterion"]), None)
    return None


def judge_answer(categories: dict, entry: dict) -> str:
    """"yes", "no", or `MISSING` when the judge gave no readable answer there."""
    item = _item(categories, entry) or {}
    if "locator" in entry:
        places = item.get("places") if isinstance(item.get("places"), list) else []
        item = passes._place_answers(places, {entry["locator"]}).get(entry["locator"], {})
    met = passes._met(item.get("answer"))
    return MISSING if met is None else "yes" if met else "no"


def score(run: HarnessRun, entries: list[dict]) -> list[Score]:
    """One score per provider sample. A sample with no judgement on a judged document
    answered none of its key items, so each counts as a missing answer."""
    samples = sorted({(j.provider, j.sample) for r in run.resumes for j in r.judgments})
    scores = {s: Score(f"{s[0]} sample {s[1]}") for s in samples}
    for resume in run.resumes:
        if resume.skipped:
            continue
        judged = {(j.provider, j.sample): j.categories for j in resume.judgments}
        for entry in (e for e in entries if e["doc"] == resume.name):
            for sample, result in scores.items():
                answer = judge_answer(judged.get(sample, {}), entry)
                if answer == entry["answer"]:
                    result.matched += 1
                else:
                    result.mismatches.append((entry, answer))
    return list(scores.values())


def render(scores: list[Score], entries: list[dict], path: Path) -> str:
    out = [f"Against the answer key ({path.name}, {len(entries)} items)"]
    for result in scores:
        out.append(f"  {result.judge:<22} {result.matched}/{result.scored} matched")
        out += [f"    {e['doc']} / {e['category']}/{e['criterion']} / {e.get('locator', '-')}"
                f" / key {e['answer']} vs judge {answer}"
                for e, answer in result.mismatches]
    return "\n".join(out)
