type: task (AFK)
status: open
claimed:
blocked-by: —

# Move the criteria into the program

## Question

The rubric's five specs are JSON files in `docs/wayfinder/rubric-grounding/criteria/`,
and the code that turns criterion answers into a band and a value is `band_of` in
`scripts/criteria_probe.py` — a documentation folder and a one-off measurement script.
`ats/` cannot see either. Nothing else on this map can start until it can.

Move both into the package, with no change in behaviour to anything.

## What moves, and what must not break

- The five specs become package data the program loads. They stay the same files in
  content; if they move on disk, every document that links to them is updated in the
  same commit.
- `band_of`, the `when`-clause evaluator, `leverage`, and the spec loader move into
  `ats/`. They are the rubric, not a script's internals.
- **The deterministic judges stay in the script.** They exist to measure criterion
  agreement, not to score a resume — `deterministic_verdict` and its five answer kinds
  are measurement scaffolding, and pulling them into the package would put a second,
  unwired rule channel next to the real one.
- `scripts/criteria_probe.py` keeps working and keeps printing the same numbers.
  `tests/test_criteria_probe.py` keeps passing unchanged where it can, and its
  properties — total, monotone, the two lookup shapes — move to wherever the lookup now
  lives.

The bar for "no change in behaviour" is exact: `python scripts/criteria_probe.py`
prints the same five verdicts as it does today (53/55 LOOK, 44/48 unmeasured, 54/55
PASS, 54/55 LOOK, 54/55 LOOK).

## Why this shape

The other map settled that the band lookup is data, not code: rules are `when` clauses
in the spec and `band_of` evaluates them in order, so a sixth category adds no branches.
That property is what makes this a move rather than a rewrite, and it is worth keeping
in a test after the move.

Done when: `ats/` loads the five specs and computes a band from a set of criterion
answers; the probe script and its tests still run and still print the same numbers; and
nothing else in the program has changed.
