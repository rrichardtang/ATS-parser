type: decision (HITL)
status: closed
claimed: claude
blocked-by: —

# `Resume craft`'s rule channel floors on every full-length resume

## Question

Raised by rubric-migration 07. `Resume craft`'s deterministic deductions run 120 to 436
(median 242) over migration 08's thirty drawn documents, against a category that floors
at 0, so the rule channel is 0 on 30 of 30. With `rule_share` 0.7 the category is then
capped at 28.5 whatever a judge answers. On the owner's resume, judged band C (58), it
scored 17.4. How should the rules charge so that the channel still discriminates?

## What floors it

Measured over the thirty, deterministic layer only. Two rules carry almost all of it,
and both fire once per failing bullet at 12 points:

| rule | fired | mean cost | max |
|---|---|---|---|
| `content/no-outcome` | 30/30 | 123.6 | 180 |
| `slop/portable` | 30/30 | 83.2 | 192 |
| `content/first-person` | 22/30 | 11.4 | 36 |
| `content/passive-voice` | 27/30 | 10.3 | 32 |
| everything else | | under 9 each | |

So cost grows with the number of bullets, and a fifteen-bullet resume pays three times
what a five-bullet one does for the same habits.

## Options put to the owner

1. **Charge by share**: severity times the share of bullets that fail. Length-neutral.
2. **Charge once per rule**, however many bullets fail. Simpler; loses how many.

## Decided: option 1

The owner chose it on 25 September. The question put to them named the two big rules,
but the figures shown (55 to 83) were for the per-bullet rules together, and changing
only two leaves the channel length-biased (8.9 to 78.8). So all six `Resume craft`
rules that fire at most once per bullet are charged by share: `content/no-outcome`,
`content/weak-opener`, `content/passive-voice`, `content/first-person`,
`content/long-bullet` and `slop/portable`. `Finding.cost_scale` carries the 1 / bullets,
and `score._cost` multiplies by it before the per-finding clamp. Rules that fire per
match or per pair (`slop/banned-word`, `content/duplicate-bullet`) are unchanged, and
`content/ownership`, per bullet but in `Production ownership`, is outside this ticket.

Measured after, deterministic layer only:

| | before | after |
|---|---|---|
| rule channel over the thirty | 0 on 30 of 30 | 55.0 to 82.7, median 66.4, floored on 0 |
| `Resume craft` at a band-C judge | 17.4 on every one | 55.9 to 75.3 |
| `strong`, `no_phone` rule channel | 88 | 98.3 |
| `slop` rule channel | 0 | 0 |

`slop` stays at 0 on its per-match rules, which is the channel doing its job.

Not touched: `Resume craft` C4 and C5, the judged criteria that get harder with length
(migration 08's finding). That is a separate question about the criteria, not the
rules.

## Changed

- `ats/models.py`: `Finding.cost_scale`.
- `ats/score.py`: `_cost` applies it.
- `ats/rules.py`, `ats/slop.py`: the six rules set it.
- `tests/test_scoring.py`: the same share of weak bullets costs the same at 4 and 16
  bullets. It fails on the old code (44 against 0).
