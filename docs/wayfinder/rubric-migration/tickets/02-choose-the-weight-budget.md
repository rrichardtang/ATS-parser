type: grilling (HITL)
status: closed
claimed: claude
blocked-by: 01

# Choose the weight budget

## Question

Four of the eight category weights are derived from document frequency, and 09 built
`derived_weights(counts, total, budget)` to derive them. **`budget` has never been
chosen.** It is the number of the composite's 100 points that the four behaviour
categories share, and 09 left it a parameter deliberately: *"04 settled that df sets
these weights and left how many of the composite's 100 points the derived block gets
explicitly open. This is the derivation; the number it divides is still authored."*

Two questions, and the second is the interesting one:

1. **The budget.** 04 illustrated with the authored block held at today's 50, which
   gives 15 / 15 / 12.5 / 7.5 — *"an illustration, not a specification"*. At 40 the
   derivation gives 12 / 12 / 10 / 6.
2. **Proportional or tiered.** Proportional splits 6:6:5:3, so `AI-assisted coding
   fluency` is worth half of `Agentic systems`. ramp states it as a hard expectation —
   *"This is how the team works, and we expect you to be excellent at it"* — and
   document frequency cannot see the difference between a hard requirement in three
   postings and a passing mention in three.

## Do not answer this in the abstract

Blocked by 01 so it can be answered against output. After 01 the program can compute a
band per category for a document without any provider: the deterministic judges in the
probe already do it for all five categories on eleven documents each. Multiply band
values by candidate weights, add the rule deductions that already run, and every
candidate budget produces a composite per fixture that can be read and argued with.

The comparison to make it against is the current rubric, which scores the same seven
fixtures today, rules-only, no LLM.

**This is also the first time the five categories will have been looked at together on
one document.** Everything the other map measured was one category in isolation. A
category set can be individually sound and collectively wrong — two categories that
both punish the same weak resume, or a strong resume that lands mid-table because its
strengths sit in the light categories — and this is the ticket where that becomes
visible, whatever it decides about the budget.

Done when: the budget and the proportional-versus-tiered question are both answered,
with the composite table that justifies them; and the sanity check above is recorded —
what the new rubric does to the seven fixtures against what the old one does, including
anything that ranks in a way nobody would defend.

## Answered

**Budget 50, split in proportion to document frequency** — 15 / 15 / 12.5 / 7.5, with
`Resume craft` 25 and `Parseability` 15, `Structure` 5, `Title` 5 held at today's
numbers. 04's illustration, adopted as the specification.

The full argument, the composite table it rests on and the sanity check are in
[weight-budget.md](../weight-budget.md). The short form:

- **50** because it holds the authored block at today's numbers, so the migration moves
  one variable rather than two on a test set that cannot separate them; because the
  only disagreement anyone has measured (one adjacent band, 1 document in 11) costs
  1.9–3.8 composite points against a tolerance of 5; and because 60 would price
  `Resume craft`, which holds 19 deducting rules and has zero inter-judge variance,
  below `Agentic systems`, which has no rule channel at all.
- **Proportional** because a floor is an authored constant inside the block whose whole
  stated property is *derived, never authored*, and because on these documents it is
  worth about one composite point: it lowers the worst-case agreement cost from 12.8 to
  12.1 and raises `AI-assisted coding fluency`'s from 6.4 to 8.1, buying nothing net.
  02's objection is not refuted — it is a question about `jd_dimensions.scan` reading a
  boolean where requirement strength is what matters, and it goes back to the other map
  rather than being patched into the weights here.

## The sanity check, and what it found

The seven fixtures were scored under the new rubric at seven candidate weight sets and
printed beside today's rules-only composite. Three findings, in order of how much they
matter:

**1. Two of the five judged categories are constant on this test set.** `Agentic
systems` and `AI-assisted coding fluency` are band E on every fixture, including
`strong` — 60 recorded criterion answers, all `no`. The fixtures were written before
those categories existed and none of them mentions an agent or a coding assistant. So
22.5 of the composite's 100 points carry no information here, which is what the ~18
point drop on every fixture actually is, and why raising the budget lowers every score
monotonically.

This is the collective-soundness failure the ticket predicted, arriving from a
direction it did not: not two categories punishing one resume twice, but two categories
saying nothing at all. It makes **08 more urgent** and means **09 must not measure
tolerance on the fixtures** — agreement measured where a fifth of the composite is a
shared constant is agreement about nothing. Both recorded on the map.

**2. The budget does not change what the rubric ranks.** Rank order is identical under
every candidate and identical to today's, except `slop` and `hidden_text` swapping
below budget 60 — and `hidden_text` is pinned at the fraud cap of 40 in every column,
so that is the cap moving, not a weight. The budget decides level, not order.

**3. `Agentic systems` can fail the composite tolerance on its own**, and no budget
fixes it. At `rule_share` 0 and weight 15, a C1 split costs 12.8 composite points
against a bar of 8; getting under the bar by weight alone needs a budget near 31. This
is the one thing found here that the ticket could not settle, and it is raised on the
map for 09.

### Rankings recorded rather than fixed

- **`two_column` (72.7) outranks `buried_evidence` (70.5)** — a resume no parser can
  read scores above one that parses cleanly and buries its evidence. Inherited, not
  caused: today's rubric does the same at 93.6 against 91.3, and the new one narrows
  the gap. On the map as unspecified.
- **`strong` gets a C.** Entirely finding 1's constant; not the rubric grading harshly.
- **`no_phone` ties `strong` to within 0.2 points.** The anti-hard-gate clamp working
  as designed, unchanged from today.

### Changed

- `scripts/weight_budget.py` — new. A measurement, not a scoring path; nothing in
  `ats/` imports it. It assembles the new rubric from parts already decided: today's
  rules refiled by 07 §1–§4 with 12's three rulings, bands from `ats.rubric.band_of`
  over the recorded model judge's answers, and `score.py`'s own blend and caps. The
  `old` column is `score.build` itself, not a model of it.
- `tests/test_weight_budget.py` — new. 49 rule ids through the mapping, which raises
  rather than defaulting, so a rule added later without a home fails the suite; that
  every candidate spends exactly 100 points; and that the chosen weights are the ones
  `derived_weights` produces.
- `docs/wayfinder/rubric-migration/weight-budget.md` — new: the tables, the argument,
  and the assumptions the numbers rest on.
- `docs/wayfinder/rubric-migration/MAP.md` — two decisions recorded, two open questions
  added, and the weights row of "What exists to migrate" updated.
