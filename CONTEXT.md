# ATS-parser

Scores a resume against the kinds of AI-engineering roles its owner is actually
applying to, and explains every point it deducted.

## Language

### Scoring

**Rubric**:
The scheme the content pass scores against: the categories, and what each score band
means in evidence terms.
_Avoid_: rules, criteria, scoring logic (those are the deterministic layer)

**Category**:
One axis of the rubric, carrying a weight and a 0–100 score.
_Avoid_: dimension, subgrade, axis

**Band**:
A stated range within a category, defined by the evidence a resume must show to land
in it. Never named by a judge: it is a lookup from the criteria the judge answered.
What makes a score reproducible between judges rather than a matter of taste.
_Avoid_: level, tier, threshold

**Criterion**:
One binary evidence question within a category, answered by a judge with the quote
that settles it. The unit a judge answers: bands and scores are computed from criteria,
never chosen by the judge. Findings remain the judge's other output.
_Avoid_: check, sub-score, rule (a rule is deterministic and produces findings)

**Corpus-derived weight**:
A category weight computed from how many postings state the behaviour that category
measures. Derived, never authored, like the digest — add a posting and it moves with
nobody editing anything. Distinct from an **authored weight**, a judgment call someone
can disagree with, which is all a category outside the corpus can have.

**Composite**:
The single headline score, derived from the weighted categories and every deduction.
_Avoid_: total, overall score, grade (the grade is the letter derived from it)

**Coverage**:
Whether the resume evidences the skills the target postings require, measured by the
deterministic keyword rules. Distinct from whether it evidences them *well*. Not a
scored category: the corpus converges on behaviours rather than named tools, so
behaviour evidence belongs to the categories and tool coverage stays here.

### Findings

**Finding**:
One evidenced defect in one place in the resume, carrying the quote it is based on.
A finding without a quote is not checkable and is discarded.
_Avoid_: issue, error, problem, flag

**Rule id**:
Names the *kind* of defect a finding is an instance of. What the report groups by and
the ledger totals by, so it must describe the kind, never one occurrence.

**Advice-only finding**:
A finding that fires, prints its message and fix, and deducts nothing. It is evidence
for no band, so it carries **no category** — a category is where a cost goes and this
has no cost — and it carries its own **gate** instead, which is how it still gets
printed. Tool coverage is the whole of it plus three collision losers.
_Avoid_: warning, soft finding, informational (they suggest a lesser defect; the defect
is as real as any other, it is the *price* that is zero)

**Deterministic rule**:
A finding produced by regex or structural analysis, with no model involved.
_Avoid_: static check, heuristic (heuristic is a provenance value, not a synonym)

**Ledger**:
The line-by-line derivation from 100 down to the composite. Every row is a real
movement of the score.

### The corpus

**Posting**:
One verbatim job description the owner chose, stored whole and never edited at rest.
_Avoid_: JD, job ad, listing, req

**Personal corpus**:
The postings the owner actually targets (`corpus/jds/user/`). Grounds their own runs.
Distinct from the **generic corpus** shipped with the tool, which grounds nobody's.

**Digest**:
The distillation of the personal corpus that reaches a prompt: which skills recur,
how often, and which qualities the postings emphasise. Derived, never authored.

**Dimension**:
A quality a posting emphasises — ownership, production evidence, evaluation rigor,
seniority, leadership. Measured by how many postings mention it.
_Avoid_: category (a category is a scoring axis; a dimension is a corpus property)

### Judging

**Judge**:
One model scoring one resume. Two judges scoring the same resume should agree; how
closely they do is the test of whether the rubric is any good.
_Avoid_: provider (a provider is an API; a judge is a role), model, grader

**Inter-judge agreement**:
The spread between two judges on the same category and resume. The rubric's
acceptance test, not a diagnostic about the resume.
_Avoid_: disagreement, variance, band (the report's word "banded" means something else)
