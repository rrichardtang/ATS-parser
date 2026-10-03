type: task (AFK)
status: open
claimed: claude
blocked-by: —

# Measure what rewrites fix

## Question

How often does a rewrite make the problem it was asked to fix go away, without the
fact-check rejecting it?

## What to build

A script beside `scripts/agreement_harness.py` that, for each resume in the acceptance
set:

1. Scores it and runs pass 3 as the app does.
2. For each rewrite, asks the content judge the targeted criterion again with the
   rewritten bullet swapped in, and reruns the deterministic rules on it.
3. Counts, per target: fixed (criterion now `yes`, or the rule no longer fires), not
   fixed, or no rewrite shipped (and why: audit rejection, no margin, no candidates).

It writes a redacted summary that can be committed (counts only) and keeps quoted text
in `runs/`, which is gitignored. It takes `--dry-run` to print the call budget, like the
agreement harness.

## Done when

The script exists with tests that need no network, and the baseline numbers are recorded
here and in the map. Recording them needs `OPENAI_API_KEY`. A session without it builds
the script, says so, and leaves the baseline for one that has it.

## Found

**Built, 3 October. Baseline not recorded yet:** the session that built it had no
`OPENAI_API_KEY`, so no number exists. A session with the key runs the command below and
records the printed table here and in the map.

- `scripts/rewrite_harness.py` drives `ats/rewrite_eval.py` (pure logic, tested without a
  network in `tests/test_rewrite_harness.py`). Targets are picked as the agreement harness
  picks them; OpenAI only, built with `pipeline.app_providers` and the "default" mode.
- Per document: before (deterministic rules, `content_pass`, `slop_pass`, `rewrite_pass`
  with the app's arguments), a control (`content_pass` again on the unchanged resume), and
  after (every shipped rewrite swapped into the parsed bullets and the full text, then the
  rules and `content_pass` again).
- Each (locator, rule_id) that pass 3 handed a writer is `fixed`, `not_fixed`,
  `not_shipped` (reason bucket: `no candidates`, `no margin`, `audit rejected`),
  `not_swapped` (original not found in the full text) or `unmeasured` (an LLM slop finding,
  which is not re-run, or a content finding when the judge failed after the swap).
  Deterministic and content-judge findings are counted apart; the control vanish rate
  prints beside the content fix rate.
- `passes.rewrite_targets` was factored out of `rewrite_pass` so the harness reads the
  same target selection. App behaviour is unchanged.
- `--summary PATH` writes counts, rule ids and locators only. The raw run goes to
  `runs/rewrite-eval-<UTC stamp>.json`. `--from RUN.json` re-renders without calls.
- Not swapped into: `resume.sections` and `resume.lines`, which the rules read for the
  projects section and the unlinked-projects check.

`--budget` caps real spend. Each OpenAI reply's token usage (a JSON repair included; cached
input priced as input) is accumulated in `ats/llm.py` and read per document, and the run stops
before any document whose own worst case would take spend past the budget, saving the
partial run and printing the documents skipped. A single document's worst case over the
budget refuses the run. A document with a failed call is charged its worst case if that is more than was
measured, because a timed-out reply is billed but never reports its usage. Worst case per document is about $0.44; real cost is expected near $3.

**Run the baseline on commit `14c6a89`**, the last commit before ticket 02 changes what
the writer is told. A run on a later commit measures 02, not the baseline. (A
`rewrite-baseline` tag was meant to mark it, but this environment refuses tag pushes.)

    git checkout 14c6a89
    .venv/bin/python scripts/rewrite_harness.py --acceptance-set --no-fixtures --openai-price 0.10,0.50 --budget 4

Its dry run (`--dry-run` added), with the document and per-document lines elided:

    30 resume(s) x (9 content + 3 slop + 3 rewrite + 2 judge and polish) = up to 510 calls
    ...
    Worst case $13.21 in all. Real spend is measured per reply and the run stops before any document that could take it past the $4.00 budget.

**Concurrent documents and timing, 3 October.** The 30-document run took hours: documents
ran one after another, each about seven sequential LLM waits. The harness now takes
`--jobs N` (default 5) and records where the time goes.

- Up to N documents run at once; each document's own steps are unchanged. Usage is
  attributed per document: `llm.usage_key` (a contextvar) names the document a reply is
  recorded under, and `ensemble.gather` runs each call in a copy of the caller's context so
  the key follows it into the worker threads. The app never sets the key, so its behaviour
  is unchanged. A document starts only if what finished documents were charged, plus the
  worst case of every running one, plus its own, is within `--budget`. A document with
  errors, a 429 or a crash included, is still charged max(measured, worst case), so late
  threads and timed-out calls stay inside the cap. Per-document spend stays exact.
- The saved run and the table list documents in target order whatever order they finish
  in; the partial run is saved when the budget stops it; a progress line prints as each
  document starts and finishes.
- `ats/llm.py` logs each OpenAI reply's wall-clock seconds and records reasoning tokens
  apart from output. The three passes record their seconds in `meta["seconds"]` and pass 3
  its generate, judge and polish steps in `meta["step_seconds"]`, so the app's run_meta
  (pass1, pass2, pass3, and pass3 from `generate_rewrites`) shows them too.
- Each document records the seconds of before, slop, rewrite (and generate, judge, polish),
  control, after, its total and its slowest single reply, plus reasoning and visible output
  tokens. The table adds the median and max of each, and the summary carries the seconds.
- With `--jobs`, a budget below N worst cases runs fewer than N at once: at $0.47 a
  document, `--budget 1` would run two at a time, then one.

This harness now runs on code after ticket 02, so a timing run measures the post-02 prompt.
The baseline is still commit `14c6a89`, which has no `--jobs`. The shorter timing run, on
five drawn documents from shortest (902 characters) to longest (2,418):

    .venv/bin/python scripts/rewrite_harness.py --docs 15-backend-junior-no-ai,19-academic-terse-mid,06-data-platform-senior,30-junior-genai-product,10-new-grad-agentic --openai-price 0.10,0.50 --budget 2.5 --jobs 5

Its dry run (`--dry-run` added), with the path lines elided:

    5 resume(s) x (9 content + 3 slop + 3 rewrite + 2 judge and polish) = up to 85 calls (a resume with no text layer is skipped before any call)
    ...
      15-backend-junior-no-ai worst case $0.47
      19-academic-terse-mid worst case $0.47
      06-data-platform-senior worst case $0.47
      30-junior-genai-product worst case $0.47
      10-new-grad-agentic worst case $0.47
    Worst case $2.35 in all. Real spend is measured per reply and no document starts that could take it past the $2.50 budget, counting the worst case of every running one (5 at once).
