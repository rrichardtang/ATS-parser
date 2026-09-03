# Resume craft: the criteria, the lookup that is not a ladder, and the three rules it rules on

Ticket: [12](tickets/12-criteria-for-resume-craft.md). Category defined by
[04](tickets/04-design-the-category-set.md); format proved by
[05](tickets/05-draft-bands-for-one-category.md) and generalised by
[11](tickets/11-criteria-for-the-three-remaining-behaviour-categories.md). Rules filed
here by [07](tickets/07-which-category-does-each-keyword-rule-file-into.md).
Machine-readable in [ats/criteria/resume-craft.json](../../../ats/criteria/resume-craft.json).

> **Resume craft** — whether the document survives a six-second recruiter scan and
> reads as edited prose. No document frequency, authored weight, `rule_share` 0.7.

05 predicted this category would not converge: *subtract what `ats/human.py` already
checks deterministically and what remains is weighed, not countable.* The subtraction
was done first, because it decides whether there is anything to write.

## The subtraction

07 files about forty deterministic rules here — more than the other four judged
categories hold between them. What they cover:

| what a reader notices | rules that already answer it |
|---|---|
| identity and evidence in the first third of page one | `scan/no-identity-above-fold`, `scan/no-evidence-above-fold` |
| a summary, and Experience ahead of optional sections | `scan/no-summary`, `scan/experience-outranked` |
| a career arc with no unexplained pivot | `scan/unexplained-pivot` |
| passive voice, first person, over-long bullets, weak openers | `content/passive-voice`, `content/first-person`, `content/long-bullet`, `content/weak-opener` |
| near-duplicate bullets | `content/duplicate-bullet` |
| AI slop — banned words, empty phrases, metadiscourse, faux insight, and ~14 more | `slop/*` patterns |
| a sentence that would fit any candidate | `slop/portable` |
| sentence-length monotony, synonym cycling | `slop/robotic-rhythm`, `slop/synonym-cycling` |
| keyword stuffing, skills dumps, soft-skill padding | `kw/over-repetition`, `kw/skills-dump`, `kw/soft-skill-padding` |

**Every piece of evidence 04 named for this category is in that table.** *Identity and
evidence above the fold; a summary; experience outranking other sections; no unexplained
pivot; bullets active, third-person, non-duplicated, within length* — all deterministic,
all already shipped. 05's prediction is right about the part of the category 04 wrote
down.

What is left, once those are subtracted, is three readings — and they came from the
baseline, not from introspection:

- **Whether a bullet names a change or an assignment.** `invariants.evaluate(...).outcome`
  answers it from a closed verb list. 07 §3 priced the bundle's three other predicates
  in other categories and left `outcome` here, saying *"what is left to it is craft"*.
  13 baseline findings under `activity-not-outcome` plus 5 more asking for a user or
  business outcome.
- **Whether the resume says what any of the work was for.** About 8 baseline findings
  across `missing-context`, `missing-role-context`, `missing-employment-context`,
  `limited-product-context`, `unclear-project-context`. **Nothing in the repository
  checks this**, in any category.
- **Whether two roles read as two jobs.** `content/duplicate-bullet` catches bullet
  pairs above 0.8 token overlap; a reader catches the same job told twice well below
  that. `undifferentiated-experience`, `duplicate-role-content`, `generic-positioning`.

Three readings, all quotable. That is enough for criteria, so criteria were written —
and two of the five below are the deterministic layer re-asked at a reading's
resolution, which `rule_share` 0.7 makes legitimate: cross-channel overlap is a convex
combination, not a second charge (07 §3).

## What the judge answers

### C1 — Says what it is
**Does the resume say what this person is, above the first role, rather than leaving the
reader to infer it from a job title?**

*Yes* needs a quote above the first role naming the discipline — a summary line or a
role line.
*No* looks like: a name, an email, and straight into a job.

### C2 — Names what changed
**Does every role have at least one bullet naming something that is different because of
the work?**

*Yes* needs one quote per role stating a change. Not the assignment, the difference.
*No* looks like: a role whose bullets are all responsibilities — "Responsible for
maintaining the pipeline", "Worked on model architectures".

### C3 — Says what it was for
**Does the resume say what the work was for — a product, a user, a problem — rather than
only the stack and the number?**

*Yes* needs a quote naming the thing the work served.
*No* looks like: "Cut p99 latency 380ms to 95ms with vLLM" — for what, and who noticed?

Separable from `Production ownership` C1 in both directions, which is the test 04 sets:
a resume can ship to production and never say what the product does, and can say what
the work was for without anything reaching production.

### C4 — Roles read differently
**Does each role read as a different job, rather than the same work described again?**

*Yes* needs the roles to differ in what they claim. One role is enough to satisfy it.
*No* looks like: two roles whose bullets are interchangeable, or a promotion where only
the title changed.

### C5 — Could not be anyone's
**Is every bullet specific enough that it could not move unchanged to a stranger's
resume?**

*No* looks like: "Leveraged cutting-edge AI technologies to deliver robust and scalable
solutions" — true of anyone who has ever been employed.

## The lookup is a count, not a ladder

This is the structural finding, and it is about the format rather than the category.

The other four categories are gated: C1 asks whether the category's subject exists at
all, band E means *absent*, and a criterion's cost is its position in the lookup. That
shape rests on the subject being able to be absent. **Craft is never absent.** Every
resume is written somehow, so a gate would mean scoring a well-written document at 10
for a missing header line — and the E band would be reachable only by a defect that has
nothing to do with the other four criteria.

So the band is the number of criteria met:

| band | name | rule | value | reads as |
|---|---|---|---|---|
| **E** | Not written for a reader | at most one met | 10 | Nothing about the document is aimed at the person reading it. |
| **D** | Needs a rewrite | exactly two | 35 | Two of the five hold. The rest is a draft. |
| **C** | Readable, unedited | exactly three | 58 | A reader can follow it and will notice what was left in. |
| **B** | One thing left | exactly four | 78 | Edited, with one criterion unmet — and the report can name which. |
| **A** | Edited | all five | 95 | It says what it is, what changed, what it was for, that the jobs differed, and none of it could be anyone else's. |

Counts 0 and 1 share the bottom band: at that end the difference between nothing and one
thing is not worth a band, while at the top four against five is exactly the difference
a reader notices.

Total and monotone, like the others. Two further properties are under test, and they are
this shape's alone: `test_a_counted_category_has_no_gate_and_no_cheap_seats` and
`test_a_counted_band_is_the_number_of_criteria_met`.

## Leverage: uniform, which is the whole of the cost

| criterion | flips the band | widest move |
|---|---|---|
| C1 says what it is | 30/32 | 1 band |
| C2 names what changed | 30/32 | 1 band |
| C3 says what it was for | 30/32 | 1 band |
| C4 roles read differently | 30/32 | 1 band |
| C5 could not be anyone's | 30/32 | 1 band |

05's design consequence was *spend the wording budget on the gate criterion*. There is
no gate here, so there is no budget to concentrate — **and nowhere cheap to disagree**.
In `Production ownership` two judges may split on C5 all day and cost one adjacent band;
here a split on any criterion costs one adjacent band, and two splits anywhere is a
failure.

So this category has to answer *more* criteria identically than a gated one to reach the
same verdict. That is the precise, quantitative form of 05's prediction — and it is not
the reason 05 gave. The difficulty is not that craft criteria are harder to answer. It is
that a category with no gate has no cheap seats.

## The three conditional rules, ruled on

07 filed three rules here *"conditional on 12"*, which must either be answered by a
criterion or sent to advice-only.

- **`content/bullet-invariants` → keeps deducting, narrowed to one predicate.** C2
  answers its `outcome` failure. Its `measurability`, `ownership` and now `mechanism`
  failures are advice: the first two by 07 §3, and mechanism because no criterion here
  asks about naming — 07's own forward constraint forbids one, since a craft criterion
  about naming things would duplicate `Production ownership` C2. What deducts is one
  predicate, so the rule is no longer a bundle and the migration should rename it.
- **`content/quantification` → advice-only.** No criterion here answers measurability,
  and authoring one would collide across categories rather than within: a resume with no
  numbers already fails `Evaluation rigour` C2 (a named metric and a number) and
  `Production ownership` C3 (a fact that could only be true after the system ran).
  Charging it a third time in `Resume craft` is exactly the double-pricing 07's collision
  test forbids. **The cost, stated:** nothing deducts for an unquantified resume in this
  category any more, and the fix text — *"get to 50%: latency, throughput, accuracy,
  dataset size, cost"* — survives as advice, which is 03's move applied one layer down.
- **`cred/unlinked-projects` → advice-only.** No criterion answers it; an unlinked
  project is a verifiability reading and this category has none. MINOR, projects section
  only, and the fix text is the whole of its value.

## The gate question, which turns out to be smaller than 04 thought

04 left it open: `Resume craft` merges `Recruiter scan` (`Gate.RECRUITER`) with `Writing
quality` (`Gate.MANAGER`) and must pick one, and 04 recorded that this *"moves visible
output"* because `report.py` groups by gate and `score.py:161` derives the sub-scores
from it.

Half of that is not true. `score.py:161` reads

```python
human_sub = _subscore(categories, {Gate.RECRUITER, Gate.MANAGER}, weights)
```

— a **set**. `_subscore` partitions categories into that set or out of it, so moving a
category between `RECRUITER` and `MANAGER` changes neither the parser sub-score nor the
human one. Only `PARSER` versus the rest moves a number, and `Resume craft` is in neither
running.

What is left is display: `report.by_gate` decides which of the three report sections a
finding is printed under. **Answer: `Gate.RECRUITER`** — 04's definition leads with the
six-second scan, all five `scan/*` rules already carry `Provenance.RECRUITER_EVIDENCE`,
and 07 put the advice-only tool-coverage block there too, *"where keyword search actually
happens"*.

And it is provisional in a way worth recording: 07's migration list already requires
findings to carry their own gate, because an advice-only finding needs a gate and has no
category. Once they do, `CATEGORY_GATE[Resume craft]` is read by nothing — the `scan/*`
findings can print under the recruiter and the `slop/*` findings under the manager, which
is where each belongs. The category-level answer above is what to use until then.

## Open

- **C4 and C5 are not independent, and the measurement found it.** On the probe written
  to hold two roles of different filler, the deterministic judge measures low token
  overlap and answers C4 *yes*; the reader answers *no*, because neither role reads as a
  job at all, so nothing distinguishes them. When C5 fails, C4 has no answer. The repair
  is one line — make C4 conditional on C5 — and it is **not applied here**, on 05's own
  precedent for its C5 wording: patching a criterion against the judge that found the
  problem is how a LOOK stops meaning anything. It needs the second judge 06 supplies.
- **C3 is the criterion with no rule channel and the most brittle one available.** Its
  alias family is a list of domain nouns — support, tickets, fraud, checkout — over an
  unbounded space of things software is for. It is `cred/no-named-models`'s shape, and
  `rule_share` 0.7 means it is also the criterion the rule channel most needs and least
  can supply.
