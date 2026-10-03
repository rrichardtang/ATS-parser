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
