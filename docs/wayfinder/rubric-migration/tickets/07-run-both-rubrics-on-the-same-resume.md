type: prototype (HITL)
status: open
claimed: claude
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

## Answered, except for the half that needs credentials

`scripts/side_by_side.py` scores one document under both rubrics and prints what moved
and why. The write-up, the tables and the findings are in
[both-rubrics.md](../both-rubrics.md).

**The old column is the old code, not a model of it.** 03 replaced `models.Category`
outright, so nothing old survives in the package to run beside the new path. The script
materialises the tree from git at **`1418f0a`** — the commit that recorded
baseline-agreement.md — and runs it in a subprocess. The pin is load-bearing: 02 looks
like a documentation ticket but removed four `RULE_DIMENSION` entries, so a commit later
would have moved the *before* picture without saying so.

Three judge channels: **recorded** (the baseline's two providers against the recorded
`model-claude` criterion answers, on the seven fixtures), **rules-only** (any document),
and **live** (each side calls its own content pass). The live path is written and has
**never run** — no session on this map has had credentials — and that is what is left of
this ticket, along with the owner's resume, which is not in this environment.

## What it found

**The fixtures move as 02 predicted, and one moves the other way.** Four fall 7 to 16
points, and the fall is the constant 02 identified: `Agentic systems` and `AI-assisted
coding fluency` are band E on every criterion of every fixture, against 20 points of
tool-coverage deductions coming back as advice. `hidden_text` does not move at all — the
fraud cap pins it at 40 on both sides. **`two_column` rises 9.6**, because its roles do
not parse, all five judged categories are withheld (05), and the composite renormalises
over what was checked (06) — where the old rubric judged the visible text anyway and
scored it in the 60s. Its **human gate prints 100.0 off `Title & seniority alignment`
alone**, which is 06's open item observed on a document rather than predicted. (Since
fixed on `main`, 5657d91: that gate now reports no score and prints `n/a`.)

**`Resume craft`'s rule channel is a constant 0 on realistic documents.** Over 08's
thirty drawn resumes its deterministic deductions run 120 to 436 (median 242) against a
category that floors at 0, so it is floored on **30 of 30**. With `rule_share` 0.7 that
caps the category at **28.5** whatever a judge answers — on the heaviest authored weight
in the rubric. It discriminates on the fixtures only because they are too short to
accumulate 100 points of cost. This is inherited rather than caused — the old rubric
floored `Impact & quantification` on 28 of 30 with the same blend — but the migration
concentrated the mass into one category and made it the heaviest one. It is also the
second finding on this map that the rubric is calibrated on short documents; 08 found
the other, by a different mechanism, in the same category. Both go back to the other map.

**The deterministic layer alone is close to a wash**: 19 down, 11 up, mean -2.4, range
-21.3 to +7.3 over the thirty documents, with advice-only rules returning a mean of 36.3
points each. So the ticket's second prediction — *scores will move down, and unevenly* —
is right about unevenness and wrong about direction: direction is a property of whether
the document has evidence in the four behaviour categories, not of the migration. The
first prediction, that a band lookup deletes the old rubric's calibration offset, is
**not tested**: the new side has one recorded judge, so there is no second reading to
disagree with it. That is 09's, and this comparison cannot stand in for it.

## Changed

- `scripts/side_by_side.py`, `tests/test_side_by_side.py` — the comparison and its
  seven tests.
- `docs/wayfinder/rubric-migration/both-rubrics.md` — the tables, the findings and the
  two predictions.
- `MAP.md` — one decision, two open questions.

## The first live run: the owner's resume (25 September)

The owner ran `--doc` on their own resume on their own machine, with both keys set. The
live path worked end to end on its first run. Only numbers and ids are recorded here; the
resume and its quoted text stay off the repo.

| | old | new | moved |
|---|---|---|---|
| composite | 64.7 (D) | 59.3 (F) | -5.4 |
| parser gate | 92.5 | 91.5 | -1.0 |
| human gate | 57.7 | 51.2 | -6.5 |

- **The fall is mostly the `Resume craft` floor, on a real document now.** The judges put
  the category in band C (58), with no unmet criterion. It scores **17.4**, which is
  0.3 × 58 + 0.7 × 0: the rule channel is floored, as on 30 of 08's 30 documents.
  At weight 25 that floor costs about 10 composite points, more than the 5.4 the resume
  fell, so the D to F is this open item and not a judgement about the resume.
- **The two providers split on 2 of 5 judged categories, one criterion each, one band
  apart.** `Agentic systems` split on C3 (C or B, scored C) and `Production ownership`
  on C3 (D or C, scored D). They agreed on the other three. This is the first reading
  of two live judges under the band lookup. It is one document, so it is an input to
  09 and not a tolerance verdict.
- **Two script fixes, found by the run.** The channel label still said *never yet run*,
  and a rule id of 34 characters ran into the next column. Both fixed.

## What is left

1. Run the live path on the seven fixtures. Then this ticket closes.
2. 09 is unblocked for everything that does not need 07's live run, since its inputs are
   08's set and the harness rather than this comparison.
