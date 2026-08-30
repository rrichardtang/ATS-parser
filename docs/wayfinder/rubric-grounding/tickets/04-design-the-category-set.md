type: grilling (HITL)
status: closed
claimed: claude
blocked-by: 02, 03

# Design the category set

## Question

What are the categories, derived from the corpus inventory (02) and shaped by the
output-form decision (03)?

Constraints already agreed: every category must be scoreable from observable evidence
in the resume; the current five are replaced rather than evolved; expect four to six.
`Coverage` — does the resume evidence the skills these postings require — is the one
axis nothing today measures, and is the most direct reading of "grounded in what the
job descriptions want".

Done when: the set is named, each category has a one-line definition of what it
measures, and each names the evidence a judge would point at.

## Answer

**Five judged categories, four of them corpus-derived behaviours plus one artifact
axis. The judge answers binary criteria with a quote; the band is a lookup from the
criteria, and the weight is a lookup from the corpus.**

Nothing the model emits is a number the model chose — 03 removed the score, this
removes the band label too.

### The set

Eight categories total, unchanged in count. Three carry over untouched (`Parseability`
15, `Structure & formatting` 5, `Title & seniority alignment` 5): they are
deterministic, no band, and no posting has an opinion about them. The five judged ones
are new.

| # | category | measures | evidence a judge points at | df | `rule_share` |
|---|---|---|---|---|---|
| 1 | **Production ownership** | Whether the resume evidences taking a system to production and staying responsible for it after launch | A shipped system with a destination (users, production, customers) **and** post-launch responsibility: operating it, on-call, incident response, reliability work, iteration after release | 6/6 | 0.4 |
| 2 | **Agentic systems** | Whether the resume evidences *building* systems that reason over context, call tools and take actions | A named system the candidate built, with its mechanism: which tools it could call, what decided the next step, what guardrails bounded it | 6/6 | 0.4 |
| 3 | **Evaluation rigour** | Whether the resume evidences measuring model quality with something that could have returned a negative answer | A named eval — metric, dataset, and a number — or a regression suite, A/B test, or human annotation process. fluidstack sets the bar: *"evaluation harnesses that told you the truth about model quality before users did"* | 5/6 | 0.4 |
| 4 | **AI-assisted coding fluency** | Whether the resume evidences working fluently with AI coding tools as a *practice* | Bullets naming the tooling **and** what it changed about the work — throughput, review practice, what the candidate now does differently | 3/6 | **0** |
| 5 | **Resume craft** | Whether the document survives a six-second recruiter scan and reads as edited prose | Identity and evidence above the fold; a summary; experience outranking other sections; no unexplained pivot; bullets active, third-person, non-duplicated, within length | — | 0.7 |

Categories 1–4 are the corpus's behaviours. Category 5 merges today's `Recruiter scan`
and `Writing quality` — it is not corpus-derived and cannot be, since the postings
describe the job, not the resume.

Retired: `Impact & quantification`, `AI/ML relevance & depth`, `Credibility &
verifiability`, `Recruiter scan`, `Writing quality`. Where their deterministic rules
now file is ticket 07, restated.

### Why these, and why not the others

**Separability decides what exists; document frequency decides what it is worth.**
Two categories evidenced by the same sentence are not two categories — 08 names
separability as the agreement lever, and this is the test applied throughout.

- **Production, ownership and reliability merge.** fluidstack's *"shipped ML or LLM
  features to production and owned them after launch"* evidences all three in one
  clause, and `jd_dimensions.py` already groups reliability under production
  (`r"\breliability\b"` is a production pattern). One axis.
- **Evaluation stays separate.** Separable in both directions: you can ship without
  evals, and build evals for something unshipped.
- **Agentic stays separate** from production for the same reason, and it splits three
  ways in the corpus (building agents / advising on them / using agentic coding tools).
  Under criteria-only decomposition it is no longer scored as one thing, so 02's
  conflation warning is answered by the format rather than by more categories.
- **AI-assisted coding fluency earns its own category at 3/6.** An earlier draft of
  this answer folded it into `Agentic systems` on the grounds that 3/6 is too weak to
  carry a category. That was the wrong test: df is the weighting mechanism, not an
  existence gate. It separates from category 2 in both directions — ramp's ideal
  candidate is excellent with agentic tooling and may never have shipped an agent;
  anyone who shipped an agent in 2023 did it without such tooling. Separable, so it
  exists; 3/6, so it is worth little.
- **Cross-functional collaboration is 6/6 and still excluded** — on soundness, not on
  count. `ats/jd_dimensions.py` carries the standing objection: *"its natural phrasing
  ('partnered with product and design') is close enough to the ownership-dilution
  pattern ('the team shipped X') that wiring it in without resolving that collision
  would reward and penalise the same sentence shape at once."* Unresolved since it was
  written, and this ticket does not resolve it.
- **"Can explain the engineering decisions" (3/6) is not a category.** It fails the
  map's evidence rule at any df: a resume cannot evidence whether someone *can explain*
  something — that lives in an interview. What a resume can carry is whether the bullet
  states its mechanism, and `ats/invariants.py` already checks exactly that as one of
  its four bullet criteria. Covered by the deterministic layer, no judged criterion
  needed.

**`Coverage` dissolves.** As tool coverage it was killed by 02 (4/6 ceiling, inherits
the disjunction bug, scores a strong Ramp candidate as weak). Its surviving
definition — *has this person shipped, owned, evaluated and operated a production LLM
system* — **is** categories 1–3. A single `Coverage` category holding six independent
behaviours would be scored holistically, which is what 08 says costs agreement. The
word survives for what the deterministic keyword rules measure; see `/CONTEXT.md`.

### What the model emits

Not a number (03), and not a band label either. Per category it answers a set of
**criteria** — binary, individually falsifiable evidence questions — each with the
quote that answers it. The band is a deterministic lookup from which criteria are met;
the category score is a lookup from the band.

This is 03's decision at its limit, which 03 sanctioned in advance: *"04 may go further
and decompose a category into binary criteria — the same decision taken to its limit,
not a departure from it."* It is also the shape this codebase already uses:
`ats/invariants.py` scores every bullet on four binary criteria (outcome,
measurability, mechanism, ownership).

Writing the criteria for one category, and the criteria-to-band mapping, is ticket 05.

### Weights become corpus-derived

Document frequency sets category weight. Today `weights.toml` is entirely
hand-authored; under this decision the rubric splits into two blocks:

- **Derived** — categories 1–4, weighted by how many postings state the behaviour
  (6 : 6 : 5 : 3). Digest output, in `/CONTEXT.md`'s sense: *derived, never authored*.
  Add a seventh posting that never mentions evals and Evaluation rigour's weight falls
  with no one editing anything.
- **Authored** — `Parseability`, `Structure & formatting`, `Title & seniority
  alignment`, `Resume craft`. Not in the corpus, so no df exists to derive from.

The arithmetic is left to the implementing effort. Illustratively, holding the
authored block at today's 50 points and splitting the other 50 by 6:6:5:3 gives
15 / 15 / 12.5 / 7.5 — an illustration, not a specification.

**`config.dimension_multiplier()` retires for four of its five rules.** It already
spends df once, scaling rule *cost* by up to 1.5×. With df also setting category
weight, the same count would move the score twice — a smaller copy of the double count
03 just closed. Checked entry by entry: `content/ownership`, `cred/no-production` and
`cred/notebook-only` (→ Production ownership) and `cred/no-evaluation` (→ Evaluation
rigour) would all double-count. `title/seniority-mismatch` would not, because its
category keeps an authored weight, so that entry and `RULE_DIMENSION`'s seniority
dimension survive.

This decides the map's open question about what happens to `RULE_DIMENSION` and
`dimension_multiplier()` once categories are redesigned.

**The digest cannot compute these weights today**, which is what ticket 09 exists to
fix:

| category | inventory (02, hand-read) | `jd_digest.json` now |
|---|---|---|
| Production ownership | 6/6 | production 6/6, ownership **1/6** |
| Agentic systems | 6/6 | **no dimension exists** |
| Evaluation rigour | 5/6 | **3/6** |
| AI-assisted coding fluency | 3/6 | **no dimension exists** |

So the weights named here come from 02's hand-read counts, which are recorded with
verbatim quotes and checkable by hand. Ticket 09 teaches `jd_dimensions.py` to
reproduce them and to compute them for postings added later. This is the same defect
family as 01 (headers the vocabulary never saw) and 02 (a 57-noun taxonomy against a
corpus that converges on verbs): third layer down, five regex sets against four
behaviours, two of which have no pattern at all.

### `rule_share` stops being an inherited constant

`score.py` blends two independent 0–100 opinions of the same category:
`blended = rule_score * rule_share + model_value * (1 - rule_share)`.

Two findings about today's value, both recorded because they change what it is:

1. **It is not a two-value rule in practice.** The 0.7 set is `{PARSEABILITY,
   STRUCTURE, RECRUITER_SCAN}`, but only `Recruiter scan` is in
   `prompts.CATEGORY_NAMES`, so in normal operation 0.7 applies to exactly one
   category. What `scoring-mechanics.md` reads as a policy about mechanical categories
   is one category's exception wearing a set literal.

   The other two entries are **not** inert by construction, though, and that is worth
   separating out: `passes.CATEGORY_BY_NAME` is built over the whole `Category` enum
   and nothing filters a provider's response down to the five requested. A provider
   that returns a `Parseability` entry has it accepted, passed into `llm_categories`,
   and blended at 0.7 — silently converting a category that is supposed to be purely
   deterministic into a blended one. Nothing in the prompt prevents this; only the
   model's obedience does. Not this ticket's to fix, but it is the kind of thing that
   makes a rubric spec untrue of the running system, so it belongs to the migration
   work the map already lists as unspecified.
2. **A category with no rules does not get a 40% rule channel — it gets a constant.**
   `score.build` initialises `deductions = {c: 0.0 for c in weights}`, so a category
   nothing ever deducts from has `rule_score = 100.0` permanently. At `rule_share`
   0.4 it can never score below 40, and 40% of it is pinned at full marks. Latent
   today, because all five judged categories have rules; the new set would have
   activated it.

So `rule_share` is now **set per category by whether a robust rule channel exists**,
where *robust* means absence-over-the-whole-document across many synonyms, and
*brittle* means a closed list of proper nouns.

The distinction is load-bearing, and `cred/no-named-models` is why: a closed list of
15 model families with no Gemini, no DeepSeek, no Cohere, and a `gpt-?\d` pattern that
does not match `o3`. *"Fine-tuned Gemini 1.5 for classification"* fires a false finding
today. The score damage is negligible (MINOR, 4 points, `4 × 0.4 = 1.6` category points
→ 0.16 composite) but the fix list tells the candidate to name a model they named,
which is the real cost.

`PRODUCTION_RE` (20 terms) and `EVAL_RE` (16 terms) are the opposite shape: they fire
only when *nothing* in any bullet or the summary matches, so their failure mode is
false negatives, not false positives. Those earn a rule channel. A name list for AI
coding tools would not — it is `cred/no-named-models`'s shape applied to the corpus's
fastest-moving vocabulary, stale the day it ships. Hence category 4 at `rule_share` 0,
the first model-owned category in the rubric, which `scoring-mechanics.md` notes does
not exist today. Named as a deliberate first, for 05 to test.

### Consequences

**One category changes gate, and the report's grouping moves with it.** `Recruiter
scan` is `Gate.RECRUITER`, `Writing quality` is `Gate.MANAGER`; merged into `Resume
craft` they must pick one. `report.py` groups findings by gate and `score.py:161`
derives the parser and human sub-scores from it, so this is visible output, not
bookkeeping. Recorded as unspecified rather than decided here — it is a reporting
question, not a rubric one.

**`weights.toml` stops being uniformly a "disagree with me" file.** Its header reads
*"Edit these — every number here is a judgment call."* Four numbers become derived
output that hand-editing would silently desynchronise from the corpus. The header must
say which block is which.

**The rules' job is stated, and it is not accuracy.** They supply resolution (a
five-band category moves on nothing until a boundary is crossed) and zero inter-judge
variance. They are not there because regexes judge better than the model. This is why
a category with only brittle rules available is better off with none.

### What this hands downstream

- **05** — writes the criteria for one category and the criteria-to-band mapping, not
  band prose. `Production ownership` is the category to write: 6/6, the most scoreable
  axis in the corpus per 02, and phrased as a claim about history in four of the six
  postings. Its second experiment (band-only vs. band-plus-a-point-inside-it) still
  stands, one field apart as 03 described.
- **06** — measures **criterion** agreement primarily, with band agreement derived
  from it. That is strictly more diagnosable than the band-agreement test the map
  states: two judges landing in different bands can be traced to the criterion they
  split on. The map's acceptance test is unchanged in what it requires; 06 gains a
  level of resolution beneath it.
- **07** — restated. Its ownership question is answered (keyword rules keep tool
  coverage; judged categories take behaviour evidence), leaving the narrower one:
  which new category does each `jd/*` and `kw/*` rule file into, and does any of them
  duplicate a band criterion. `rule_share` makes that mapping load-bearing, so it is
  spec, not implementation detail.
- **09** — new. Repairs `jd_dimensions.py` so the weights named here are computed
  rather than hand-read.

### What would overturn this

05. If criteria cannot be written for `Production ownership` tightly enough for two
judges to answer them the same way, the problem is criteria-only decomposition, and the
fallback is 03's own runner-up — the model names the band label directly, one field
different. The category *set* survives that; only the output form changes.

The separability judgements are the softer part. The production/ownership/reliability
merge is the one most likely to be revisited: it rests on the corpus stating them in
single clauses and on `jd_dimensions.py` already fusing them, not on their being
logically inseparable. If 05 finds judges splitting on reliability independently of
production, that merge is where to look first.

### Changed

- `docs/wayfinder/rubric-grounding/tickets/04-design-the-category-set.md` — this
  ticket, answered and closed.
- `docs/wayfinder/rubric-grounding/tickets/07-which-category-does-each-keyword-rule-file-into.md`
  — restated to the rule-mapping question.
- `docs/wayfinder/rubric-grounding/tickets/09-derive-category-weights-from-the-corpus.md`
  — new.
- `docs/wayfinder/rubric-grounding/MAP.md` — the decision recorded, the
  `RULE_DIMENSION` fog patch resolved, the gate question logged as unspecified, and
  the Notes exception for carrying one execution ticket.
- `/CONTEXT.md` — `Criterion` added; `Band` and `Coverage` sharpened.
