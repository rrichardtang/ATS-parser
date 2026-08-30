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
