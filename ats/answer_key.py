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

from . import ensemble, passes
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


def _item(categories: dict, entry: dict) -> dict:
    for name, body in categories.items():
        category = passes._category(name)
        if category and passes.criteria_index()[category][0] == entry["category"]:
            return next(iter(passes.criterion_items(body, entry["criterion"])), {})
    return {}


def _place_answer(places: list | None, locator: str) -> bool | None:
    found = passes._place_answers(places or [], {locator}).get(locator, {})
    return passes._met(found.get("answer"))


def judge_answer(categories: dict, entry: dict) -> str:
    """"yes", "no", or `MISSING` when the judge gave no readable answer there.

    A voted sample keeps every try's per-place answers under "try_places", and the keyed
    place is voted across them as the criterion was. A run saved before that carries
    only the copied try's "places"."""
    item = _item(categories, entry)
    if "locator" not in entry:
        met = passes._met(item.get("answer"))
    elif "try_places" in item:
        met = ensemble.vote([_place_answer(p, entry["locator"]) for p in item["try_places"]])
    else:
        met = _place_answer(item.get("places"), entry["locator"])
    return MISSING if met is None else "yes" if met else "no"


def _samples(run: HarnessRun) -> list[tuple[str, int]]:
    """Every (provider, sample) the run planned, so one that answered nothing anywhere
    still gets its line. A run saved before samples were counted per provider names
    only the samples it has judgements for."""
    planned = run.meta.get("samples_per_provider")
    seen = {(j.provider, j.sample) for r in run.resumes for j in r.judgments}
    if isinstance(planned, dict):
        seen |= {(name, i) for name, count in planned.items() for i in range(count)}
    return sorted(seen)


def score(run: HarnessRun, entries: list[dict]) -> list[Score]:
    """One score per provider sample, over every key entry. An entry whose document the
    run skipped or never judged, or that a sample left unanswered, is `MISSING`."""
    judged = {(r.name, j.provider, j.sample): j.categories
              for r in run.resumes if not r.skipped for j in r.judgments}
    scores = []
    for provider, sample in _samples(run):
        result = Score(f"{provider} sample {sample}")
        for entry in entries:
            answer = judge_answer(judged.get((entry["doc"], provider, sample), {}), entry)
            if answer == entry["answer"]:
                result.matched += 1
            else:
                result.mismatches.append((entry, answer))
        scores.append(result)
    return scores


def render(scores: list[Score], entries: list[dict], path: Path) -> str:
    out = [f"Against the answer key ({path.name}, {len(entries)} items)"]
    for result in scores:
        out.append(f"  {result.judge:<22} {result.matched}/{result.scored} matched")
        out += [f"    {e['doc']} / {e['category']}/{e['criterion']} / {e.get('locator', '-')}"
                f" / key {e['answer']} vs judge {answer}"
                for e, answer in result.mismatches]
    return "\n".join(out)
