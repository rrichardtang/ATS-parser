type: grilling (HITL)
status: closed
claimed: claude
blocked-by: 11

# Criteria for Resume craft, or an admission that it cannot have them

## Question

`Resume craft` is the fifth judged category and the one 05 singles out as the one to be
careful with:

> subtract what `ats/human.py` already checks deterministically and what remains is
> weighed, not countable, and criteria will not make it converge.

That is a prediction of failure from the ticket that invented the format, and it is why
this is split from [11](11-criteria-for-the-three-remaining-behaviour-categories.md)
rather than being its fourth item. The three behaviour categories should not wait on it,
and it should not be attempted with three sets' worth of momentum behind it.

It is a **grilling** ticket, not a prototype, because the first question is whether to
write criteria at all — not how to word them.

## Why it is different from the other four

- **It is not a behaviour.** The other four are things the corpus asks candidates to
  have done, counted by document frequency. `Resume craft` has no df to derive from; 04
  gave it an authored weight for that reason.
- **`rule_share` 0.7, the highest.** Most of its score already comes from the
  deterministic channel. So the criteria are being asked to carry the *smallest* share
  of score of any category — while being the hardest to write.
- **The baseline says it is the worst.** `Writing quality`, its predecessor, had the
  largest residual in the run: 10.1 mean, 20.3 max, and only 2 of 7 resumes inside the
  bar. On `two_column` all four samples agreed the bullets were telegraphic and landed
  on 50, 55, 57, 48. That is the shared-reading-different-number failure in its purest
  form, and it is the failure 04's output form was supposed to remove.
- **The overlap problem is real, not theoretical.** `ats/human.py` and the `scan/*` and
  `content/*` rules already check passive voice, first person, bullet length, duplicate
  bullets, weak openers and quantification rate. 07 is deciding where those file. What
  is left after subtracting them is the question this ticket has to answer, and 07
  should land first if it is going to.

## The three outcomes, and none of them is a bad result

1. **Criteria that converge.** 05's prediction was wrong, and the format is more general
   than its author thought. Requires the same artifacts 11 produces.
2. **Criteria that do not converge, measured.** The category keeps its deterministic
   channel and the model's 0.3 share is dropped or held at a fixed value. `rule_share`
   0.7 makes this survivable in a way it would not be for a behaviour category — the
   score mostly does not depend on the model here.
3. **No model channel at all.** `Resume craft` becomes deterministic, `rule_share` 1.0.
   Clean, and it costs the candidate the qualitative reading a resume's craft arguably
   needs most.

Outcome 3 is the one to hold in view, because 10 makes it sharper than it looks: with
the open-ended search gone, a `Resume craft` with no criteria is a category that says
nothing qualitative at all. If that is the answer, say so deliberately rather than
arriving at it by failing to word criteria well enough.

## Also here, because it cannot be settled without this

**Which gate `Resume craft` belongs to.** It merges `Recruiter scan` (`Gate.RECRUITER`)
with `Writing quality` (`Gate.MANAGER`) and must pick one. `report.py` groups findings
by gate and `score.py` derives the parser and human sub-scores from it, so this moves
visible output. 04 left it as a reporting question; it is tracked in the map's *Not yet
specified* and this is the ticket that has the context to close it.

Done when: either criteria with a measured verdict as 11 produces, or a recorded
decision that `Resume craft` has no model channel — with the measurement that supports
it, not the difficulty of writing them. The gate question answered either way.

## Answer

**Outcome 1: criteria that converge — 54/55, one adjacent band, LOOK. 05's prediction
was wrong, and the reason it gave was the wrong reason.**

- [resume-craft-criteria.md](../resume-craft-criteria.md) — the subtraction, the five
  criteria, the lookup, the rulings on 07's three conditional rules, and the gate.
- [resume-craft-agreement.md](../resume-craft-agreement.md) — the measurement.
- `criteria/resume-craft.json`, `criteria/probes/resume-craft/` (7),
  `criteria/judgments/resume-craft/model-claude.json`.

### The subtraction came first, because it decides whether there is anything to write

Every piece of evidence 04 named for this category — identity and evidence above the
fold, a summary, experience outranking optional sections, no unexplained pivot, bullets
active, third-person, non-duplicated, within length — is answered by one of the ~40
deterministic rules 07 files here. 05 is right about that part.

Three readings survive, all quotable, all recurring in the baseline: a bullet that names
a change rather than an assignment (18 findings), a resume that says what the work was
*for* (8 findings, **and nothing in the repository has ever checked it**), and roles that
read as different jobs below `content/duplicate-bullet`'s 0.8 threshold. That is enough
for criteria, so criteria were written.

### The finding: the lookup shape does not transfer, and that is the real difficulty

The other four categories are gated — C1 asks whether the subject exists at all and band
E means *absent*. **Craft is never absent**; every resume is written somehow. A gate here
would score a well-written document at 10 for a missing header line. So the band is the
**count of criteria met**, with no gate.

The consequence is the whole of the cost. Leverage is uniform — 30/32, one band, every
criterion — so there are no cheap seats: one split is one adjacent band, always, and two
splits anywhere is a **FAIL** where `Production ownership` spent two and still reached
LOOK. `Resume craft` must answer *more* criteria identically than a gated category to
reach the same verdict.

That is 05's prediction in quantitative form, and it is not 05's mechanism. The
difficulty is not that craft is weighed rather than pointable — nothing here had to be
weighed. It is that a category with no gate has nowhere cheap to disagree. Any future
category whose subject cannot be absent inherits both.

### The one split found something new

`2-two-of-five` holds two roles of *different* filler. The rule channel measures token
overlap, finds it low, and answers C4 "roles read differently" yes; the reader answers no,
because neither role reads as a job at all. **When C5 fails, C4 has no answer.** 04 and 08
both name separability as the agreement lever and both apply it *between categories*; this
is the first time it has bitten *within* a criteria set. Repair is one line and is
deliberately not applied, on 05's own precedent — a criterion patched against the judge
that found the problem measures nothing.

### 07's three conditional rules, ruled on

- `content/bullet-invariants` — **deducts**, narrowed to `outcome`, which C2 answers. Its
  `mechanism` failure joins the other two as advice, because 07's forward constraint
  forbids a craft criterion about naming (it would duplicate `Production ownership` C2).
  It now deducts on one predicate and is no longer a bundle: rename it in the migration.
- `content/quantification` — **advice-only**. No criterion here answers measurability, and
  authoring one would double-price across categories: a resume with no numbers already
  fails `Evaluation rigour` C2 and `Production ownership` C3. Cost stated: nothing deducts
  for an unquantified resume here any more, and the fix text survives as advice.
- `cred/unlinked-projects` — **advice-only**. No criterion answers it; verifiability is
  not a reading this category has.

### The gate question, which was half a false alarm

04 recorded that the `RECRUITER`/`MANAGER` choice moves visible output because
`score.py:161` derives the sub-scores from it. It does not: `_subscore(categories,
{Gate.RECRUITER, Gate.MANAGER}, weights)` takes a **set**, so moving a category between
those two changes neither sub-score. Only `PARSER` versus the rest is load-bearing.

What is left is report placement. **Answer: `Gate.RECRUITER`** — 04's definition leads
with the six-second scan, the five `scan/*` rules already carry
`Provenance.RECRUITER_EVIDENCE`, and 07 put the advice-only tool-coverage block there.
Provisional in one respect worth recording: 07's migration already requires findings to
carry their own gate, and once they do `CATEGORY_GATE[Resume craft]` is read by nothing.

### Changed

- `docs/wayfinder/rubric-grounding/resume-craft-criteria.md`,
  `resume-craft-agreement.md` — new.
- `docs/wayfinder/rubric-grounding/criteria/resume-craft.json`, 7 band probes, one
  judgment file.
- `scripts/criteria_probe.py` — four document-level deterministic kinds, each reusing the
  predicate of the rule that already answers it.
- `tests/test_criteria_probe.py` — shape-aware: the gate properties apply to gated
  categories, and two new properties pin the count shape.
- `docs/wayfinder/rubric-grounding/MAP.md` — the findings recorded, the gate question
  closed, the "criteria for the other four categories" item retired.
