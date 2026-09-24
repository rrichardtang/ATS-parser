"""Scores one document under both rubrics and prints what moved, and why.

This is the ticket the migration map exists to reach (07): the first time the new
rubric scores a document next to the old one scoring the same document.

**The old column is the old code, not a model of it.** `03` replaced `models.Category`
outright, so there is no old path left in the package to run beside the new one -- and
reconstructing one here would be a second implementation to disbelieve. Instead the
tree as it stood when the baseline was recorded is materialised from git into a
temporary directory and run in a subprocess, because two `ats` packages cannot share an
interpreter. The pin is `BASELINE_COMMIT` and it is the commit that recorded
baseline-agreement.md, not a later one: `01` and `02` look like documentation tickets
but `02` removed four `RULE_DIMENSION` entries, which changes what four rules cost.

**The judge channel.** Both rubrics have one, and they are different objects: the old
prompt asked for five category scores out of 100, the new one asks the criteria. With
provider credentials each side calls its own *content* pass -- and only that: the LLM
slop pass is skipped on both sides, because it is a second call whose findings the
migration changed only in where they file, and the deterministic slop rules that carry
most of that signal run on both sides already. Without credentials, both sides can
still be fed the judgements already recorded for the seven fixtures --
`rubric-grounding/baseline/run-summary.json` for the old, `criteria/judgments/` for the
new -- which is the same documents through both paths, off the record rather than off a
fresh reading. `--rules-only` skips the judge channel on both sides and compares what
the deterministic layer alone does, which is the only comparison available on a
document nobody has judged.

    .venv/bin/python scripts/side_by_side.py --fixtures
    .venv/bin/python scripts/side_by_side.py --doc ~/resume.pdf
    .venv/bin/python scripts/side_by_side.py --acceptance-set --rules-only
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats import config, passes, score  # noqa: E402
from ats.extract import extract  # noqa: E402
from ats.llm import providers_from  # noqa: E402
from ats.models import JUDGED_CATEGORIES, Category  # noqa: E402
from ats.pipeline import deterministic, resolve_target_title  # noqa: E402
from ats.rubric import SLUGS, load_spec, slug_by_category  # noqa: E402
from ats.sections import parse  # noqa: E402
from scripts.agreement_harness import acceptance_targets, fixture_targets  # noqa: E402
from scripts.baseline_analysis import load, means  # noqa: E402
from scripts.criteria_probe import load_recorded  # noqa: E402

# The tree the 30 August baseline was recorded against. See the module docstring.
BASELINE_COMMIT = "1418f0a"

# Extracted once per machine and reused. Outside the repo on purpose: the old tree
# carries its own `tests/`, and inside the checkout pytest would collect them and put
# the old `ats` package on the path ahead of the real one.
OLD_TREE = Path(tempfile.gettempdir()) / f"ats-old-tree-{BASELINE_COMMIT}"
BASELINE = ROOT / "docs" / "wayfinder" / "rubric-grounding" / "baseline" / "run-summary.json"

# Runs inside the materialised old tree. Kept here rather than in a file so the old
# tree stays exactly what git has: nothing is added to it to make it runnable.
OLD_DRIVER = """
import json, sys
sys.path.insert(0, sys.argv[1])
from ats import config, ensemble, passes, score
from ats.llm import providers_from
from ats.extract import extract
from ats.models import Category
from ats.pipeline import deterministic, resolve_target_title
from ats.sections import parse


def judged(entries):
    out = {}
    for name, values in entries.items():
        try:
            out[Category(name)] = values
        except ValueError:
            continue
    return out


def run(request):
    doc = extract(request["pdf"])
    resume = parse(doc.text)
    findings = deterministic(doc, resume, "", resolve_target_title(""))
    llm = {}
    if request.get("live"):
        # The old content pass, called exactly as the old pipeline called it. Never
        # run: the sessions that built this had no credentials. See ticket 07.
        settings = config.ensemble_settings()
        content = passes.content_pass(
            providers_from({}), resume, doc.text, "", findings,
            int(settings["content_samples"]), float(settings["temperature"]),
            config.jd_digest(),
        )
        findings += content.data
        llm = judged(content.meta.get("scores") or {})
    elif request.get("per_provider"):
        llm = judged(ensemble.combine_scores(request["per_provider"])[0])

    report = score.build(findings, llm_categories=llm, partial=not llm)
    return {
        "composite": report.composite,
        "grade": report.grade,
        "parser_subscore": report.parser_subscore,
        "human_subscore": report.human_subscore,
        "categories": [
            {"category": c.category.value, "score": c.score, "weight": c.weight,
             "low": c.low, "high": c.high, "note": c.note}
            for c in report.categories
        ],
        "findings": [
            {"rule_id": f.rule_id, "category": f.category.value if f.category else None,
             "severity": f.severity.value, "cost": getattr(f, "_raw_cost", 0.0),
             "locator": f.locator}
            for f in report.findings
        ],
    }


print(json.dumps([run(request) for request in json.loads(sys.stdin.read())]))
"""


@functools.cache
def old_tree() -> Path:
    """The baseline commit, extracted once and reused by every run after.

    Extracted beside its final path and renamed into place, so two runs starting at
    once cannot leave a half-written tree for a third to trust.
    """
    if not OLD_TREE.exists():
        staging = OLD_TREE.with_name(f"{OLD_TREE.name}.{os.getpid()}")
        staging.mkdir(parents=True, exist_ok=True)
        archive = subprocess.run(["git", "archive", BASELINE_COMMIT],
                                 cwd=ROOT, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", str(staging)], input=archive.stdout, check=True)
        try:
            staging.rename(OLD_TREE)
        except OSError:   # another run got there first; its tree is the same commit
            shutil.rmtree(staging)
    return OLD_TREE


def run_old_many(requests: list[dict]) -> list[dict]:
    """Every document through the old rubric in one interpreter.

    Starting Python and importing the old package is most of what one document costs,
    so the documents share one start rather than paying it each.
    """
    done = subprocess.run(
        [sys.executable, "-c", OLD_DRIVER, str(old_tree())],
        input=json.dumps(requests), capture_output=True, text=True, cwd=ROOT,
    )
    if done.returncode:
        raise SystemExit(f"old rubric failed:\n{done.stderr[-2000:]}")
    return json.loads(done.stdout)


def run_old(pdf: Path, per_provider: dict[str, dict[str, float]] | None,
            live: bool = False) -> dict:
    return run_old_many([{"pdf": str(pdf), "per_provider": per_provider or {},
                          "live": live}])[0]


def run_new(pdf: Path, judgments: list[passes.ContentJudgment] | None,
            live: bool = False) -> dict:
    """`pipeline.analyze` with the provider call replaced by recorded answers.

    Everything either side of the call is the real path -- the same `deterministic`,
    the same withholding decision, the same `score.build`. What is not the real path is
    that the judgements arrive from a file, which is the whole reason this is a script
    in `scripts/` and not a mode in `ats/`.
    """
    doc = extract(str(pdf))
    resume = parse(doc.text)
    findings = deterministic(doc, resume, "", resolve_target_title(""))
    reason = passes.withholding_reason(resume)
    withheld = ({c: "withheld -- " + reason for c in JUDGED_CATEGORIES}
                if reason else {})

    # The answers behind each band, for the "what moved and why" column.
    # `judge_categories` returns the band and the split, deliberately not the answer
    # sets -- naming the criterion that produced a drop is this script's job.
    answers: dict[Category, dict[str, bool]] = {}
    judged: dict = {}
    if reason:
        # Withholding happens before any call in `content_pass`, so a withheld document
        # has no judge channel at all -- not one whose answers are computed and then
        # dropped. Recorded answers for such a document predate 05 and are left unused
        # on purpose: that is the behaviour, not a limitation of this script.
        pass
    elif live:
        # The new content pass, called as `pipeline.analyze` calls it. Never run, for
        # the same reason as its opposite number in OLD_DRIVER. `content_pass` folds the
        # answers away and returns the bands (06), so the live path shows the band and
        # the criteria nothing in the resume spoke to.
        settings = config.ensemble_settings()
        content = passes.content_pass(
            providers_from({}), resume, doc.text, "", findings,
            int(settings["content_samples"]), float(settings["temperature"]),
            config.jd_digest(),
        )
        findings += content.data
        judged = content.judged
        for item in content.meta.get("unmet") or []:
            slug, cid = item["criterion_id"].split("/", 1)
            answers.setdefault(Category(load_spec(slug)["category"]), {})[cid] = False
    elif judgments:
        judged = passes.judge_categories(judgments)
        for judgment in judgments:
            for answer in passes.criterion_answers(judgment.categories):
                answers.setdefault(answer.category, {}).setdefault(
                    answer.criterion_id.split("/", 1)[1], answer.met)
    report = score.build(findings, llm_categories=judged, partial=not judged,
                         withheld=withheld)
    return {
        "composite": report.composite,
        "grade": report.grade,
        "parser_subscore": report.parser_subscore,
        "human_subscore": report.human_subscore,
        "categories": [
            {"category": c.category.value, "score": c.score, "weight": c.weight,
             "assessed": c.assessed, "note": c.note}
            for c in report.categories
        ],
        "findings": [
            {"rule_id": f.rule_id,
             "category": f.category.value if f.category else None,
             "severity": f.severity.value,
             "cost": getattr(f, "_raw_cost", 0.0),
             "advice_only": f.advice_only,
             "gate": f.gate.value if f.gate else None,
             "locator": f.locator}
            for f in report.findings
        ],
        "judged": {c.value: {"band": j.band, "band_name": j.band_name,
                             "value": j.value, "contested": j.contested,
                             "reads_as": j.reads_as(),
                             "answers": answers.get(c, {})}
                   for c, j in judged.items()},
        "withheld": reason,
        "withheld_but_recorded": bool(reason and judgments),
    }


# --------------------------------------------------------------------------
# The recorded judgements, one loader per rubric
# --------------------------------------------------------------------------


def old_recorded() -> dict[str, dict[str, dict[str, float]]]:
    """`{fixture: {provider: {category: score}}}` from the redacted baseline.

    `baseline_analysis.means` averages samples within a provider, which is what
    `passes.content_pass` did at that commit before `combine_scores` saw them -- the
    baseline holds the samples apart and the old scoring path did not.
    """
    if not BASELINE.exists():
        return {}
    out: dict[str, dict[str, dict[str, float]]] = {}
    for (resume, category), by_provider in means(load(BASELINE)).items():
        for provider, mean in by_provider.items():
            out.setdefault(resume, {}).setdefault(provider, {})[category] = mean
    return out


def new_recorded() -> dict[str, list[passes.ContentJudgment]]:
    """`{document: [ContentJudgment]}` from the recorded criterion answers.

    One judgement per recorded judge, which is the shape 06 emits per sample, so a
    second recorded judge is banded against the first rather than overwriting it.
    `load_recorded` is the probe's own loader and validates every answer set.
    """
    by_judge: dict[tuple[str, str], dict[str, dict]] = {}
    for slug in SLUGS:
        spec = load_spec(slug)
        for document, verdicts in load_recorded(spec).items():
            for judge, verdict in verdicts.items():
                by_judge.setdefault((document, judge), {})[spec["category"]] = {
                    "criteria": [
                        {"id": cid, "answer": "yes" if met else "no",
                         "evidence": verdict.evidence.get(cid, "")}
                        for cid, met in verdict.answers.items()
                    ],
                }
    out: dict[str, list[passes.ContentJudgment]] = {}
    for (document, judge), categories in sorted(by_judge.items()):
        out.setdefault(document, []).append(passes.ContentJudgment(
            provider=f"recorded:{judge}", sample=0, categories=categories, findings=[],
        ))
    return out


# --------------------------------------------------------------------------
# Printing
# --------------------------------------------------------------------------

# The mechanical categories, which both rubrics have: everything the judge never asks.
CARRIED = tuple(c.value for c in Category if c not in JUDGED_CATEGORIES)

# A rule that changed name is not a rule that stopped firing, and a raw id diff cannot
# tell them apart. Both entries are decisions, not bookkeeping: 04 (implementing the
# other map's 12) split `content/bullet-invariants` down to one predicate and renamed
# it for what it now deducts on, and 03 §4 retired `cred/no-named-models` rather than
# refiling it -- a closed list of 15 model families against the fastest-moving
# vocabulary in the corpus.
RENAMED = {"content/bullet-invariants": "content/no-outcome"}
RETIRED = {"cred/no-named-models": "03 §4: a closed model-name list goes stale"}


def costs(findings: list[dict]) -> Counter:
    """What each rule cost on one side, summed over its occurrences."""
    total: Counter = Counter()
    for finding in findings:
        total[finding["rule_id"]] += finding["cost"]
    return total


def advice_rules(new: dict) -> list[str]:
    return sorted({f["rule_id"] for f in new["findings"] if f["advice_only"]})


def returned(old: dict, new: dict) -> float:
    """What the rules that are advice-only now used to deduct on this document."""
    was = costs(old["findings"])
    return sum(was[rule_id] for rule_id in advice_rules(new))


def _gate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}"


def render(name: str, old: dict, new: dict, channel: str) -> list[str]:
    lines = [f"=== {name} ===", f"    judge channel: {channel}"]
    lines.append("")
    lines.append(f"{'':<34}{'old':>10}{'new':>10}{'moved':>10}")
    lines.append(f"{'composite':<34}{old['composite']:>10.1f}"
                 f"{new['composite']:>10.1f}"
                 f"{new['composite'] - old['composite']:>+10.1f}"
                 f"   {old['grade']} -> {new['grade']}")
    # A gate holding a withheld category reports no score (score._subscore), so either
    # side can be None, and a move to or from n/a is not a number either.
    for label, key in (("parser gate", "parser_subscore"),
                       ("human gate", "human_subscore")):
        was, now = old[key], new[key]
        moved = "n/a" if was is None or now is None else f"{now - was:+.1f}"
        lines.append(f"{label:<34}{_gate(was):>10}{_gate(now):>10}{moved:>10}")

    old_cats = {c["category"]: c for c in old["categories"]}
    new_cats = {c["category"]: c for c in new["categories"]}

    lines.append("")
    lines.append("categories that carried over")
    for label in CARRIED:
        left, right = old_cats.get(label), new_cats.get(label)
        if not left or not right:
            continue
        lines.append(f"  {label:<32}{left['score']:>10.1f}{right['score']:>10.1f}"
                     f"{right['score'] - left['score']:>+10.1f}"
                     f"   w {left['weight']:g} -> {right['weight']:g}")

    lines.append("")
    lines.append("retired, and what replaced them")
    for label in [c for c in old_cats if c not in CARRIED]:
        cat = old_cats[label]
        band = ""
        if cat.get("low") is not None and cat["low"] != cat["high"]:
            band = f"  ({cat['low']:.0f}-{cat['high']:.0f})"
        lines.append(f"  {label:<32}{cat['score']:>10.1f}{'--':>10}"
                     f"{'retired':>10}{band}")
    for label in [c for c in new_cats if c not in CARRIED]:
        cat = new_cats[label]
        judged = new["judged"].get(label)
        if not cat.get("assessed", True):
            shown, tail = "n/a", f"   {cat['note'] or 'not assessed'}"
        else:
            shown = f"{cat['score']:.1f}"
            tail = f"   band {judged['band']}" if judged else "   rules only"
        lines.append(f"  {label:<32}{'--':>10}{shown:>10}{'new':>10}{tail}")

    if new["judged"]:
        lines.append("")
        lines.append("why each judged category landed there")
        slugs = slug_by_category()
        for label, judged in sorted(new["judged"].items()):
            spec = load_spec(slugs[label])
            names = {c["id"]: c["name"] for c in spec["criteria"]}
            unmet = [f"{cid} {names[cid]}" for cid, met in judged["answers"].items()
                     if not met]
            band = next(b for b in spec["bands"] if b["label"] == judged["band"])
            lines.append(f"  {label:<32}band {judged['band']} "
                         f"({judged['value']:g})  {band['name']}")
            if judged["reads_as"]:
                lines.append(f"  {'':<32}{judged['reads_as']}")
            lines.append(f"  {'':<32}unmet: {', '.join(unmet) if unmet else 'none'}")

    if new["withheld"]:
        lines.append("")
        lines.append(f"withheld on this document: {new['withheld']}")
        lines.append("  " + ", ".join(c.value for c in JUDGED_CATEGORIES))
        if new["withheld_but_recorded"]:
            lines.append("  recorded criterion answers exist for this document and are "
                         "not used: withholding happens before the call (05), and the "
                         "old rubric judged it anyway -- which is the difference.")

    old_costs, new_costs = costs(old["findings"]), costs(new["findings"])
    old_ids, new_ids = set(old_costs), set(new_costs)
    advice = advice_rules(new)
    if advice:
        gates = {f["rule_id"]: f["gate"] for f in new["findings"] if f["advice_only"]}
        lines.append("")
        lines.append("findings that stopped deducting (04)")
        for rule_id in advice:
            lines.append(f"  {rule_id:<34}was {old_costs[rule_id]:>5.1f}   now 0.0"
                         f"   gate {gates[rule_id]}")
        lines.append(f"  {'points returned':<34}{returned(old, new):>9.1f}")

    renamed = [(was, now) for was, now in RENAMED.items()
               if was in old_ids or now in new_ids]
    retired = [r for r in RETIRED if r in old_ids]
    if renamed or retired:
        lines.append("")
        lines.append("rules renamed or retired")
        for was, now in sorted(renamed):
            lines.append(f"  {was} -> {now:<20}"
                         f"cost {old_costs[was]:>6.1f} -> {new_costs[now]:.1f}")
        for rule_id in sorted(retired):
            lines.append(f"  {rule_id:<34}cost {old_costs[rule_id]:>6.1f} -> gone"
                         f"   {RETIRED[rule_id]}")

    old_home = {f["rule_id"]: f["category"] for f in old["findings"]}
    old_home.update({now: old_home[was] for was, now in RENAMED.items()
                     if was in old_home})
    refiled = [(f["rule_id"], old_home[f["rule_id"]], f["category"])
               for f in new["findings"]
               if not f["advice_only"] and f["rule_id"] in old_home
               and old_home[f["rule_id"]] != f["category"]]
    if refiled:
        lines.append("")
        lines.append("findings that changed category (07 §1)")
        for rule_id, was, now in sorted(set(refiled)):
            lines.append(f"  {rule_id:<34}{was} -> {now}")

    known = set(RENAMED) | set(RENAMED.values()) | set(RETIRED)
    gone = sorted(old_ids - new_ids - known)
    added = sorted(new_ids - old_ids - known)
    if gone or added:
        lines.append("")
        lines.append("rules that fired on one side only")
        for rule_id in gone:
            lines.append(f"  {rule_id:<34}old only (cost {old_costs[rule_id]:.1f})")
        for rule_id in added:
            lines.append(f"  {rule_id:<34}new only")
    return lines


def summary_row(name: str, old: dict, new: dict) -> dict:
    """The per-document line of `--summary`: the move, and the three things that make it."""
    return {
        "name": name,
        "old": old["composite"],
        "new": new["composite"],
        "moved": new["composite"] - old["composite"],
        "returned": returned(old, new),
        "floored": sum(1 for c in new["categories"]
                       if c.get("assessed", True) and c["score"] == 0.0),
        "unassessed": sum(1 for c in new["categories"] if not c.get("assessed", True)),
    }


def render_summary(rows: list[dict]) -> str:
    lines = [f"{'document':<34}{'old':>8}{'new':>8}{'moved':>9}"
             f"{'returned':>10}{'floored':>9}{'n/a':>5}"]
    for row in rows:
        lines.append(f"{row['name']:<34}{row['old']:>8.1f}{row['new']:>8.1f}"
                     f"{row['moved']:>+9.1f}{row['returned']:>10.1f}"
                     f"{row['floored']:>9}{row['unassessed']:>5}")
    moved = [r["moved"] for r in rows]
    down = sum(1 for m in moved if m < -0.05)
    up = sum(1 for m in moved if m > 0.05)
    lines.append("")
    lines.append(f"{len(rows)} documents: {down} down, {up} up, "
                 f"{len(rows) - down - up} unchanged; "
                 f"mean {sum(moved) / len(moved):+.1f}, "
                 f"range {min(moved):+.1f} to {max(moved):+.1f}")
    lines.append("`returned` is what the advice-only rules used to deduct on this "
                 "document; `floored` counts judged categories the rule channel alone "
                 "drove to 0, and `n/a` those nothing reached.")
    return "\n".join(lines)


def targets(args) -> list[tuple[str, Path]]:
    if args.doc:
        path = Path(args.doc).expanduser()
        if not path.exists():
            raise SystemExit(f"no such document: {path}")
        return [(path.stem, path)]
    if args.acceptance_set:
        return acceptance_targets()
    return fixture_targets([])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doc", help="one PDF, instead of the fixtures")
    ap.add_argument("--fixtures", action="store_true", help="the seven fixtures (default)")
    ap.add_argument("--acceptance-set", action="store_true",
                    help="08's 30 drawn documents (no recorded judgements exist, so "
                         "this implies --rules-only unless keys are set)")
    ap.add_argument("--rules-only", action="store_true",
                    help="no judge channel on either side")
    ap.add_argument("--summary", action="store_true",
                    help="one line per document instead of the full comparison")
    args = ap.parse_args()

    live = (bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
            and not args.rules_only)
    recorded = not (args.rules_only or live)
    old_scores = old_recorded() if recorded else {}
    new_answers = new_recorded() if recorded else {}

    documents = targets(args)
    olds = run_old_many([{"pdf": str(path), "per_provider": old_scores.get(name) or {},
                          "live": live} for name, path in documents])

    blocks: list[str] = []
    rows: list[dict] = []
    for (name, path), old in zip(documents, olds):
        judgments = new_answers.get(name)
        new = run_new(path, judgments, live)
        if args.summary:
            rows.append(summary_row(name, old, new))
            continue
        if live:
            channel = "live: each rubric calls its own content pass (never yet run)"
        elif old_scores.get(name) and judgments:
            channel = (f"old: {len(old_scores[name])} recorded providers, 30 Aug "
                       "baseline; new: recorded model-claude criterion answers")
        elif args.rules_only:
            channel = "none -- deterministic layer only, both sides"
        else:
            channel = ("none for this document -- no recorded judgement on one or "
                       "both sides, so this is the deterministic layer only")
        blocks.append("\n".join(render(name, old, new, channel)))
    print(f"old rubric: {BASELINE_COMMIT} (the tree the baseline was recorded against)")
    print("new rubric: the working tree\n")
    print(render_summary(rows) if args.summary else "\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
