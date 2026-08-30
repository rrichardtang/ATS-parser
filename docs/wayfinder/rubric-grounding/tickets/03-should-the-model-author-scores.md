type: grilling (HITL)
status: closed
claimed: claude
blocked-by: —

# Should the model author category scores at all?

## Question

Today the model returns a 0–100 number per category and `ensemble.combine_scores`
averages across providers, banding where they differ by ≥12. The observed spreads
were 13, 16 and 22.

The alternative: the model emits only evidenced findings, and the composite is
computed deterministically from finding counts and severities. Cross-provider score
disagreement disappears by construction — there is no model-authored number left to
disagree about — and the ensemble's score-averaging machinery becomes redundant.

This is the fork that reshapes everything downstream: if the model stops scoring,
"score bands" means something different, and the acceptance test measures agreement
on findings rather than on numbers. Settle it before designing categories.

## Decision

**No. The model authors no number — and it does not stop at findings either.**

It names one **band** per category from a written set, and cites the evidence that
puts the resume in it. The band's value is a lookup from the rubric, not a quantity
the model chose. Findings stay, with their mandatory quote, as the evidence for the
band and as the fix list — but for model-scored categories **they no longer deduct**.

The split, stated as a property rather than a preference:

| channel | who authors it | inter-judge variance |
|---|---|---|
| continuous movement | deterministic rules | zero, by construction |
| discrete placement | the model, as a band label | measurable as label agreement |
| ~~continuous placement~~ | ~~the model, as a number~~ | ~~unbounded, unanchored~~ |

The third row is what is being removed. It is the only component of today's composite
whose disagreement has no ceiling and no anchor.

## Why the fork as posed is the wrong fork

Both branches of the question survive contact with the code less well than they read.

**The 13/16/22 evidence does not indict continuous scoring.** It indicts *unanchored*
scoring, which nobody is defending. `prompts.CONTENT_SYSTEM` says "Score each category
0-100 with a one-line justification"; `prompts.content_user` passes
`CATEGORY_NAMES` as bare labels. Nothing in that prompt says what a 70 requires that a
55 does not. Those spreads are what an unanchored scale does, and this whole map exists
to add the anchors. Concluding "the model shouldn't score" from that run is drawing a
conclusion the experiment cannot support.

**"Disagreement disappears by construction" is false.** It relocates, into a quantity
with worse properties. Measured against the real scoring code (`ats/score.py`, with
today's weights):

| what the two judges differ on | composite spread |
|---|---|
| the number, on one category, by 22 | **2.9** |
| the number, on all five, by 13 / 16 / 22 | **5.2 / 6.4 / 8.9** |
| how many findings to write: 3 vs 7, one category (today's blend) | **4.3** |
| how many findings to write: 3 vs 7, all five (today's blend) | **15.9** |
| how many findings to write: 3 vs 7, all five (findings-only) | **34.4** — 48 per category |

Like for like on one category, the worst score disagreement ever observed (2.9) already
costs less than a four-finding difference in how one judge chose to split up the same
defects (4.3) — and that is measured against the *diluted* finding channel, which today's
blend weights at 0.4. Take the number away and that same four-finding difference is worth
48 points on the category.

Nothing in the prompt tells a judge how many findings a resume of a given quality should
have, so count is *less* anchored than the number it would replace, not more — and it is
unbounded above, while a score is trapped in [0, 100].

(Setup, so it can be re-derived: `score.build` with today's `weights.toml`, five
model-scored categories, N content findings each at `Severity.MAJOR` as
`passes.content_pass` emits them, model numbers held equal between the two judges except
where the row says otherwise.)

The trap is structural, not a tuning problem. If the composite is linear in finding
count with slope `s`, and judges differ by `Δn` findings on a category, they differ by
`s·Δn` points. Holding that under the 5-point bar at a plausible `Δn` of 4 needs
`s ≤ 1.25` — at which point it takes 20 findings to move a category 25 points, and the
findings channel can no longer discriminate at all. There is no `s` that is both robust
to count disagreement and able to score.

**And counts cannot express a positive property.** `Coverage` — does the resume evidence
the skills these postings require — is the axis ticket 04 calls the most direct reading
of the destination. A findings-only composite can only subtract, so it reaches that
property by inventing one finding per missing skill: at which point the count *is* a
score, computed worse. Every category would floor near 100 for anything decent and lose
its ability to separate a strong resume from an adequate one.

## What the model emits, after this

- **A band label per category**, from the set ticket 05 writes, plus the one line of
  resume evidence that places it there.
- **Findings**, unchanged in shape: rule id, message, fix, and the exact quote. The
  evidence rule is untouched — a finding without a quote is still discarded.
- **No number of any kind.**

An anchored 0–100 scale is the same design with a permissive last step: the model picks
a point *inside* its band. So the difference between this decision and the runner-up is
exactly one field, which makes it cheap for ticket 05 to test rather than argue about.

## Consequences

**The double count is closed.** Today the same judgment moves the score twice: a content
finding deducts its severity from the category (`Severity.MAJOR` → 12 points, clamped at
the category weight by `score._cost`, so 10 in Credibility and Writing) *and* drags the
model's number down, and the two are blended at 0.4/0.6. That is one opinion counted
through two channels, which is what makes the finding-count sensitivity above so large.
Model findings become evidence and fixes; the band owns the number.

**The score still moves on small edits.** This was the real cost of discretising, and
deterministic rules absorb it: every category has them — 4 in Impact, 7 in AI/ML
relevance, 7 in Credibility, 8 in Writing, 5 in Recruiter scan. They are continuous,
reproducible, and identical between judges. Bands place the substance judgment; rules
supply the resolution underneath it.

**Counts re-enter, bounded.** A band definition may say "more than half the bullets state
an outcome the candidate owned". That is a count — but a *stated threshold inside a band*,
shared by both judges and bounded by the band structure, not an unbounded multiplier on
whatever a judge chose to write down.

**Severity on content findings becomes presentational.** `passes.content_pass` hardcodes
`Severity.MAJOR` for every one of them today, so nothing is lost — but it does mean the
field now orders the fix list rather than moving the score, closing a second latent
disagreement axis before anyone had to measure it.

**`ensemble.combine_scores` is replaced, not deleted.** Averaging labels is meaningless.
Band adjudication instead: same band → that band; adjacent → report the span and mark it
contested; non-adjacent → flag the run, because that is a rubric failure, not a property
of the resume. Its `(mean, low, high)` return shape survives, so `score.build`'s
interface holds.

**A naming collision gets worse and should be fixed.** `/CONTEXT.md` already warns that
the report's "banded" means something other than a rubric band. Under this decision the
report would carry both senses at once. The disagreement display needs a different word —
*contested* — leaving **band** to mean only what `/CONTEXT.md` defines it as.

**The acceptance test is restated.** "Within 5 points per category" presupposes a
continuous per-category scale, which no longer exists. Per category it becomes **exact
band agreement between judges**, with one adjacent-band disagreement per resume as the
5–8 analogue — a pass that wants another look — and any non-adjacent disagreement, or
more than one adjacent, a failure. The map's 5 / 8 point statement survives as the
**composite-level** bar, which stays continuous. Per 08, a chance-corrected statistic is
reported beside the exact-match rate, since agreement on a band nearly every resume
lands in is not evidence of anything.

## What this hands downstream

- **04** — categories must be band-definable, and bands must be phrased as *evidence
  present*, not *defects found*. A band written as a defect list re-creates the double
  count this decision just closed.
- **05** — writes the bands for one category, and gets a concrete second experiment for
  free: same prompt, one field difference, band-only vs. band-plus-a-point-inside-it.
- **06** — unblocked. It measures band agreement per category, and finding agreement
  keyed on (defect kind, locator) rather than on wording. Both, not either: findings are
  still the report's substance even though they no longer move the number. 08 adds the
  shape of the report: between-judge spread, within-judge spread across reruns, and a
  chance-corrected statistic — three numbers, not one.
- **07** — its question is unchanged, but gains a constraint: whichever layer owns
  coverage, only one of them may move the number.

## What ticket 08 adds

08 closed while this was being argued, and it answers the half of the question the
arithmetic above could not. Its headline: **discrete levels are the precondition, and
0–100 is the worst case** — 0–5 gives the strongest human-LLM alignment of the scales
tested, judges latently quantize a fine scale into roughly 20 buckets whatever range
they are given, and human psychometrics puts peak reliability at 7–10 categories and
falling past that. Nobody recommends 100. Its own recommendation to this ticket was "a
coarse level, with the 0–100 number derived", which is this decision in different
vocabulary; `/CONTEXT.md`'s word for a coarse level is **band**, and that is the word
this map should keep.

Its caveat is carried here rather than dropped: every source was named from search
results and none could be opened, and two quantitative claims are marked **[verify]**.
That is survivable for this ticket, because the decision rests on the repo arithmetic
above and 08 corroborates it rather than carrying it.

Four things from 08 change what this ticket hands on:

- **The resolution objection has a second answer.** Coarse scales buy agreement with
  ties — one judge showed a 66.5% tie rate on similar candidates. Ties are fatal when
  ranking candidates against each other and harmless when gating one against a standard,
  and this tool gates. So the loss of resolution is not merely absorbed by the
  deterministic channel; it is not a cost in this application at all.
- **Forced evidence citation is not an agreement technique.** Its benefit diminishes
  once explicit criteria are present. That is a point *for* this decision from an
  unexpected direction: findings earn their place by making the band checkable, which is
  what `/CONTEXT.md` already demands of them — not by moving a number. Had they stayed a
  scoring channel, they would have been paying for agreement they do not buy.
- **The band count is now bounded.** Start at five and do not exceed seven. 04 may go
  further and decompose a category into binary criteria — 08 notes `Coverage` is
  naturally binary per skill — which is the same decision taken to its limit, not a
  departure from it.
- **Exact agreement can still be luck.** 08 shows the ±5 bar is passable by coincidence
  when every real resume lands between 60 and 80. The same argument applies to bands: if
  nearly every resume lands in the middle band, two judges agree by coincidence and the
  rubric has taught them nothing. So the restated band-agreement test above inherits the
  chance-corrected statistic 08 asks 06 to report; exact-match rate alone cannot
  distinguish a good rubric from a degenerate one.

## What would overturn this

Not 08 — it was the outstanding evidential risk when this was written, and it came back
confirming. What is left is 05.

If 05 cannot get two judges into the same band with the bands in front of them, the
problem is the band definitions, not this decision: findings-only stays ruled out by
arithmetic either way, and 08 rules out retreating to an unanchored 0–100. The genuine
open question is the runner-up, one field away — whether the model may pick a point
*inside* its band — and 05's second experiment already tests exactly that.

## Changed

- `docs/wayfinder/rubric-grounding/tickets/03-should-the-model-author-scores.md` — this
  ticket, answered and closed.
- `docs/wayfinder/rubric-grounding/MAP.md` — the decision recorded, the acceptance test
  restated in band terms, and the report's "banded" collision logged as unspecified.
