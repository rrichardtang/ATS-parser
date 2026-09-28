"""Measures whether two judges agree, which is the test the rubric has to pass.

MAP.md's acceptance test is a claim about judges, not resumes: per category they
must land in the same place, and the composite must not move more than 5 points
between them (above 8 fails). Nothing could apply that test, because the pipeline
folds every disagreement away before a score is reported.

It tests what the app does (ticket 15, 27 September). OpenAI, the app judge, gives
`--samples` answers per resume (default 2), each one majority-voted from `--votes`
tries (default: weights.toml's content_votes, 3), so its self-consistency is measured
between two voted answers. Claude is the audit judge: `--claude-samples` answers
(default 1) of one try each, best sent with `--batch`. With one Claude answer there is
no Claude self-consistency number; the between-judge tables compare OpenAI's voted
answer with Claude's single one.

    .venv/bin/python scripts/agreement_harness.py --dry-run
    .venv/bin/python scripts/agreement_harness.py --acceptance-set --only ""
    .venv/bin/python scripts/agreement_harness.py --resume ~/resume.pdf
    .venv/bin/python scripts/agreement_harness.py --docs strong,thin --samples 1 --dry-run
    .venv/bin/python scripts/agreement_harness.py --from runs/agreement-....json
    .venv/bin/python scripts/agreement_harness.py --docs strong,thin --batch
    .venv/bin/python scripts/agreement_harness.py --collect runs/agreement-batch-....json

`--batch` sends Claude's calls through the Message Batches API at half the price,
running OpenAI's live meanwhile; `--collect`, once the batch has ended, finishes
the run and prints the same tables a live run does.

Nothing is sent until the run's worst case (every reply at its token cap, every
live call repaired, no cache hits) fits `--budget`, $3 by default; `--dry-run`
prints the same check, counting every OpenAI try (samples x votes) and its repair
call. The harness sends OpenAI no SDK retries, so a timed-out try is lost, not
billed twice. OpenAI's price is not known here, so a run that includes it
needs `--openai-price IN,OUT` (gpt-6-luna: 0.10,0.50, per its pricing on 22
September 2026) or `--claude-only`. `--max-tokens` lowers Claude's
output cap for this run, which fits more documents under the budget; a reply that
hits it is recorded as a failed call.

Keys come from ANTHROPIC_API_KEY and OPENAI_API_KEY. Both are wanted: with one
(`--claude-only`, `--no-claude`) the only real number is the within-judge noise
floor, since between-judge agreement is the thing being measured.

Every report (live, `--collect`, `--from`) ends with each judge sample scored against
the owner's answer key (`--key`, default corpus/resumes/answer_key.json): items matched
out of every key entry, and every mismatch -- a document the run skipped or never judged
is a missing answer. Ticket 15, 28 September.

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
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats import agreement, agreement_batch, answer_key, budget, config, llm  # noqa: E402
from ats.agreement_table import render  # noqa: E402
from ats.llm import LEGACY_OPENAI, providers_from  # noqa: E402

DEFAULT_OUT = ROOT / "runs"
# openai 3.19.2's `ReasoningEffort` values.
OPENAI_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")


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


def run_notes(providers, plan: agreement.Plan, temperature: float) -> list[str]:
    """Everything about how this run sampled that would make its numbers mean less."""
    notes = [
        f"{p.label} answered once per resume: its self-consistency is not measured, and "
        "its sampling noise cannot be separated from provider disagreement."
        for p in providers if plan[p.name][0] < 2
    ]
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


def chosen_providers(args, keys: dict[str, str] | None = None) -> list:
    """The providers the keys give, less the one --claude-only or --no-claude leaves
    out, at each provider's cap and OpenAI's effort, and with no OpenAI SDK retries: a
    timed-out try is lost, not resent and billed again, and the vote absorbs it."""
    left_out = "openai" if args.claude_only else "anthropic" if args.no_claude else ""
    return [replace(p, anthropic_max_tokens=args.max_tokens, openai_max_retries=0,
                    openai_max_tokens=args.openai_max_tokens,
                    openai_effort=args.openai_effort)
            for p in providers_from(keys or {}) if p.name != left_out]


def run_plan(args, providers) -> agreement.Plan:
    """Claude answers alone; OpenAI's samples are voted as the app votes them."""
    return {p.name: (args.claude_samples, 1) if p.name == "anthropic"
            else (args.samples, args.votes) for p in providers}


def prompt_tokens(targets) -> list[int]:
    """The estimated input tokens of each judged document's content prompt; no network."""
    prepared = [agreement.prepare(name, path) for name, path in targets]
    return [budget.input_tokens(*agreement.content_prompt(*doc))
            for doc in prepared if not doc[0].skipped]


def _price(value: str) -> tuple[float, float]:
    try:
        rate_in, rate_out = (float(part) for part in value.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("expected IN,OUT in $ per million tokens")
    if rate_in < 0 or rate_out < 0:
        raise argparse.ArgumentTypeError("prices must not be negative")
    return rate_in, rate_out


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {number}")
    return number


def _stamped(prefix: str) -> Path:
    return DEFAULT_OUT / f"{prefix}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"


def _shown(path: Path) -> Path:
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def submit_batch(providers, targets, plan: agreement.Plan, temperature: float,
                 notes: list[str]) -> Path:
    """Submit Claude's content calls as one batch; run any other provider live now.

    Saves the batch id and the run so far, OpenAI's replies included, to
    `runs/agreement-batch-<timestamp>.json`, which `--collect` finishes.
    """
    claude = next((p for p in providers if p.name == "anthropic"), None)
    if claude is None:
        raise SystemExit("--batch needs ANTHROPIC_API_KEY: only Claude's calls are batched")
    live = [p for p in providers if p is not claude]
    prepared = [agreement.prepare(name, path) for name, path in targets]
    requests = agreement_batch.requests(claude, prepared, plan[claude.name][0])
    if not requests:
        raise SystemExit("every target was skipped; there is nothing to batch")

    run = agreement.HarnessRun(
        meta=agreement.run_meta(providers, plan, temperature,
                                notes + [agreement_batch.NOTE]),
        resumes=[resume_run for resume_run, _, _ in prepared],
    )
    batch = llm._anthropic_client(claude.api_key).messages.batches.create(requests=requests)
    out = _stamped("agreement-batch")
    texts = [text for _, _, text in prepared]

    def save(live_done: bool) -> None:
        _write(out, {"batch_id": batch.id, "anthropic_model": claude.model,
                     "texts": texts, "live_done": live_done, "run": run.to_dict()})

    save(live_done=not live)
    print(f"\nSubmitted {len(requests)} Claude request(s) as batch {batch.id}; "
          f"saved to {_shown(out)}")
    if live:
        for index, (resume_run, resume, text) in enumerate(prepared):
            agreement.judge(live, resume_run, resume, text, plan, temperature)
            save(live_done=index == len(prepared) - 1)
            print(f"  {resume_run.name}: {len(resume_run.judgments)} live replies",
                  flush=True)
    print("Collect it once it has ended (most batches finish within an hour):\n"
          f"  .venv/bin/python scripts/agreement_harness.py --collect {_shown(out)}")
    return out


def print_report(run: agreement.HarnessRun, band_order: list[str], key: Path | None) -> None:
    """The agreement tables, then each judge against the owner's answer key."""
    print(render(agreement.analyse(run, band_order)))
    if key:
        entries = answer_key.load(key)
        print("\n" + answer_key.render(answer_key.score(run, entries), entries, key))


def collect_batch(saved_path: Path, out: Path, band_order: list[str],
                  key: Path | None = None) -> None:
    """Finish a `--batch` run: merge Claude's results and save the run in full.

    Exits non-zero, without waiting, while the batch is still processing.
    """
    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    if not saved.get("live_done"):
        raise SystemExit(
            f"{saved_path} was saved before its live (non-Claude) phase finished; "
            "re-run --batch to completion before collecting it."
        )
    claude = next((p for p in providers_from({}, {"anthropic": saved["anthropic_model"]})
                   if p.name == "anthropic"), None)
    if claude is None:
        raise SystemExit("--collect needs ANTHROPIC_API_KEY")
    batches = llm._anthropic_client(claude.api_key).messages.batches
    batch = batches.retrieve(saved["batch_id"])
    if batch.processing_status != "ended":
        counts = batch.request_counts
        raise SystemExit(
            f"batch {saved['batch_id']} is {batch.processing_status}: "
            f"{counts.processing} processing, {counts.succeeded} succeeded, "
            f"{counts.errored} errored. Collect again later."
        )
    run = agreement_batch.merge(agreement.HarnessRun.from_dict(saved["run"]), claude,
                                batches.results(saved["batch_id"]), saved["texts"])
    # Saved before analyse(), for the reason `after_each` gives in main().
    _write(out, run.to_dict())
    print_report(run, band_order, key)
    print(f"Raw judgements saved to {_shown(out)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--samples", type=_positive, default=2,
                        help="OpenAI's answers per resume, each voted from --votes tries "
                             "(default 2)")
    parser.add_argument("--votes", type=_positive,
                        default=int(config.ensemble_settings()["content_votes"]),
                        help="tries per OpenAI answer, majority-voted as the app votes "
                             "(default: weights.toml's content_votes)")
    parser.add_argument("--claude-samples", type=_positive, default=1,
                        help="Claude's answers per resume, one try each (default 1)")
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
    parser.add_argument("--key", type=Path,
                        default=answer_key.KEY if answer_key.KEY.exists() else None,
                        help="the owner's answer key each judge is scored against "
                             f"(default {_shown(answer_key.KEY)} when it exists)")
    parser.add_argument("--from", dest="replay",
                        help="re-render a saved run; makes no API calls")
    parser.add_argument("--batch", action="store_true",
                        help="submit Claude's calls as one Message Batch (half price, "
                             "results within hours); other providers run live now")
    parser.add_argument("--collect", metavar="BATCH_FILE",
                        help="finish a --batch run from its runs/agreement-batch-*.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan, its calls and its worst-case cost, then stop")
    one_judge = parser.add_mutually_exclusive_group()
    one_judge.add_argument("--claude-only", action="store_true",
                           help="leave OpenAI out even when OPENAI_API_KEY is set")
    one_judge.add_argument("--no-claude", action="store_true",
                           help="leave Claude out even when ANTHROPIC_API_KEY is set")
    parser.add_argument("--budget", type=float, default=3.0,
                        help="refuse, before sending anything, a run whose worst case "
                             "costs more dollars than this (default 3.0)")
    parser.add_argument("--max-tokens", type=_positive, default=llm.ANTHROPIC_MAX_TOKENS,
                        help="Claude's output cap for this run, thinking included "
                             f"(default {llm.ANTHROPIC_MAX_TOKENS})")
    parser.add_argument("--openai-max-tokens", type=_positive, default=llm.MAX_TOKENS,
                        help="OpenAI's output cap for this run, reasoning included "
                             f"(default {llm.MAX_TOKENS})")
    parser.add_argument("--openai-effort", choices=OPENAI_EFFORTS,
                        default=config.ensemble_settings()["openai_effort"],
                        help="OpenAI's reasoning effort (default: weights.toml's "
                             "[ensemble] openai_effort)")
    parser.add_argument("--openai-price", type=_price, metavar="IN,OUT",
                        help="OpenAI's $ per million input and output tokens; needed "
                             "to budget a run that includes OpenAI (gpt-6-luna: 0.10,0.50)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")
    logging.getLogger("ats.llm").setLevel(logging.INFO)

    band_order = [b.strip() for b in args.bands.split(",") if b.strip()]
    if args.key and not args.key.exists():
        raise SystemExit(f"no such answer key: {args.key}")

    if args.replay:
        run = agreement.HarnessRun.from_dict(
            json.loads(Path(args.replay).read_text(encoding="utf-8"))
        )
        print_report(run, band_order, args.key)
        return
    out = Path(args.out) if args.out else _stamped("agreement")
    if args.collect:
        collect_batch(Path(args.collect), out, band_order, args.key)
        return

    targets, coverage = select_targets(args)

    temperature = args.temperature
    if temperature is None:
        temperature = float(config.ensemble_settings()["temperature"])

    providers = chosen_providers(args)
    # A keyless dry run is costed as if both keys were set.
    costed = providers or chosen_providers(args, {"anthropic": "-", "openai": "-"})
    plan = run_plan(args, costed)
    per_resume = ", ".join(f"{name} {samples} x {votes}"
                           for name, (samples, votes) in plan.items())
    print(f"{len(targets)} resume(s) x ({per_resume}) sample(s) x vote(s) = up to "
          f"{agreement.planned_calls(targets, plan)} content calls "
          "(a resume with no text layer is skipped before any call)")
    for name, path in targets:
        print(f"  {name:<18} {path}")
    labels = ", ".join(p.label for p in providers)
    print(f"  providers: {labels or 'none -- set ANTHROPIC_API_KEY, OPENAI_API_KEY'}")

    calls = {name: samples * votes for name, (samples, votes) in plan.items()}
    fits, report = budget.verdict(costed, prompt_tokens(targets), calls,
                                  args.batch, args.openai_price, args.budget)
    print(report)
    if args.dry_run:
        return
    if not providers:
        raise SystemExit("no API key found; set ANTHROPIC_API_KEY and/or OPENAI_API_KEY")
    if not fits:
        raise SystemExit("over budget; nothing was sent")

    notes = run_notes(providers, plan, temperature) + coverage
    if args.batch:
        submit_batch(providers, targets, plan, temperature, notes)
        return
    shown = _shown(out)
    print(f"\nSaving after every resume to {shown}; a stopped run keeps what it paid for.")
    started = time.monotonic()

    def after_each(run: agreement.HarnessRun) -> None:
        # Saved before analyse(), deliberately: scoring a judgement runs score.build,
        # which writes each finding's cost onto the shared deterministic findings.
        # Saving afterwards would bake one judgement's deductions into the raw record.
        _write(out, run.to_dict())
        latest = run.resumes[-1]
        state = (f"skipped ({latest.skipped})" if latest.skipped
                 else f"{len(latest.judgments)} replies"
                 + (f", {len(latest.errors)} failed" if latest.errors else ""))
        print(f"  [{len(run.resumes)}/{len(targets)}] {latest.name}: {state}  "
              f"({(time.monotonic() - started) / 60:.1f} min)", flush=True)

    run = agreement.collect(providers, targets, plan, temperature, notes,
                            after_each=after_each)
    print()

    print_report(run, band_order, args.key)
    print(f"Raw judgements saved to {shown}")


if __name__ == "__main__":
    main()
