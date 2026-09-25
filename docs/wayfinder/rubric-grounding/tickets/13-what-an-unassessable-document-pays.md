type: decision (HITL)
status: closed
claimed: claude
blocked-by: —

# What a document pays when its judged categories cannot be assessed

## Question

Raised by rubric-migration 07's live run. When a resume's roles do not survive
extraction, all five judged categories are withheld: no criterion has a bullet to be
about. Migration 06 left them out of the composite, which renormalises over the three
the parser gate checked. So withholding costs nothing, and on live judges `two_column`,
which no parser can read, scores 86.6 and ranks first of the seven fixtures, 14.2 above
`strong`.

What should a withheld category contribute to the composite?

## Options put to the owner

1. **Score each withheld category at its no-evidence band.** Every criterion `no`,
   through the spec's own lookup: E (10) on all five. No new number.
2. **Leave them out, and cap the composite**, like the fraud cap (40) and the
   unreadable cap (15). Needs an authored cap; at 40 `two_column` still sits above
   `slop` (38.1).
3. **Score them 0.** Harsher, and reads as bad work rather than unreadable work.

## Decided: option 1

The owner chose it on 25 September. `score.no_evidence_values()` runs `band_of` over
all-`no` answers for each spec, and a withheld category scores that. Its loss gets its
own ledger row (`score/withheld`), so the ledger still reconciles without calling it
judgement or rounding. Findings inside a withheld category still cost nothing, as
before. The human gate is a number again: on `two_column`, (5 × 100 + 75 × 10) / 80 =
15.6.

What it costs: the parse defect is charged twice, by `parse/multi-column` in the parser
gate and as missing evidence here. 06 rejected scoring withheld categories for exactly
that reason. The owner's reading is that the second charge is real: a hiring system
that stored no work history forwards nothing for a reader to judge.

Measured on the fixtures (rules-only, since withholding needs no judge):

| fixture | before | after |
|---|---|---|
| two_column | 93.6 (rules-only) / 86.6 (live) | 29.1 |
| hidden_text | 40.0 (fraud cap) | 28.2 |

`scanned` is unchanged at 0: the unreadable path zeroes it first. Against 07's live
numbers the order is now `no_phone`, `strong`, `buried_evidence`, `slop`, `two_column`,
`hidden_text`, `scanned`.

## Changed

- `ats/score.py`: `no_evidence_values`, withheld scoring, the ledger row, `_subscore`
  no longer declines.
- `scripts/side_by_side.py`: withheld rows print the value and the reason.
- Tests in `test_scoring.py`, `test_pipeline.py`, `test_llm_passes.py` and
  `test_side_by_side.py` rewritten from 06's rule to this one.
