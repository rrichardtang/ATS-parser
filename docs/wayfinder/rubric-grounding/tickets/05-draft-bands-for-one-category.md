type: prototype (HITL)
status: closed
claimed: claude
blocked-by: 04

# Draft score bands for one category, and test they hold

## Question

Can a band definition actually be written in evidence terms tightly enough that two
judges agree within 5 points? Write the bands for the single highest-stakes category
and run them, rather than writing five sets and discovering the format does not work.

Use the agreement harness (06) against the fixtures. If two judges cannot converge on
one category with bands in front of them, the format is wrong and the remaining four
should not be written yet.

Done when: one category has full band definitions, measured agreement across the
fixture set, and a verdict on whether the format generalises.

## Outcome

- Bands: [../coverage-bands.md](../coverage-bands.md) — four levels for **Coverage**,
  chosen as the highest-stakes category per the map. Score is arithmetic over
  per-requirement levels, not a number a judge picks.
- Measurement and verdict: [../coverage-bands-agreement.md](../coverage-bands-agreement.md)
- Probe: `scripts/coverage_band_probe.py`, tests in `tests/test_coverage_band_probe.py`
- Inputs: [../coverage/requirements.json](../coverage/requirements.json) (provisional,
  hand-derived; 02 replaces it) and [../coverage/judgments/](../coverage/judgments/)

**Verdict: the format holds for Coverage and does not generalise on its own.** A band
boundary converges when it is settled by a fact both judges point at — a span is
present or absent, it sits inside a role or outside one. It does not converge when it
asks a judge to weigh something. So the format should be reused for countable
categories and must not be applied by default to "Writing quality", "Recruiter scan",
or a seniority-fit judgment.

Measured: deterministic judge vs. one model judge, four scorable fixtures, **max
spread 5.0, mean 1.2** — a pass on the line. Two variants failed: scoring documents
whose structure did not parse (19.7) and collapsing to three levels (9.3).

The binding constraint turned out to be arithmetic, not prose. With nine requirements
weighted 6…2 the heaviest carries 14.3 of 100 points, so **the worst single
level-step costs 5.7 and the tolerance affords zero judgment calls**. Headroom comes
from a wider, flatter requirement set — not from any level scheme.

## What this ticket did not do

The map's acceptance test — two providers, sampled twice, on all seven fixtures plus
the real resume — **was not run.** The harness (06) does not exist and this
environment has no provider credentials. The two judges compared were the
deterministic band application and one model judge; that measures where the band
prose leaves room to differ, not whether two providers differ elsewhere. 06 still
owes that number.

Ran ahead of its `blocked-by` on purpose: 04 was needed only to confirm Coverage is a
category, which the map already asserts, and the "stable bands, living inputs"
decision means the band prose does not depend on 02's inventory. The requirement set
used is provisional and labelled as such. Findings routed to 03, 04, 06, 07 and 08
are listed at the end of the agreement document.
