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

Dry run for the acceptance set (the 30 drawn documents plus the 7 fixtures, as
`--acceptance-set` does in the agreement harness):

    .venv/bin/python scripts/rewrite_harness.py --acceptance-set --dry-run --openai-price 0.10,0.50

    37 resume(s) x (9 content + 3 slop + 3 rewrite + 2 judge and polish) = up to 629 calls
    Worst case $14.80 against a $3.00 budget: over.

At that price a $3 budget covers about 7 documents (`--docs`), or raise `--budget`. The
live command is the same line without `--dry-run`.
