type: prototype (HITL)
status: open
claimed:
blocked-by: 06

# Score against the recorded baseline

## Question

This is the ticket the whole map exists to reach: the first time the new rubric scores
a real document, next to what the old one scored on the same document.

**Re-scoped after 06.** This ticket was written as *"Run both rubrics on the same
resume"* — both paths live, both results printed, the old one retired last. That is no
longer possible, and the reason is recorded below rather than worked around.

## What changed under it

The map's stated approach was *"the new rubric is added **beside** the old one, not in
place of it… Retiring the old path is the last ticket, not the first."* The implementing
tickets did not do that. 03 swapped `models.Category` in place, and 04, 05 and 06 built
on the swapped enum. Measured: the five retired categories — `RECRUITER_SCAN`, `IMPACT`,
`RELEVANCE`, `CREDIBILITY`, `WRITING` — appear **nowhere** in `ats/`, `scripts/` or
`app.py`. There is no old path left to run.

So the *before* picture is a **recording**, not a second live path:
[`baseline/run-summary.json`](../../rubric-grounding/baseline/run-summary.json) — 30
August, two providers, two samples each, eight documents (the seven fixtures plus the
owner's resume, renamed `private_resume_1`), redacted of quoted text by
`scripts/baseline_analysis.py --extract`.

This is a smaller claim than the original ticket made, and the difference matters: a
side-by-side of two live paths would have shown both rubrics reading *today's* parse of
each document. What is available instead compares today's new-rubric run against a
reading taken on 30 August, so any change in the parser or the deterministic rules since
then lands in the diff as if it were a rubric effect. Whoever works this must say which
of the two they are measuring.

## What has to be decided first

**The recording cannot be loaded by the code that would read it.** Both blockers are
measured, and neither is incidental:

1. `HarnessRun.from_dict` raises `ValidationError`: the redaction removed
   `Finding.message` and `Finding.fix`, which are required fields. The findings half of
   the baseline is therefore not reconstructable — only its rule ids and locators
   survive.
2. `Category("Impact & quantification")` raises `ValueError`. The enum lost those five
   members in 03, so even the scores half cannot be keyed without a decision about what
   to key it *as*.

Three ways out, and choosing between them is this ticket's first act:

- **Compare composites only**, recomputing the old composite from the recorded numbers
  and the old weights, and never constructing a `Category`. Cheapest; loses the
  per-category story the ticket was written to get.
- **Give the old category names a home** — a frozen table in the comparison script, not
  in `ats/` — so the recording keys against something without reviving a retired enum.
  Preserves per-category comparison; the cost is a second vocabulary living in the repo.
- **Re-run the old rubric from git history** at the commit before 03, against today's
  fixtures, and get a live *before* after all. Most faithful; most work, and it needs
  provider credentials for the old path too, doubling the call budget.

## What it still has to show

Unchanged from the original ticket, except that "old" now means "recorded":

- Composite and per-category, recorded and new, side by side.
- **What moved and why.** A resume that drops 20 points needs the criterion that
  answered `no` named beside it, or the comparison is two numbers and an argument.
- Which categories were withheld, and on what document. 06 makes this visible for the
  first time: three of the eight documents (`two_column`, `hidden_text`, `scanned`) parse
  to zero roles and now withhold all five judged categories.
- Which findings are advice-only now and cost nothing where they used to cost points.

## What to expect, so surprises are informative

Two predictions worth writing down before running, because a prediction that survives is
evidence and one that fails is a finding:

- **The old rubric's disagreement was mostly calibration.** openai scored above
  anthropic in 34 of 35 category-resume cells, mean +18.0, while ranking resumes almost
  identically (Spearman 0.75–0.96), and their written justifications for cells 19 points
  apart said the same thing in different words. A band lookup should delete that offset
  by construction — two judges who read a resume the same way now land in the same band
  whatever they would have called it out of 100. If the offset survives, the output form
  is not doing what 03 and 04 claimed.
- **Scores will move down, and unevenly.** Eleven rules stop deducting (04) while five
  categories that previously blended a generous model number now blend a band lookup
  with an explicit floor. 06 adds a third direction: the lower band wins on a split, and
  withheld categories leave the composite entirely. Which effect dominates is unknown;
  that it will be uneven across resumes is not.

## Credentials

Needs `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` for the new-rubric half — the recorded
half costs nothing. Neither key is set in the sessions that have worked this map; they
were present for the 30 August run, so they exist somewhere reachable. The dry run
(`python scripts/agreement_harness.py --dry-run`) prints the call budget without
spending it: **7 fixtures × 2 providers × 2 samples = up to 28 content calls**, less the
documents withheld or skipped before a call is spent.

Done when: one command prints the recorded and the new score side by side for all eight
documents; the differences are explained by criterion rather than asserted; and the
comparison says plainly which of its differences are rubric effects and which are eight
weeks of parser drift.
