type: task (AFK)
status: open
claimed:
blocked-by: 03

# Build the inter-judge agreement harness

## Question

The acceptance test — two providers within 5 points per category, >8 fails — cannot
be applied without something that measures it. Build the harness: run each resume
through both providers twice, report per-category spread between providers and
between samples of the same provider, so sampling noise is visible separately from
genuine disagreement.

Inputs: the seven fixtures in `tests/fixtures/` plus the user's real resume.
Blocked by 03 because what it measures depends on whether the model emits scores.

Done when: the harness runs from the command line, prints a per-category table, and
its output is the evidence any rubric change is judged on.
