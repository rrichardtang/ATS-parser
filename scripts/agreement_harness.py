"""Measures whether two judges agree, which is the test the rubric has to pass.

MAP.md's acceptance test is a claim about judges, not resumes: per category they
must land in the same place, and the composite must not move more than 5 points
between them (above 8 fails). Nothing could apply that test, because the pipeline
folds every disagreement away before a score is reported. This runs each resume
past each provider twice with the samples kept apart, so sampling noise shows up
as its own column rather than as the disagreement it is easily mistaken for.

    .venv/bin/python scripts/agreement_harness.py --dry-run
    .venv/bin/python scripts/agreement_harness.py --resume ~/resume.pdf
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
import sys
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
    made = __import__("tests.make_fixtures", fromlist=["build_all"]).build_all()
    if only:
        missing = [name for name in only if name not in made]
        if missing:
            raise SystemExit(f"unknown fixture(s): {', '.join(missing)}")
        return [(name, made[name]) for name in only]
    return sorted(made.items())


def run_notes(
    providers, fixtures_run: int, fixtures_total: int, samples: int,
    temperature: float, real_resume: bool,
) -> list[str]:
    """Everything about this run that would make its numbers mean less than they look."""
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

    missing = []
    if fixtures_run < fixtures_total:
        missing.append(f"{fixtures_total - fixtures_run} of the {fixtures_total} fixtures (--only)")
    if not real_resume:
        missing.append("the owner's own resume (--resume)")
    if missing:
        notes.append(
            "Not the full acceptance-test corpus: missing " + " and ".join(missing) + ". "
            "The fixtures are synthetic and deliberately extreme, so they exercise the "
            "rubric's ends and say least about the middle, where real resumes sit."
        )
    return notes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--samples", type=int, default=2,
                        help="samples per provider per resume (default 2)")
    parser.add_argument("--resume", help="the real resume PDF, the 8th input")
    parser.add_argument("--only", default="",
                        help="comma-separated fixture names, instead of all seven")
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

    band_order = [b.strip() for b in args.bands.split(",") if b.strip()]

    if args.replay:
        run = agreement.HarnessRun.from_dict(
            json.loads(Path(args.replay).read_text(encoding="utf-8"))
        )
        print(render(agreement.analyse(run, band_order)))
        return

    all_fixtures = fixture_targets([])
    only = [n.strip() for n in args.only.split(",") if n.strip()]
    fixtures = [(n, p) for n, p in all_fixtures if n in only] if only else all_fixtures
    if only and len(fixtures) < len(only):
        known = {n for n, _ in all_fixtures}
        raise SystemExit(f"unknown fixture(s): {', '.join(sorted(set(only) - known))}")
    targets: list[tuple[str, str]] = [(name, str(path)) for name, path in fixtures]
    if args.resume:
        resume_path = Path(args.resume).expanduser()
        if not resume_path.exists():
            raise SystemExit(f"no such resume: {resume_path}")
        targets.append((resume_path.stem, str(resume_path)))

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

    notes = run_notes(
        providers, len(fixtures), len(all_fixtures), args.samples,
        temperature, bool(args.resume),
    )
    print()
    run = agreement.collect(providers, targets, args.samples, temperature, notes)

    out = Path(args.out) if args.out else (
        DEFAULT_OUT / f"agreement-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    # Saved before analyse(), deliberately: scoring a judgement runs score.build,
    # which writes each finding's cost onto the shared deterministic findings.
    # Saving afterwards would bake one judgement's deductions into the raw record.
    out.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")

    print(render(agreement.analyse(run, band_order)))
    print(f"Raw judgements saved to {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")


if __name__ == "__main__":
    main()
