"""Measures whether two judges agree, which is the test the rubric has to pass.

MAP.md's acceptance test is a claim about judges, not resumes: per category they
must land in the same place, and the composite must not move more than 5 points
between them (above 8 fails). Nothing could apply that test, because the pipeline
folds every disagreement away before a score is reported. This runs each resume
past each provider twice with the samples kept apart, so sampling noise shows up
as its own column rather than as the disagreement it is easily mistaken for.

    .venv/bin/python scripts/agreement_harness.py --dry-run
    .venv/bin/python scripts/agreement_harness.py --acceptance-set --only ""
    .venv/bin/python scripts/agreement_harness.py --resume ~/resume.pdf
    .venv/bin/python scripts/agreement_harness.py --docs strong,thin --samples 1 --dry-run
    .venv/bin/python scripts/agreement_harness.py --from runs/agreement-....json

Keys come from ANTHROPIC_API_KEY and OPENAI_API_KEY. Both are wanted: with one
the only real number is the within-judge noise floor, since between-judge
agreement is the thing being measured.

The run is saved whole (raw replies, not just the tables) so the next rubric
change is judged on a diff rather than on a remembered number, and so a change to
how agreement is measured can be re-run against calls already paid for. It holds
quoted resume text, so `runs/` is gitignored -- the printed table quotes nothing
and is the part that belongs in a ticket.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats import agreement, config  # noqa: E402
from ats.agreement_table import render  # noqa: E402
from ats.llm import LEGACY_OPENAI, providers_from  # noqa: E402

DEFAULT_OUT = ROOT / "runs"


def fixture_targets(only: list[str]) -> list[tuple[str, Path]]:
    """The seven fixtures, generated rather than checked in (tests/make_fixtures.py).

    Call this once per run: it regenerates every fixture PDF.
    """
    from tests.make_fixtures import build_all

    made = build_all()
    if only:
        missing = [name for name in only if name not in made]
        if missing:
            raise SystemExit(f"unknown fixture(s): {', '.join(missing)}")
        return [(name, made[name]) for name in only]
    return sorted(made.items())


def acceptance_targets() -> list[tuple[str, Path]]:
    """08's set, rendered on demand for the same reason the fixtures are.

    The seven fixtures are deliberately extreme and were written by the sessions
    validating the rubric; these were written from briefs drawn out of the posting
    corpus, with no document aimed at a band. Which tier a number came from has to
    reach the write-up, so they stay separately addressable rather than being merged
    into `fixture_targets`. See docs/wayfinder/rubric-migration/acceptance-set.md.
    """
    from scripts.make_acceptance_set import build_all

    return sorted(build_all().items())


def run_notes(providers, samples: int, temperature: float) -> list[str]:
    """Everything about how this run sampled that would make its numbers mean less."""
    notes = []
    if samples < 2:
        notes.append(
            f"{samples} sample per provider: sampling noise cannot be separated from "
            "provider disagreement without at least two."
        )
    modern = [p.label for p in providers if not LEGACY_OPENAI.match(p.model)]
    if modern and temperature:
        notes.append(
            f"temperature={temperature} does not reach {', '.join(modern)} -- current "
            "models dropped the parameter (see ats/llm.py), so the within-judge column "
            "measures each provider's own default sampling, not a temperature chosen here."
        )
    return notes


def coverage_notes(
    names: set[str], fixtures: list, acceptance: list, resume: list,
) -> list[str]:
    """What the run left out of the corpus, given the names it actually judges."""
    notes = []
    missing = []
    fixtures_run = sum(name in names for name, _ in fixtures)
    if fixtures_run < len(fixtures):
        missing.append(f"{len(fixtures) - fixtures_run} of the {len(fixtures)} fixtures "
                       "(--only, --docs)")
    if not any(name in names for name, _ in resume):
        missing.append("the owner's own resume (--resume)")
    if missing:
        notes.append(
            "Not the full acceptance-test corpus: missing " + " and ".join(missing) + ". "
            "The fixtures are synthetic and deliberately extreme, so they exercise the "
            "rubric's ends and say least about the middle, where real resumes sit."
        )
    acceptance_run = sum(name in names for name, _ in acceptance)
    if not acceptance_run:
        notes.append(
            "08's acceptance set was not run (--acceptance-set): every document here "
            "was written by a session that was also validating the rubric."
        )
    elif acceptance_run < len(acceptance):
        notes.append(f"Only {acceptance_run} of 08's {len(acceptance)} acceptance-set "
                     "documents were run (--docs).")
    return notes


def _names(csv: str) -> list[str]:
    return [n.strip() for n in csv.split(",") if n.strip()]


def select_targets(args) -> tuple[list[tuple[str, str]], list[str]]:
    """The (name, path) targets the flags pick, and what they leave out of the corpus."""
    fixtures = fixture_targets([])
    docs = _names(args.docs)
    acceptance = acceptance_targets() if args.acceptance_set or docs else []
    resume = []
    if args.resume:
        resume_path = Path(args.resume).expanduser()
        if not resume_path.exists():
            raise SystemExit(f"no such resume: {resume_path}")
        resume = [(resume_path.stem, resume_path)]

    if docs:
        pool = dict(fixtures + acceptance + resume)
        unknown = [name for name in docs if name not in pool]
        if unknown:
            raise SystemExit(f"unknown document(s): {', '.join(unknown)}")
        chosen = [(name, pool[name]) for name in docs]
    else:
        only = _names(args.only)
        chosen = [(n, p) for n, p in fixtures if n in only] if only else list(fixtures)
        if only and len(chosen) < len(only):
            known = {n for n, _ in fixtures}
            raise SystemExit(f"unknown fixture(s): {', '.join(sorted(set(only) - known))}")
        chosen += acceptance + resume

    names = {name for name, _ in chosen}
    return ([(name, str(path)) for name, path in chosen],
            coverage_notes(names, fixtures, acceptance, resume))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--samples", type=int, default=2,
                        help="samples per provider per resume (default 2)")
    parser.add_argument("--resume", help="the real resume PDF, the 8th input")
    parser.add_argument("--only", default="",
                        help="comma-separated fixture names, instead of all seven")
    parser.add_argument("--docs", default="",
                        help="comma-separated document names, picked from the fixtures, "
                             "08's acceptance set and the --resume file's stem; "
                             "replaces --only and --acceptance-set")
    parser.add_argument("--acceptance-set", action="store_true",
                        help="also judge 08's 30 drawn documents (corpus/resumes/)")
    parser.add_argument("--temperature", type=float,
                        help="default: weights.toml's [ensemble] temperature")
    parser.add_argument("--bands", default="",
                        help="band order, worst first, once ticket 05 lands them "
                             "(e.g. --bands absent,thin,solid,strong)")
    parser.add_argument("--out", help=f"where to save the run (default {DEFAULT_OUT}/)")
    parser.add_argument("--from", dest="replay",
                        help="re-render a saved run; makes no API calls")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and what it will cost in calls, then stop")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")
    logging.getLogger("ats.llm").setLevel(logging.INFO)

    band_order = [b.strip() for b in args.bands.split(",") if b.strip()]

    if args.replay:
        run = agreement.HarnessRun.from_dict(
            json.loads(Path(args.replay).read_text(encoding="utf-8"))
        )
        print(render(agreement.analyse(run, band_order)))
        return

    targets, coverage = select_targets(args)

    temperature = args.temperature
    if temperature is None:
        temperature = float(config.ensemble_settings()["temperature"])

    providers = providers_from({})
    calls = agreement.planned_calls(targets, len(providers), args.samples)
    print(f"{len(targets)} resume(s) x {len(providers)} provider(s) x {args.samples} "
          f"sample(s) = up to {calls} content calls "
          "(a resume with no text layer is skipped before any call)")
    for name, path in targets:
        print(f"  {name:<18} {path}")
    labels = ", ".join(p.label for p in providers)
    print(f"  providers: {labels or 'none -- set ANTHROPIC_API_KEY, OPENAI_API_KEY'}")

    if args.dry_run:
        return
    if not providers:
        raise SystemExit("no API key found; set ANTHROPIC_API_KEY and/or OPENAI_API_KEY")

    notes = run_notes(providers, args.samples, temperature) + coverage
    out = Path(args.out) if args.out else (
        DEFAULT_OUT / f"agreement-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    shown = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"\nSaving after every resume to {shown}; a stopped run keeps what it paid for.")
    started = time.monotonic()

    def after_each(run: agreement.HarnessRun) -> None:
        # Saved before analyse(), deliberately: scoring a judgement runs score.build,
        # which writes each finding's cost onto the shared deterministic findings.
        # Saving afterwards would bake one judgement's deductions into the raw record.
        out.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")
        latest = run.resumes[-1]
        state = (f"skipped ({latest.skipped})" if latest.skipped
                 else f"{len(latest.judgments)} replies"
                 + (f", {len(latest.errors)} failed" if latest.errors else ""))
        print(f"  [{len(run.resumes)}/{len(targets)}] {latest.name}: {state}  "
              f"({(time.monotonic() - started) / 60:.1f} min)", flush=True)

    run = agreement.collect(providers, targets, args.samples, temperature, notes,
                            after_each=after_each)
    print()

    print(render(agreement.analyse(run, band_order)))
    print(f"Raw judgements saved to {shown}")


if __name__ == "__main__":
    main()
