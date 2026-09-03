type: task (AFK)
status: closed
claimed: claude
blocked-by: 04

# Teach the dimension scan the behaviours the categories name

## Question

Ticket 04 made category weight a function of document frequency: how many postings
state the behaviour a category measures. The digest cannot currently compute that.

| category | inventory (02, hand-read) | `jd_digest.json` now |
|---|---|---|
| Production ownership | 6/6 | production 6/6, ownership **1/6** |
| Agentic systems | 6/6 | **no dimension exists** |
| Evaluation rigour | 5/6 | **3/6** |
| AI-assisted coding fluency | 3/6 | **no dimension exists** |

`ats/jd_dimensions.py` is five regex sets — ownership, production, evaluation,
seniority, leadership — and two of the four new categories have no pattern at all.
Ownership reads 1/6 against a corpus that is 6/6 because the regexes require `own`
adjacent to production/lifecycle/end-to-end, and the corpus says it many other ways.

This is the same defect family as 01 (headers the vocabulary never saw) and 02 (a
57-noun taxonomy against a corpus that converges on verbs), one layer further down.
02's inventory is the ground truth to reproduce: every count there is recorded with
at least one verbatim quote, so each is checkable by hand.

Two things this must do, not one:

1. **Reproduce 02's counts on the current six postings.** A pattern set tuned until
   the numbers match is worth little on its own — the counts are the test, not the
   goal.
2. **Compute weights for postings added later.** The whole point of deriving weight
   from the corpus is that a seventh posting moves it with nobody editing anything.
   Patterns fitted to these six specifically would defeat that, so the failure mode
   to design against is overfitting to the corpus that exists.

Also in scope, because 04's decision makes them wrong to leave: `RULE_DIMENSION` drops
its four double-counting entries (`content/ownership`, `cred/no-production`,
`cred/notebook-only`, `cred/no-evaluation`) and keeps `title/seniority-mismatch`,
whose category retains an authored weight. `leadership` is tracked with no scoring
target and should be reconsidered or removed while the file is open.

Note on scope: this is execution, and the map's destination is a spec. It is carried
here by the exception recorded in the map's Notes, because it is the precondition for
04's weights being computed rather than transcribed.

Done when: `jd_dimensions.py` reproduces 02's counts for all four behaviours on the
current corpus, the patterns are covered by tests using verbatim posting text, the
weight derivation is demonstrated on a corpus with a posting added, and
`RULE_DIMENSION` no longer double-counts.

## Answer

**`ats/jd_dimensions.py` reproduces 02's four hand-read counts exactly — 6/6, 6/6,
5/6, 3/6 — from eight behaviour dimensions, four of them new. The full record, with
the matched phrase behind every hit, is [dimension-scan.md](../dimension-scan.md).**

| category | dimensions | 02 | before | now |
|---|---|---|---|---|
| Production ownership | `production` ∪ `ownership` ∪ `reliability` | 6/6 | production 6/6, ownership **1/6** | **6/6** |
| Agentic systems | `agentic` | 6/6 | no dimension | **6/6** |
| Evaluation rigour | `evaluation` | 5/6 | **3/6** | **5/6** |
| AI-assisted coding fluency | `ai_assisted_coding` | 3/6 | no dimension | **3/6** |

Every hit fires on the sentence `inventory.md` quotes for that posting, which is the
check that matters — the pattern agrees with the human reader's reason, not just their
number. The two counts that are *not* 6/6 are the load-bearing ones: evaluation must
miss ramp, and AI-assisted coding must hit exactly amex, fluidstack and ramp. A pattern
set generous enough to read 6/6 on both would be matching the corpus's general
vocabulary rather than reproducing anything. Both are asserted directly.

### Against overfitting

**A pattern is a family, not a sentence** — a verb set crossed with an object set, with
`_SHIP` and `_DESTINATION` shared across dimensions so a verb cannot be spelled out in
one and forgotten in another. Anything matching only one posting's phrasing belongs in
the test file, not in `DIMENSIONS`.

The tests enforce it from both ends: corpus tests on verbatim posting text, and
generalisation tests on phrasing that appears nowhere in the six (*"steward each
initiative from kickoff to rollout"*, *"carry the pager"*, *"benchmark candidate
models"*, *"Pair with Cursor and Copilot daily"*), plus a negative case that must hit
nothing. The honest limit: those phrasings are ones I wrote knowing the patterns, so
this guards against the narrowest overfitting rather than proving coverage. The real
test is the seventh real posting, and the failure it would show is a **false negative**
— a behaviour stated in words no family anticipated.

### Two dimensions that are not category weights

- **`reliability` split out of `production`.** `\breliability\b` was an alternative
  inside the production list, so a posting could read "production" on the word
  *reliable* alone. Two behaviours, both 6/6; 04 merges them at the category level,
  which is a judgement about what a judge can separate, not a reason to conflate them
  in the scan. The union costs nothing and each count now means one thing.
- **`experience_gate` recorded, never scored.** 02 found three postings gate on years
  while `seniority` read 0/6. Adding years to `seniority` would have silently changed
  what `title/seniority-mismatch` costs, so the numeric gate is its own dimension with
  no target — the digest stops being blind to half the corpus, and nothing moves.
- **`leadership` removed**, as the ticket invited: no target, 0/6, and a dimension
  nothing consumes is an invitation to wire it up without deciding what it should cost.

### The derivation, demonstrated

`derived_weights(counts, total, budget)` splits a budget in proportion to df — at
budget 40 on this corpus: 12.0 / 12.0 / 10.0 / 6.0. **`budget` is a parameter, not a
constant**, because 04 settled that df sets these weights and left the point split
explicitly open on the map. This is the derivation; the number it divides is still
authored.

A seventh posting is demonstrated in
`test_a_seventh_posting_moves_the_weights_with_nobody_editing_anything`: one asking for
evals and nothing agentic takes `Evaluation rigour` 5/6 → 6/7 and lifts its weight,
while `Agentic systems` holds at 6 and its weight falls, because the budget is shared.
No edit to `jd_dimensions.py` or `weights.toml`.

The digest carries `category_document_frequency` computed at build time, not summed
from the per-dimension counts: a category is a union, so a posting stating two of its
behaviours must still count once, and that cannot be recovered from the totals.

### `RULE_DIMENSION`, and a finding the ticket did not ask for

The four double-counting entries are gone and `test_jd_digest_wiring.py` now asserts it
— with every behaviour dimension at 6/6, all four must return exactly 1.0.
`cred/notebook-only` was doubly dead: 07 had already stopped it deducting.

Measuring the survivor turned up this: `Title & seniority alignment` is weighted 5 of
100, so **the largest composite movement the whole multiplier mechanism can now produce
is 0.05 points** — below the report's own rounding, which is why its test had to be
rewritten to assert on the category score. `dimension_multiplier()` is a digest field,
a scoring hook and its own test file, for an effect no user can see. Not removed here,
because 04 kept the entry deliberately and this ticket's brief was to stop the double
count; recorded as the case for retiring it.

### Changed

- `ats/jd_dimensions.py` — rewritten: eight behaviour dimensions, `CATEGORY_DIMENSIONS`,
  `categories_for`, `category_document_frequency`, `derived_weights`.
- `ats/config.py` — `RULE_DIMENSION` down to `title/seniority-mismatch`.
- `scripts/build_user_corpus.py` — records and prints `category_document_frequency`.
- `ats/jd_digest.json` — regenerated.
- `tests/test_jd_dimensions.py` — rewritten: corpus counts, generalisation, derivation.
- `tests/test_jd_digest_wiring.py`, `tests/test_build_user_corpus.py` — updated for the
  new mapping and the new digest field. 211 tests pass.
- `docs/wayfinder/rubric-grounding/dimension-scan.md` — new: the record above.
- `docs/wayfinder/rubric-grounding/MAP.md` — the decision recorded.
