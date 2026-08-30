type: grilling (HITL)
status: closed
claimed: claude
blocked-by: —

# What makes two findings the same finding?

## Question

The baseline run measured findings agreement between two judges at **0.03**. Re-keyed
on the locator alone it is **0.51**, and on the quoted evidence span **0.36** — the same
findings, the same run, a 17× swing decided entirely by what "the same finding" means.
See [../baseline-agreement.md](../baseline-agreement.md).

The cause is that both halves of today's key are text the model invents. Across 198
findings the two providers produced **108 distinct `rule_id`s**, sharing **5**.
`missing-evaluation-methodology`, `-detail`, `-context`, `-method` and
`missing-eval-methodology` are five spellings of one defect, 33 findings between them.
`prompts.CONTENT_SYSTEM` already asks for a name "reused verbatim across every finding
of that kind"; asking harder is not a fix, because the model has no list to reuse *from*.

This is not only a measurement problem. `/CONTEXT.md` defines a rule id as naming the
*kind* of defect, and `Report.grouped` and the ledger both total by it. At 108 names for
198 findings, one defect renders as five cards in the report a candidate reads.

Three things to settle, and the third is the one with teeth:

1. **The key.** What identifies a finding for agreement measurement — locator, evidence
   span, or a pair. The harness reports one number today and it is the least informative
   of the three.
2. **The vocabulary.** A closed list the model chooses from, rather than a name it
   invents. What is on the list, and what happens to a defect that does not fit one.
3. **Whether the model needs a findings vocabulary at all.** 04 already gives it a
   closed vocabulary — the criteria. A finding could be *the evidence for a criterion
   answered `no`*, in which case the criterion id is the rule id, the list is fixed by
   construction, and this ticket collapses into 04. The cost is that a defect no
   criterion asks about becomes unreportable, and the slop pass and the deterministic
   rules both emit findings that no criterion covers. Settle whether the model's
   findings are criterion evidence, a separate channel with its own list, or both.

Note the constraint 03 leaves standing: model findings are evidence for the band and
the fix list, and no longer deduct. So this decides what the candidate reads, not what
the score is — which lowers the stakes on getting the list exhaustive and raises them on
getting it legible.

Also recorded, because it bears on 1 and is easy to miss: within-judge locator overlap
(0.57) barely beats between-judge (0.51). Finding localisation is unstable inside a
single judge, so ensembling two providers does not fix it and a stable key will not
either.

Done when: the key is chosen and `ats/agreement.py` reports it, the vocabulary question
is answered one of the three ways above, and whichever answer is taken is stated
precisely enough that `prompts.py` could be changed without a second decision.

## Answer

Spec: [../findings-identity.md](../findings-identity.md).

**A finding is the evidence for one criterion, and its `rule_id` is the criterion id.**
Question 3 collapses into 04 for the *vocabulary* and does not collapse for the *object*:
the model gets no findings list of its own, but a criterion answered `no` yields two
different things depending on whether the defect has text to point at.

### 1. The key — `(rule_id, locator)`, and locator alone was a trap

Kept, per 03; what changes is that both halves stop being free text. The locator
alternative is rejected on a measurement the ticket did not have. A resume has 5–9
bullets plus the summary — I regenerated the fixtures and parsed them to count — and
each judge flags 4–11 of them. Two judges marking most of a short list overlap heavily
for no reason at all:

| key | between | chance | kappa |
|---|---|---|---|
| `(rule_id, locator)` | 0.03 | 0.34 | **−0.48** |
| `locator` alone | 0.51 | 0.58 | **−0.16** |

Locator agreement is *below* random flagging, on 6 of 7 resumes. Against the true
parsed-bullet universe rather than the observed union it is milder and mixed (−0.21 to
+0.24), so the defensible claim is *at or below chance* either way — but "the judges
agree on about half the places", which is how the baseline first read this, is not
true. The 17× swing is real and it is a bad key against a key that looks good because
its pool is small.

`ats/agreement.py` now reports all three keys per resume with `chance` and `kappa`
beside each `between`, and `scripts/baseline_analysis.py` prints the same two columns.
That is 08's chance-correction requirement reaching the findings table, which is where
it was most needed.

### 2. The vocabulary — the criteria, and nothing else

~25 ids of the form `<category>/C<n>`, fixed by construction. The 108 invented names
become a design-time input rather than a runtime output: the terms both judges reached
for unprompted are evidence for wording the criteria 04 has not written yet.

### 3. The object — split on quotability

`/CONTEXT.md` requires a quote; 05 makes a quoteless criterion a `no`. Those meet on
pure absences — nothing anywhere says the work reached production, so there is nothing
to quote and nowhere to point. That defect is real, it is the most important thing the
candidate could be told, and it is not a Finding.

- **Unmet criterion** — the absence. No locator, no quote, one per criterion per resume.
  What the band reads and what the report leads with.
- **Placed finding** — present-but-weak, where the resume does say something and what it
  says is the problem. Quote and locator required, `rule_id` = criterion id. C5's
  *"We shipped the ranking service"* is the clean case.

Agreement measurement follows: unmet criteria are compared as a set of criterion ids and
need no key at all, so only placed findings go through `(rule_id, locator)`.

### 4. Locators are resolved, not trusted

**10% of the baseline's locators name nothing in the parsed resume** — `interests.bullet[0]`,
`exp[0]`, `skills`, and one compound `exp[0].bullet[0] / exp[1].bullet[0]` that breaks
"one defect in one place" outright (anthropic 16%, openai 6%). `passes.py` already
resolves locators against real bullet text for the rewrite pass; that resolution moves
earlier and applies to all of them. A placed finding whose locator does not resolve is
demoted to an unmet criterion — the reading survives, the fictional address does not.

## What this costs

A content defect no criterion asks about becomes unreportable. Bounded by 03 (findings
no longer deduct, so it costs advice and not points), by slop and the deterministic
rules still covering writing and structure, and by the criteria being authored — a
defect the judges keep reaching for is an argument for a criterion.

## What would overturn this

**The criteria set is now load-bearing for report quality, not just for the score.** 04
chose categories on separability and document frequency; nothing asked them to be
exhaustive over defects, and this decision now asks exactly that. If the remaining four
categories' criteria cannot hold what the judges actually say — the baseline shows them
converging on *evaluation methodology*, *deployment reach*, *scale/latency/cost* — the
report gets thinner as it gets more consistent, and the answer to reach for is a
separate closed findings list after all (option B), not a return to invented names.

The second risk is smaller and measurable: the split in §3 assumes absence-defects and
weak-text-defects are cleanly separable per criterion. If judges disagree about *which
of the two* a given `no` is, the unmet-criterion set and the placed-finding set both
get noisy and the key problem comes back one level up. The harness can see this the
first time criteria run through it.

## Changed

- `docs/wayfinder/rubric-grounding/findings-identity.md` — the spec, new.
- `ats/agreement.py` — findings agreement reported under all three keys, each with a
  chance line and a kappa; `FindingsRow` gains `key`, `chance`, `kappa`.
- `ats/agreement_table.py` — the findings table renders them, and says to read kappa.
- `scripts/baseline_analysis.py` — `chance` and `kappa` columns on the key table.
- `docs/wayfinder/rubric-grounding/baseline-agreement.md` — "the judges agree on about
  half the places" corrected; the key table carries its chance line; the unresolvable
  locator rate recorded.
- `tests/test_agreement.py`, `tests/test_baseline_analysis.py` — the key of record and
  the chance line under test.
- `docs/wayfinder/rubric-grounding/MAP.md` — the decision recorded.
- This ticket, answered and closed.
