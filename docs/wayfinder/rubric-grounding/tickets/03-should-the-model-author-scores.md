type: grilling (HITL)
status: open
claimed:
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

## Prep

[`../scoring-mechanics.md`](../scoring-mechanics.md) — what the model authors today,
what the observed spreads actually cost, and the options with their costs. Gathered
for this grilling; it does not decide the fork.

Three things it establishes that change the question:

- **The model authors 40.5 of the composite's 100 points**, across five of eight
  categories. Three categories worth 25 points already score with no model at all, so
  the alternative has a working precedent in the codebase.
- **The model's number is never used raw.** `score.py` blends it against the rule
  score at 0.4 (or 0.7 on Recruiter scan), so the worst observed spread — 22 — moves
  the composite by **2.9 points**. The disagreement is nearly invisible in the
  headline number and fully visible in the per-category scores, which the report
  displays.
- **The acceptance test is underdetermined.** ±5 on *which* number, raw or blended?
  They differ by 1.7–3.3×, and a raw spread of 16 fails on one and passes on the
  other. Ticket 06 is blocked on this.

Tickets 02 and 08 both landed since this ticket was written, and point the same way:
the corpus's real signal is binary per behaviour (02), and discrete levels are what
judges actually agree on (08). That suggests a third option beyond this ticket's two —
the model authors a coarse level and the 0–100 number is derived.
