"""Measures how often a rewrite fixes the problem it was asked to fix (rewrite-context 01).

For each document it scores the resume and runs pass 3 as the app does, runs the content
judge again on the unchanged resume (the control: the judges change their own answer
about 12% of the time between samples, so some findings vanish with no edit), then swaps
every shipped rewrite in and reruns the deterministic rules and the content judge. Each
finding pass 3 handed a writer is counted fixed, not fixed, not shipped (and why) or not
swapped, deterministic and content-judge findings apart. See ats/rewrite_eval.py.

    .venv/bin/python scripts/rewrite_harness.py --acceptance-set --dry-run
    .venv/bin/python scripts/rewrite_harness.py --acceptance-set --openai-price 0.10,0.50
    .venv/bin/python scripts/rewrite_harness.py --docs strong,thin --openai-price 0.10,0.50
    .venv/bin/python scripts/rewrite_harness.py --resume ~/resume.pdf --openai-price 0.10,0.50
    .venv/bin/python scripts/rewrite_harness.py --from runs/rewrite-eval-....json --summary s.json

Targets are picked as the agreement harness picks them. OpenAI only, built as the app
builds it (weights.toml's "default" mode); the key comes from OPENAI_API_KEY. Nothing is
sent until the run's worst case fits `--budget`, $3 by default, and a live run needs
`--openai-price IN,OUT`. `--dry-run` prints the same check without a key.

The run is saved whole to `runs/rewrite-eval-<UTC stamp>.json` after every document. It
holds quoted resume text, so `runs/` is gitignored; the printed table quotes nothing.
`--summary PATH` writes counts only (rule ids and locators, no text), safe to commit.
`--from RUN.json` re-renders a saved run without calls.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats import budget, config, passes, pipeline, rewrite_eval  # noqa: E402
from ats.extract import extract  # noqa: E402
from ats.sections import parse  # noqa: E402
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


def prepared(targets) -> list:
    """(resume, text, deterministic findings) of each document the content judge reads."""
    out = []
    for _, path in targets:
        doc = extract(path)
        resume = parse(doc.text)
        if doc.has_text_layer and not passes.withholding_reason(resume):
            out.append((resume, doc.text, pipeline.deterministic(
                doc, resume, "", pipeline.resolve_target_title(""))))
    return out


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
    parser.add_argument("--out", help="where to save the run (default runs/rewrite-eval-*.json)")
    parser.add_argument("--summary", metavar="PATH", help="write a counts-only JSON here")
    parser.add_argument("--from", dest="replay", help="re-render a saved run; no calls")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the calls and worst-case cost, then stop")
    parser.add_argument("--budget", type=float, default=3.0,
                        help="refuse, before sending anything, a run whose worst case "
                             "costs more dollars than this (default 3.0)")
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
    targets, _ = select_targets(args)
    settings = config.ensemble_settings("default")
    providers, others = providers_for(settings, key)
    counts = rewrite_eval.call_counts(settings)
    print(f"{len(targets)} resume(s) x ({' + '.join(f'{n} {k}' for k, n in counts.items())}) "
          f"= up to {len(targets) * sum(counts.values())} calls "
          "(a resume with no text layer is skipped before any call)")
    for name, path in targets:
        print(f"  {name:<18} {path}")

    try:
        cost = rewrite_eval.worst_case(providers, others, settings, prepared(targets),
                                       args.openai_price)
    except budget.PriceUnknown as exc:
        raise SystemExit(str(exc))
    fits = cost <= args.budget
    print(f"Worst case ${cost:.2f} against a ${args.budget:.2f} budget: "
          f"{'fits' if fits else 'over'}.")
    if args.dry_run:
        return
    if not fits:
        raise SystemExit("over budget; nothing was sent")

    out = Path(args.out) if args.out else _stamped("rewrite-eval")
    run = {"settings": settings, "documents": []}
    for name, path in targets:
        run["documents"].append(rewrite_eval.evaluate(name, path, providers, others, settings))
        _write(out, run)
        print(f"  [{len(run['documents'])}/{len(targets)}] {name}", flush=True)
    print("\n" + rewrite_eval.render(run))
    print(f"Raw run saved to {_shown(out)}")
    if args.summary:
        save_summary(run, args.summary)


if __name__ == "__main__":
    main()
