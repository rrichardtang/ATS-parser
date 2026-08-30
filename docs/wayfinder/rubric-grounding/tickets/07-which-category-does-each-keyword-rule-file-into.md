type: grilling (HITL)
status: closed
claimed: claude
blocked-by: 04

# Which category does each keyword rule file into?

## Question

The original question — does a `Coverage` category duplicate the deterministic keyword
rules — was answered by 04 dissolving `Coverage`. The ownership split is settled:
`ats/keywords.py` keeps tool coverage (nouns), the judged categories take behaviour
evidence (verbs), and they are genuinely different things because the corpus converges
on verbs and never above 4/6 on any noun.

What is not settled is the mapping. 04 retired all five judged categories, and every
rule that filed into them now has nowhere to go:

- `jd/missing-core` (was Credibility), `jd/missing-secondary`, `jd/missing-named-tools`,
  `kw/over-repetition`, `kw/skills-dump`, `kw/soft-skill-padding`,
  `kw/unsupported-skills` (were AI/ML relevance)
- `content/bullet-invariants`, `content/weak-opener`, `content/ownership`,
  `content/quantification` (were Impact)
- `cred/no-evaluation`, `cred/no-production`, `cred/notebook-only`,
  `cred/unlinked-projects`, `cred/no-named-models`, `contact/no-github` (were
  Credibility)
- `content/passive-voice`, `content/first-person`, `content/long-bullet`,
  `content/duplicate-bullet`, `scan/*` (were Writing quality / Recruiter scan)

This is spec, not implementation detail, because `rule_share` makes it load-bearing:
a rule's category decides which band's 40% it is half of, and a category with no rules
filed into it scores against a constant rather than a channel (04's Q11 finding).

Two things to settle, and the second is the one with teeth:

1. **The mapping itself.** Which of the five new categories each rule files into.
   Several are obvious (`cred/no-production` → Production ownership,
   `cred/no-evaluation` → Evaluation rigour). Several are not: `jd/missing-core` fires
   on a missing *term*, which is tool coverage, and no new category measures tool
   coverage — so where does it go, or does it stop deducting?
2. **Whether any rule duplicates a band criterion.** 03's constraint survives verbatim:
   whichever layer owns a property, only one of them may move the number. A rule that
   fires on the same evidence a criterion asks about is the double count 03 closed,
   reopened one layer down. `cred/no-production` and a Production ownership criterion
   reading "evidences a system reaching production" are the obvious collision to test
   first.

Note that 02 recorded a live defect here that is not 04's to fix and should not be
lost: `jd/missing-core` firing on "python" against a posting that said "Python, Go, or
TypeScript" is a false finding, because document frequency over terms cannot represent
a disjunction. Whatever category these rules land in, that stays wrong.

Done when: every deterministic rule has a named category under the new set, each
collision with a band criterion is either resolved or explicitly ruled not a
collision, and no category is left with zero rules except `AI-assisted coding fluency`,
which 04 set to `rule_share` 0 deliberately.

## Answer

**Every rule keeps its code-authored id and takes one of three dispositions — deducts
against a named new category, fires as advice and deducts nothing, or retired. Tool
coverage is the whole of the advice-only block. The full mapping, with the arithmetic,
is [rule-mapping.md](../rule-mapping.md).**

### The mapping, in one line each

- **Unchanged**: `parse/*`, `struct/*`, `contact/no-<field>`, `title/*` — their
  categories survived 04. `contact/no-github` rejoins its siblings in `Structure`; it
  was filed under Credibility only because a contact field read as credibility.
- **Production ownership**: `cred/no-production` (the C1 channel), `content/ownership`
  (the C5 channel).
- **Evaluation rigour**: `cred/no-evaluation`.
- **Resume craft**: all five `scan/*`, all three `slop/*`, `content/passive-voice`,
  `content/first-person`, `content/long-bullet`, `content/duplicate-bullet`,
  `content/weak-opener`, `kw/over-repetition`, `kw/skills-dump`,
  `kw/soft-skill-padding`, plus `content/bullet-invariants`, `content/quantification`
  and `cred/unlinked-projects` conditional on 12 authoring criteria whose evidence they
  answer.
- **Advice-only, deducts nothing**: `jd/missing-core`, `jd/missing-secondary`,
  `jd/missing-named-tools`, seven `kw/thin-<group>`, `kw/unsupported-skills`,
  `cred/notebook-only`.
- **Retired**: `cred/no-named-models`.

### Tool coverage stops deducting

Three reasons, in the order they bind: no new category measures nouns, so filing a
`jd/*` rule anywhere would deduct in a category whose criteria ask a different
question; 02's disjunction defect is structural, not a bug — df over terms cannot
express *"Python, Go, or TypeScript"*, so the false positive can never be fixed and a
structurally false signal must not move a number; and the advice is the value, which
survives without the deduction. That is 03's move — keep the reading, remove the number
— applied one layer down. `kw/unsupported-skills` joins them as the same object: a noun
claimed against the same noun matched literally elsewhere.

Mechanically an advice-only finding is emitted in full and excluded from the deduction
ledger. Findings are grouped for the report by **gate**, not category, so it needs a
gate and no category — `Gate.RECRUITER` for the tool-coverage block, where keyword
search happens. Same shape as 10's unmet criteria, which need no key at all.

### The collision test is within a channel, not across them

The blend is `rule_score * share + band_value * (1 - share)` — a convex combination.
Two channels reading the same evidence average; they do not sum. So a rule answering
the same question as a criterion is *the design*, and 05 measured that channel working
(53/55). What does collide is `deductions[category] += cost`, which is additive. Three
found, all resolved by *one property, one deducting rule*:

1. `cred/no-production` and `cred/notebook-only` both require
   `not PRODUCTION_RE.search(blob)` — they cannot fire apart, so one absence was
   charged MAJOR + MINOR, both scaled 1.5× by the same dimension. `notebook-only`
   becomes advice.
2. `content/quantification` and `content/bullet-invariants` are the same
   `measurability` predicate, per bullet and aggregated. Measurability deducts once, at
   document level.
3. `invariants.ownership` is literally `content/ownership`'s `TEAM_SUBJECT_RE`. Under
   this mapping they sit in different categories, which is worse than adding — one
   defect priced in two categories. Team attribution deducts once, in
   `Production ownership`.

`content/bullet-invariants` is a bundle of four predicates; two are separately priced
elsewhere, so the bundle keeps only `outcome` and `mechanism`, which is craft.

The forward constraint for 11 and 12: test *evidence*, not category. A craft criterion
about team attribution collides with `content/ownership`; one about naming things
collides with C2, which 05 already found is model-owned.

### `Agentic systems` must drop to `rule_share` 0

It has no rule and no dimension. `score.build` initialises `deductions` to zero for
every category, so a category nothing deducts from holds `rule_score = 100.0`
permanently: at 0.4 it can never score below 40, and 40% of it is pinned at full marks.
04 found the mechanism and called it latent — this is where it stops being latent. The
invariant, stated: **`rule_share` > 0 requires at least one deducting rule.**

That leaves `Production ownership` 0.4, `Evaluation rigour` 0.4, `Agentic systems` 0,
`AI-assisted coding fluency` 0, `Resume craft` 0.7 — three of five judged categories
model-owned, where 04 had one.

### The done-when it does not meet

Two categories are left with zero rules, not one. `AI-assisted coding fluency` was 04's
deliberate case; `Agentic systems` is not, and the honest answer is that no rule can be
written for it today rather than that it needs one. `rule_share` 0 is the safe state
until 09 supplies a dimension — which is now worth building for the channel, not only
for the weight.

### What would overturn this

`Resume craft` holds 19 of the 22 deducting content rules at `rule_share` 0.7, so the
rubric's whole deterministic mass sits on the one category the corpus did not produce
and that 05 predicts will not converge. That follows from where rules can be written —
craft is countable, behaviour is not — but if the composite turns out to be driven by
craft deductions, this mapping is where to look, and the fix is fewer craft rules
deducting rather than invented behaviour rules.

### Changed

- `docs/wayfinder/rubric-grounding/rule-mapping.md` — new: the mapping, the collisions
  and the arithmetic.
- `docs/wayfinder/rubric-grounding/tickets/07-which-category-does-each-keyword-rule-file-into.md`
  — this ticket, answered and closed.
- `docs/wayfinder/rubric-grounding/MAP.md` — the decisions recorded, the slop-pass and
  `RULE_DIMENSION` fog patches resolved, and the `rule_share` correction carried to 11.
