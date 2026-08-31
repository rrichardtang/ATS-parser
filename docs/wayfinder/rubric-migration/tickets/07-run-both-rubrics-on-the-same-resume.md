type: prototype (HITL)
status: open
claimed:
blocked-by: 06

# Run both rubrics on the same resume

## Question

This is the ticket the whole map exists to reach: the first time the new rubric scores
a real document, next to the old one scoring the same document.

Not a replacement. Both paths run, both results print, and the comparison is the
output. The old rubric is not deleted until someone has looked at this on real resumes
and said it is better.

## What it has to show

- Composite and per-category, old and new, side by side.
- **What moved and why.** A resume that drops 20 points needs the criterion that
  answered `no` named beside it, or the comparison is two numbers and an argument.
- Which categories were withheld, and on what document.
- Which findings are advice-only now and cost nothing where they used to cost points.

The `before` picture already exists — [baseline-agreement.md](../../rubric-grounding/baseline-agreement.md),
run 30 August against the rubric still in the code, on the seven fixtures plus the
owner's resume. The same documents through both paths makes this directly comparable
rather than a fresh reading.

## What to expect, so surprises are informative

Two predictions worth writing down before running, because a prediction that survives is
evidence and one that fails is a finding:

- **The old rubric's disagreement was mostly calibration.** openai scored above
  anthropic in 34 of 35 category-resume cells, mean +18.0, while ranking resumes almost
  identically (Spearman 0.75–0.96), and their written justifications for cells 19 points
  apart said the same thing in different words. A band lookup should delete that
  offset by construction — two judges who read a resume the same way now land in the
  same band whatever they would have called it out of 100. If the offset survives, the
  output form is not doing what 03 and 04 claimed.
- **Scores will move down, and unevenly.** Eleven rules stop deducting (04) while five
  categories that previously blended a generous model number now blend a band lookup
  with an explicit floor. Which direction wins is unknown; that it will be uneven across
  resumes is not.

Needs provider credentials — `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`, neither set in
the session that opened this map.

Done when: one command scores a resume both ways and prints the comparison; the seven
fixtures and the owner's resume have been through it; and the differences are explained
by criterion rather than asserted.
