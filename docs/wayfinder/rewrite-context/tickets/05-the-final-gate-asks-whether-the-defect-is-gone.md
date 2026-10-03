type: task (AFK)
status: open
claimed: claude
blocked-by: 01, 02

# The final gate asks whether the defect is gone

## Question

Should a rewrite that reads better but leaves the named defect in place ship?

## Why it matters

`ensemble.rank_score` rewards four regex invariants, no slop hits and staying under 32
words. A candidate can beat the original by `rewrite_margin` on those and still leave
the criterion unanswered. 02 tells the writer and the ranking judge the defect; this
ticket makes the gate check it.

## What to build

Before a candidate ships, rerun the deterministic rules that fired on the original
against it. A rule that still fires blocks it, the same way an audit problem does. Use
01's numbers to decide whether a model re-check of the criterion is worth its calls as
well, or whether 02 already fixes enough without it.

## Done when

The gate blocks a candidate that keeps its rule defect, tests cover it, the decision on
the model re-check is recorded here with 01's number behind it, and Felix has approved it.

## Found
