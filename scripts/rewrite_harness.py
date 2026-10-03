"""Measures how often a rewrite fixes the problem it was asked to fix (rewrite-context 01).

For each document it scores the resume and runs pass 3 as the app does, runs the content
judge again on the unchanged resume (the control: the judges change their own answer
about 12% of the time between samples, so some findings vanish with no edit), then swaps
every shipped rewrite in and reruns the deterministic rules and the content judge. Each
finding pass 3 handed a writer is counted fixed, not fixed, not shipped (and why) or not
swapped, deterministic and content-judge findings apart. See ats/rewrite_eval.py.

    .venv/bin/python scripts/rewrite_harness.py --acceptance-set --no-fixtures --dry-run
    .venv/bin/python scripts/rewrite_harness.py --acceptance-set --openai-price 0.10,0.50
    .venv/bin/python scripts/rewrite_harness.py --docs strong,thin --openai-price 0.10,0.50
    .venv/bin/python scripts/rewrite_harness.py --resume ~/resume.pdf --openai-price 0.10,0.50
    .venv/bin/python scripts/rewrite_harness.py --from runs/rewrite-eval-....json --summary s.json

Targets are picked as the agreement harness picks them. OpenAI only, built as the app
builds it (weights.toml's "default" mode); the key comes from OPENAI_API_KEY. `--jobs N`
(default 5) runs up to N documents at once; each document's own steps run as before.
`--budget` (default $3) caps real spend: each reply's token usage is recorded under its
document (a JSON repair included, cached input priced as input), and a document starts
only if what finished documents were charged, plus the worst case of every running one,
plus its own, is within the budget; the run saves what it has and lists the documents it
never started. It refuses to start if one document's worst case alone is over. A document
with a failed call (a 429 included) is charged its worst case if that is more than was
measured: a timed-out reply is billed but never reports its usage. A live run needs
`--openai-price IN,OUT`.
`--dry-run` prints each document's worst case and the total, without a key.
`--acceptance-set --no-fixtures` runs the 30 drawn documents only.

The run is saved whole to `runs/rewrite-eval-<UTC stamp>.json` after every document, in
target order whatever order they finish in, with each document's real spend and the
seconds of each step (the table shows their median and max). It holds quoted resume
text, so `runs/` is gitignored; the printed table quotes nothing. `--summary PATH` writes counts, real spend and the skipped count
(rule ids and locators, no text), safe to commit.
`--from RUN.json` re-renders a saved run without calls.

A shorter timing run on five drawn documents, shortest to longest (a budget under five
worst cases runs fewer than five at once):

    .venv/bin/python scripts/rewrite_harness.py --docs 15-backend-junior-no-ai,19-academic-terse-mid,06-data-platform-senior,30-junior-genai-product,10-new-grad-agentic --openai-price 0.10,0.50 --budget 2.5 --jobs 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats import budget, config, llm, passes, pipeline, rewrite_eval  # noqa: E402
from ats.extract import extract  # noqa: E402
from ats.sections import parse  # noqa: E402
from tests.make_fixtures import OUT as FIXTURES  # noqa: E402
from scripts.agreement_harness import (  # noqa: E402
    _positive, _price, _shown, _stamped, _write, select_targets,
)


def providers_for(settings: dict, key: str):
    """OpenAI as the app builds it for the content pass, and for the other passes, with no
    SDK retries: a timed-out try is lost, not resent and billed again (as in the
    agreement harness)."""
    keys = {"openai": key or "-"}
    content = [replace(p, openai_max_retries=0)
               for p in pipeline.app_providers(keys, {}, settings) if p.name == "openai"]
    return content, pipeline.non_content_providers(content, settings)


def prepared(targets) -> dict:
    """name -> (resume, text, deterministic findings) of each document the content judge reads."""
    out = {}
    for name, path in targets:
        doc = extract(path)
        resume = parse(doc.text)
        if doc.has_text_layer and not passes.withholding_reason(resume):
            out[name] = (resume, doc.text, pipeline.deterministic(
                doc, resume, "", pipeline.resolve_target_title("")))
    return out


def measure(index: int, name: str, path: str, providers, others, settings: dict,
            price, worst: float) -> dict:
    """One document's record with its real spend, its charge to the budget and its total
    seconds. Its replies are recorded under `index` (`llm.usage_key`), so documents
    running at once each read their own. Any failure, a 429 included, lands in its
    errors and charges its worst case: a timed-out reply is billed but never reports its
    usage, and a thread left running can still spend up to the worst case."""
    llm.usage_key.set(index)
    started = time.monotonic()
    try:
        document = rewrite_eval.evaluate(name, path, providers, others, settings)
    except Exception as exc:  # noqa: BLE001 - one document's failure must not end the run
        document = {"name": name, "targets": [], "errors": {"document": [repr(exc)]}}
    usage = llm.take_usage(index)
    document["seconds"] = {**document.get("seconds", {}),
                           "total": round(time.monotonic() - started, 2),
                           "slowest_call": round(usage["slowest_seconds"], 2)}
    document["spend"] = rewrite_eval.spend_of(usage, price)
    document["charged"] = (max(document["spend"]["dollars"], worst)
                           if document.get("errors") else document["spend"]["dollars"])
    return document


def run_documents(targets: list, worst: dict, cap: float, jobs: int, run_one, saved):
    """`run_one(index, name, path)` on up to `jobs` documents at once, started in target
    order. A document starts only if the charge of every finished document, plus the worst
    case of every running one, plus its own worst case, is within `cap`, so real spend
    cannot pass it whatever order they finish in. Returns the finished documents in target
    order and the names never started."""
    finished: dict[int, dict] = {}
    running: dict = {}
    queue = list(range(len(targets)))
    charged = 0.0

    def cost(i: int) -> float:
        return worst.get(targets[i][0], 0)

    def affordable() -> bool:
        return charged + sum(map(cost, running.values())) + cost(queue[0]) <= cap

    with ThreadPoolExecutor(jobs) as pool:
        while True:
            while queue and len(running) < jobs and affordable():
                i = queue.pop(0)
                print(f"  start {targets[i][0]}", flush=True)
                running[pool.submit(run_one, i, *targets[i])] = i
            if not running:
                break
            done, _ = wait(running, return_when=FIRST_COMPLETED)
            for future in done:
                i = running.pop(future)
                finished[i] = future.result()
                charged += finished[i]["charged"]
                saved([finished[k] for k in sorted(finished)])
                print(f"  [{len(finished)}/{len(targets)}] {targets[i][0]} done in "
                      f"{finished[i]['seconds']['total']:.0f}s", flush=True)
    return [finished[k] for k in sorted(finished)], [targets[i][0] for i in queue]


def save_summary(run: dict, path: str) -> None:
    _write(Path(path), rewrite_eval.summary(run))
    print(f"Counts-only summary saved to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--resume", help="a real resume PDF")
    parser.add_argument("--only", default="",
                        help="comma-separated fixture names, instead of all seven")
    parser.add_argument("--docs", default="",
                        help="comma-separated names from the fixtures, the acceptance set "
                             "and the --resume stem; replaces --only and --acceptance-set")
    parser.add_argument("--acceptance-set", action="store_true",
                        help="also run 08's 30 drawn documents (corpus/resumes/)")
    parser.add_argument("--no-fixtures", action="store_true",
                        help="with --acceptance-set, drop the 7 fixtures (a --resume still runs)")
    parser.add_argument("--out", help="where to save the run (default runs/rewrite-eval-*.json)")
    parser.add_argument("--summary", metavar="PATH", help="write a counts-only JSON here")
    parser.add_argument("--from", dest="replay", help="re-render a saved run; no calls")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the calls and worst-case cost, then stop")
    parser.add_argument("--budget", type=float, default=3.0,
                        help="spend at most this many dollars: stop before the document "
                             "whose worst case would take real spend past it, and refuse "
                             "to start if one document's worst case alone does (default 3.0)")
    parser.add_argument("--jobs", type=_positive, default=5,
                        help="run up to this many documents at once (default 5)")
    parser.add_argument("--openai-price", type=_price, metavar="IN,OUT",
                        help="OpenAI's $ per million input and output tokens; needed to "
                             "budget the run (gpt-6-luna: 0.10,0.50)")
    args = parser.parse_args()

    if args.replay:
        run = json.loads(Path(args.replay).read_text(encoding="utf-8"))
        print(rewrite_eval.render(run))
        if args.summary:
            save_summary(run, args.summary)
        return

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key and not args.dry_run:
        raise SystemExit("no API key found; set OPENAI_API_KEY (this harness is OpenAI only)")
    if args.no_fixtures and not args.acceptance_set:
        parser.error("--no-fixtures needs --acceptance-set")
    targets, _ = select_targets(args)
    if args.no_fixtures:
        targets = [t for t in targets if Path(t[1]).parent != FIXTURES]
    # The file stem can be a name, and the summary is committed.
    stem = Path(args.resume).expanduser().stem if args.resume else None
    targets = [("resume" if name == stem else name, path) for name, path in targets]
    settings = config.ensemble_settings("default")
    providers, others = providers_for(settings, key)
    counts = rewrite_eval.call_counts(settings)
    print(f"{len(targets)} resume(s) x ({' + '.join(f'{n} {k}' for k, n in counts.items())}) "
          f"= up to {len(targets) * sum(counts.values())} calls "
          "(a resume with no text layer is skipped before any call)")
    for name, path in targets:
        print(f"  {name:<18} {path}")

    try:
        worst = {name: rewrite_eval.worst_case(providers, others, settings, [doc],
                                               args.openai_price)
                 for name, doc in prepared(targets).items()}
    except budget.PriceUnknown as exc:
        raise SystemExit(str(exc))
    for name, cost in worst.items():
        print(f"  {name:<18} worst case ${cost:.2f}")
    print(f"Worst case ${sum(worst.values()):.2f} in all. Real spend is measured per reply "
          f"and no document starts that could take it past the ${args.budget:.2f} budget, "
          f"counting the worst case of every running one ({args.jobs} at once).")
    if args.dry_run:
        return
    if (dearest := max(worst.values(), default=0)) > args.budget:
        raise SystemExit(f"one document's worst case, ${dearest:.2f}, is over the "
                         f"${args.budget:.2f} budget; nothing was sent")

    out = Path(args.out) if args.out else _stamped("rewrite-eval")
    run = {"settings": settings, "documents": [], "skipped_for_budget": []}
    run["documents"], run["skipped_for_budget"] = run_documents(
        targets, worst, args.budget, args.jobs,
        lambda i, name, path: measure(i, name, path, providers, others, settings,
                                      args.openai_price, worst.get(name, 0)),
        lambda documents: _write(out, {**run, "documents": documents}))
    _write(out, run)
    print("\n" + rewrite_eval.render(run))
    print(f"Raw run saved to {_shown(out)}")
    if args.summary:
        save_summary(run, args.summary)


if __name__ == "__main__":
    main()
