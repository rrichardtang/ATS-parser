type: task (AFK)
status: closed
claimed: claude
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

## What was done

`ats/rubric.py` is the rubric: `SLUGS`, `load_spec`/`load_specs`/`spec_path`, the
`when`-clause evaluator `_clause`, `band_of`, and `leverage`. The five specs are
package data in `ats/criteria/`, loaded with `Path(__file__).with_name(...)` like
`taxonomy.json` and `weights.toml` already are. `ats/` now loads the five specs and
computes a band from a set of criterion answers, which is what everything after this
ticket was waiting for.

`leverage` moved with the lookup rather than staying with the measurement. It reads
nothing but a spec and `band_of` — it is a property of the lookup, and the three tests
that assert the gate structure are the same shape as the totality and monotonicity
ones they sit beside.

The deterministic judge stayed behind, as the ticket required: `deterministic_verdict`,
its five answer kinds and the four document-level ones, `HEDGE_RE`, the four document-level predicates, `load_recorded`,
`read`/`read_probe`, and the reports are all still in `scripts/criteria_probe.py`. The
script imports the rubric from the package and re-exports nothing it does not use.

### Behaviour, checked rather than asserted

The probe's output was captured before the move and diffed against it after, for
`criteria_probe.py`, `--leverage` and `--grid`. All three are byte-identical, so the
five verdicts are the stated ones — 53/55 LOOK, 44/48 unmeasured, 54/55 PASS, 54/55
LOOK, 54/55 LOOK. Nothing else in the program changed: no existing module imports the
new one yet, and `ats/rubric.py` imports nothing from `ats/`.

### Where the properties went

The lookup's properties moved to `tests/test_rubric.py` with the lookup: total,
monotone, ascending band values, the gated shape's three (C1 is the floor, C1 moves the
band from everywhere, C5 costs at most one band) and the count shape's two, plus the
spec-shape assertions. Two are new and both are about the move: the specs load from
inside `ats/`, and an incomplete answer set still names no band.

`tests/test_criteria_probe.py` keeps what is about the probe — recorded verdicts are
complete and binary, the band probes parse and span the ladder, a `yes` carries its
span or the criterion abstains, injected text answers nothing, and an unparsed document
is withheld. It imports the rubric from `ats.rubric` and the judge from the script.

### Changed

- `ats/rubric.py` — new.
- `ats/criteria/*.json` — the five specs, moved from
  `docs/wayfinder/rubric-grounding/criteria/`, unchanged in content. The `judgments/`
  and `probes/` directories stayed: they are the measurement, not the rubric.
- `scripts/criteria_probe.py` — imports the rubric; `CRITERIA_DIR` is now
  `MEASUREMENT_DIR`, since what it points at is the judgments and probes.
- `tests/test_rubric.py` — new; `tests/test_criteria_probe.py` — trimmed to the probe.
- The five `*-criteria.md` documents and `rubric-grounding/MAP.md` — links repointed.
- `docs/wayfinder/rubric-migration/MAP.md` — the decision recorded, and the two rows of
  "What exists to migrate" that this ticket moved.
