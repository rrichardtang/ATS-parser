# The weight budget, and the first look at all five categories on one document

Ticket [02](tickets/02-choose-the-weight-budget.md). Measured by
`scripts/weight_budget.py`, which scored the seven fixtures under the new rubric at
every candidate budget and printed today's rubric beside it.

> **The tables below were printed before ticket 03.** They came from a *model* of the
> new rubric, assembled in the script out of decisions that had not yet been
> implemented, because there was no other way to see a composite before the swap. 03
> implemented them, so the model is gone: the script now reads
> `config.category_weights()` and `score.rule_shares()` and prints only §3, the part a
> single run still cannot produce. §1 and §2 are the before picture and are kept as
> printed — the old column in §1 cannot be regenerated at all now, which is the
> ordering problem the map's *run both, replace last* section is about.

## The answer

**Budget 50, split in proportion to document frequency.**

| category | weight | how |
|---|---|---|
| Production ownership | 15 | derived, 6/6 |
| Agentic systems | 15 | derived, 6/6 |
| Evaluation rigour | 12.5 | derived, 5/6 |
| AI-assisted coding fluency | 7.5 | derived, 3/6 |
| Resume craft | 25 | authored |
| Parseability | 15 | authored |
| Structure & formatting | 5 | authored |
| Title & seniority alignment | 5 | authored |

This is 04's illustration, adopted as the specification. `derived_weights(counts, 20,
50.0)` on the digest's own counts produces the four derived numbers exactly;
`Parseability`, `Structure` and `Title` keep today's authored numbers, and `Resume
craft` gets 25, which is what `Recruiter scan` (15) and `Writing quality` (10) — the
two categories 04 retires and 12 put under `Gate.RECRUITER` — are worth today.

**Ticket 03 implements this**, and it is a number that has to live somewhere the
program reads. `derived_weights` takes `budget` as a parameter and nothing supplies it
yet.

### Why 50 and not 40 or 60

Not because the fixtures preferred it — they cannot tell the budgets apart in any way
that matters (§2). Three reasons, in order:

1. **It changes one variable.** At 50 the authored block is today's authored block,
   number for number. The migration is then a category swap, and a composite that
   moves is the category set moving, not a weight edit riding along with it. 40 and 60
   change both at once, on a test set that cannot separate them.
2. **The agreement cost is inside the bar.** The only disagreement anyone has measured
   is an adjacent band, in 1 of 11 documents per category. At budget 50 an adjacent
   band costs 1.9–3.8 composite points, against an inherited tolerance of 5. 40 buys
   about half a point of headroom and 60 spends about half a point.
3. **60 starves the reliable channel.** `Resume craft` at 15 holds 19 deducting rules
   (07 §5), more than every other category combined. That is the channel with zero
   inter-judge variance, and pricing it below `Agentic systems`, which has no rule
   channel at all, inverts what is actually known about each.

The case against 50 is 40's, and it is real: 40 gives the most room against the
worst-case agreement failure in §3. It was not taken because that failure is not the
budget's to fix — see §3.

### Why proportional and not a floor

02's objection is sound and is not answered by these numbers: document frequency cannot
tell a hard expectation stated in three postings from a passing mention in three, and
ramp states AI-assisted coding as the former — *"this is how the team works, and we
expect you to be excellent at it"*. Proportional prices that at half of `Agentic
systems`.

The alternative measured was a floor at two thirds of the top share (14.29 / 14.29 /
11.9 / 9.52), which keeps the corpus's ordering and only stops it being read to one
decimal place off six documents. It was not taken:

- **It is worth about one composite point.** `strong` scores 78.5 proportional and 77.4
  floored. Every fixture moves by around a point and none changes rank.
- **It trades one exposure for another.** The floor lowers the worst-case agreement
  cost from 12.8 to 12.1 by moving weight off `Agentic systems`, and raises
  `AI-assisted coding fluency`'s own from 6.4 to 8.1 — from comfortably inside the fail
  threshold to sitting on it. Net, nothing is bought.
- **It puts an authored constant inside the derived block**, whose entire stated
  property is *derived, never authored* — add a seventh posting and the weights move
  with nobody editing anything. A floor is a number someone chose, and it is a number
  that would then need defending on every future corpus.

The objection survives the decision and belongs to the corpus, not the weights: if
three postings stating a behaviour as a hard requirement should outweigh three
mentioning it in passing, then `jd_dimensions.scan` should be reading requirement
strength, and today it reads a boolean per posting. That is a question for the other
map, and it is recorded there rather than patched here.

## 1. What the new rubric does to the seven fixtures

`python scripts/weight_budget.py`

```
fixture              old  40 proportional  45 proportional  50 proportional  55 proportional  60 proportional       50 floored       40 floored
strong             96.7A           82.6 B           80.6 B           78.5 C           76.5 C           74.5 C           77.4 C           81.7 B
slop               58.9F           36.5 F           37.7 F           38.8 F           40.0 F           41.2 F           38.4 F           36.2 F
two_column         93.6A           76.5 C           74.6 C           72.7 C           70.7 C           68.8 D           71.6 C           75.6 C
hidden_text        40.0F           40.0 F           40.0 F           40.0 F           40.0 F           40.0 F           40.0 F           40.0 F
scanned             0.0F            0.0 F            0.0 F            0.0 F            0.0 F            0.0 F            0.0 F            0.0 F
no_phone           96.5A           82.4 B           80.4 B           78.3 C           76.3 C           74.3 C           77.2 C           81.5 B
buried_evidence    91.3A           72.3 C           71.4 C           70.5 C           69.5 D           68.6 D           69.4 D           71.4 C
```

The `old` column is not a model of anything. It is `score.build` on the same findings,
which is what `python app.py` does today with no provider credentials.

**Rank order is the same under every candidate**, and the same as today's, with one
exception: `slop` and `hidden_text` swap places below 60. `hidden_text` is pinned at
the fraud cap of 40 in every column, so that swap is the cap moving past `slop`, not a
weight doing anything.

So the budget does not decide what the rubric *ranks*. It decides what it *scores*,
uniformly, and the reason is §2.

## 2. Two of the five judged categories are constant on this test set

`python scripts/weight_budget.py --categories`

```
category                        weight        strong          slop    two_column   hidden_text       scanned      no_phoneburied_evidence
Parseability                     15.00           100           100            88            75             0           100           100
Structure & formatting            5.00           100            95            69            90             0            96            87
Title & seniority alignment       5.00           100            95           100           100             0           100           100
Resume craft                     25.00          98 A           3 E          93 B          87 C     0 no band          98 A          74 B
Production ownership             15.00          97 A          41 E          97 A          75 C    0 withheld          97 A          97 A
Agentic systems                  15.00          10 E          10 E          10 E          10 E     0 no band          10 E          10 E
Evaluation rigour                12.50          97 A          41 E          87 B          46 E     0 no band          97 A          87 B
AI-assisted coding fluency        7.50          10 E          10 E          10 E          10 E     0 no band          10 E          10 E
COMPOSITE                       100.00          78.5          38.8          72.7          40.0           0.0          78.3          70.5
  (today, rules only)                           96.7          58.9          93.6          40.0           0.0          96.5          91.3
```

`Agentic systems` and `AI-assisted coding fluency` are **band E on every fixture,
including `strong`**. Not roughly — the recorded model judge answered all five criteria
`no` on all six judgeable fixtures, 60 answers, all the same. The fixtures were written
before those categories existed and none of them mentions an agent or a coding
assistant.

That is 22.5 of the composite's 100 points carrying no information about these
documents, and it explains the whole shape of §1:

- **Every composite drops by about 18 points.** `strong` 96.7 → 78.5, `no_phone` 96.5 →
  78.3, `buried_evidence` 91.3 → 70.5. Almost all of it is the constant.
- **Raising the budget lowers every score monotonically**, because half the derived
  block is a fixed 10. That is a property of the fixtures, not of the rubric, and it is
  why "which budget scores better" is not a question these documents can answer.

**This is the collective-soundness failure 02 predicted, arriving from an unexpected
direction.** The ticket expected two categories double-punishing a weak resume, or a
strong resume landing mid-table because its strengths sit in the light categories. What
happened instead is that two categories say nothing at all, and their weight lands on
every document identically.

Two consequences worth carrying forward:

- **Ticket 08 gets more urgent, not less.** The map already says the test set is thin.
  It is worse than thin for this half of the rubric: on the behaviour block the seven
  fixtures test `Production ownership` and `Evaluation rigour` and nothing else. The 29
  band probes are the only documents that exercise `Agentic systems` and `AI-assisted
  coding fluency`, and they are single-category text files, not resumes a composite can
  be computed from.
- **The acceptance test (09) must not run on the fixtures.** A tolerance measured where
  22.5 points are a shared constant would be measuring agreement about nothing.

### Three rankings worth naming

1. **`two_column` (72.7) outranks `buried_evidence` (70.5).** A resume no parser can
   read scores above one that parses cleanly and buries its evidence. This is
   **inherited, not caused** — today's rubric does the same, 93.6 against 91.3 — and
   the new rubric narrows the gap rather than widening it. It is still not defensible,
   and it is `parse/multi-column` costing 12 points of `Parseability` against a
   document-wide defect. Not this ticket's to fix; recorded so it is not discovered
   again.
2. **`strong` gets a C.** Defensible on its face — the corpus asks for agentic and
   AI-assisted-coding evidence and this resume has none — but it is entirely §2's
   constant. Do not read it as the rubric grading harshly; read it as the fixture being
   silent on 22.5 points.
3. **`no_phone` (78.3) ties `strong` (78.5).** A missing phone number costs 0.2
   composite points. That is the anti-hard-gate clamp behaving exactly as designed, and
   it is unchanged from today's 96.5 against 96.7.

## 3. What one criterion split costs the composite

`python scripts/weight_budget.py --tolerance`

The seven fixtures cannot choose a budget (§2), but the acceptance test can, and it is
a composite tolerance: two judges within 5 points, over 8 fails. A criterion split
moves the band by up to its `widest move` from the leverage table; the band moves the
category score by the gap between band values; the weight turns that into composite
points:

    composite move = band gap × (1 − rule_share) × weight / 100

```
                        Production ownership            Agentic systems          Evaluation rigour AI-assisted coding fluency               Resume craft   worst
candidate                    gate / cheapest            gate / cheapest            gate / cheapest            gate / cheapest            gate / cheapest   total
40 proportional                    6.1 / 1.8                 10.2 / 3.0                  5.1 / 1.5                  5.1 / 1.5                  8.9 / 2.6    10.2
45 proportional                    6.9 / 2.0                 11.5 / 3.4                  5.7 / 1.7                  5.7 / 1.7                  7.7 / 2.3    11.5
50 proportional                    7.7 / 2.2                 12.8 / 3.8                  6.4 / 1.9                  6.4 / 1.9                  6.4 / 1.9    12.8
55 proportional                    8.4 / 2.5                 14.0 / 4.1                  7.0 / 2.1                  7.0 / 2.1                  5.1 / 1.5    14.0
60 proportional                    9.2 / 2.7                 15.3 / 4.5                  7.7 / 2.2                  7.7 / 2.2                  3.8 / 1.1    15.3
50 floored                         7.3 / 2.1                 12.1 / 3.6                  6.1 / 1.8                  8.1 / 2.4                  6.4 / 1.9    12.1
40 floored                         5.8 / 1.7                  9.7 / 2.9                  4.9 / 1.4                  6.5 / 1.9                  8.9 / 2.6     9.7
```

**Measured disagreement is inside the bar at every candidate.** The only kind observed
across all five categories is one adjacent band on 1 of 11 documents — the `cheapest`
column, 1.1 to 4.5 points, against a tolerance of 5.

**Worst-case disagreement fails the bar at every candidate**, and it is one category:
a split on `Agentic systems` C1 costs 9.7 to 15.3 composite points on its own. Two
things make it the exposure:

- **`rule_share` 0.** 07 §5 set it there because the category has no deducting rule,
  and a `rule_share` above 0 with no rule scores against a constant, not a channel.
  With no rule channel, none of the disagreement averages away — the whole band move
  reaches the composite.
- **The largest derived weight**, because the behaviour is in 6 of 6 postings.

**The budget cannot fix this and should not be asked to.** Getting `Agentic systems`
under 8 by weight alone needs a budget near 31, which halves the behaviour block to buy
headroom against a disagreement nobody has yet observed. The fix is a rule channel or a
measured decision to accept the exposure, and both belong to the acceptance test.

> **Raised for 09**: `Agentic systems` at `rule_share` 0 and weight 15 can fail the
> composite tolerance on a single criterion split. Note that `jd_dimensions.py` now has
> an `agentic` dimension (6/6) that it did not have when 07 wrote §5 — but 07's
> invariant is about a *deducting rule*, not a dimension, and no rule fires on
> `Agentic systems` today. Either one gets written, or 09 measures the exposure and
> says whether it is real.

## 4. Where the rules land

`python scripts/weight_budget.py --rules` prints the mapping applied to whatever fired.
It is `rule-mapping.md` §1–§4 with ticket 12's three rulings, which are later and win:
`content/bullet-invariants` deducts, `content/quantification` and
`cred/unlinked-projects` become advice-only. Of the 34 rules that fire on the fixtures,
**7 stop deducting** — five `kw/thin-*`, `kw/unsupported-skills` and
`content/quantification` — and `cred/no-named-models` is retired outright. 14 of the
remaining 26 file into `Resume craft`.

`_new_category` raises on a rule it cannot place rather than defaulting, and
`tests/test_weight_budget.py` runs 49 rule ids through it, so a rule added later
without a home fails the suite instead of silently landing in the wrong category.

## Assumptions, stated

- **`content/bullet-invariants` is measured as it fires today.** 12 narrowed it to
  `outcome`, which is a change to the rule and belongs to this map's 04. Narrowing can
  only make it fire less, so `Resume craft` scores here are a floor, not a ceiling.
- **Bands come from the recorded model judge** (`criteria/judgments/`), the only judge
  that answers all five categories — the deterministic judge abstains on `AI-assisted
  coding fluency` C5 by construction. Mixing two judges inside one composite would make
  the number mean nothing.
- **`scanned` scores 0 in both columns.** No text layer, so nothing ran; the composite
  is the unreadable cap, and it is in the table only so the fixture set is complete.
