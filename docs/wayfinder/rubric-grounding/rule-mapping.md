# Where every deterministic rule files

Ticket: [07](tickets/07-which-category-does-each-keyword-rule-file-into.md). Categories
and `rule_share` from [04](tickets/04-design-the-category-set.md); the worked criteria
are [production-ownership-criteria.md](production-ownership-criteria.md); the
finding/criterion split is [findings-identity.md](findings-identity.md).

> **Every rule keeps its code-authored id and gets one of three dispositions: it
> deducts against a named new category, it fires as advice and deducts nothing, or it
> is retired. Tool coverage — every `jd/*` and every `kw/thin-*` — is the whole of the
> advice-only block, because a corpus of disjunctions cannot price a missing noun.**

Three rules are conditional on [12](tickets/12-criteria-for-resume-craft.md) and say so
where they appear.

## 1. The mapping

### Unchanged — their categories survive 04

`parse/hidden-text`, `parse/no-text-layer`, `parse/multi-column`, `parse/tables`,
`parse/edge-band`, `parse/exotic-bullets` → **Parseability**.
`parse/page-count`, `parse/font-sprawl`, `struct/missing-*`, `struct/missing-dates`,
`struct/thin-role`, `struct/bloated-role`, `struct/not-reverse-chron`,
`struct/employment-gap`, `contact/no-<field>` → **Structure**.
`title/off-domain`, `title/seniority-mismatch` → **Title & seniority alignment**.

### Moved — the rules whose category 04 retired

| rule | was | files into | deducts |
|---|---|---|---|
| `cred/no-production` | Credibility | **Production ownership** — the C1 channel | yes |
| `content/ownership` | Impact | **Production ownership** — the C5 channel | yes |
| `cred/notebook-only` | Credibility | **Production ownership** | **no** (§3) |
| `cred/no-evaluation` | Credibility | **Evaluation rigour** — its gate criterion | yes |
| `scan/no-identity-above-fold` | Recruiter scan | **Resume craft** | yes |
| `scan/no-evidence-above-fold` | Recruiter scan | **Resume craft** | yes |
| `scan/no-summary` | Recruiter scan | **Resume craft** | yes |
| `scan/experience-outranked` | Recruiter scan | **Resume craft** | yes |
| `scan/unexplained-pivot` | Recruiter scan | **Resume craft** | yes |
| `content/passive-voice` | Writing quality | **Resume craft** | yes |
| `content/first-person` | Writing quality | **Resume craft** | yes |
| `content/long-bullet` | Writing quality | **Resume craft** | yes |
| `content/duplicate-bullet` | Writing quality | **Resume craft** | yes |
| `content/weak-opener` | Impact | **Resume craft** | yes |
| `slop/portable`, `slop/robotic-rhythm`, `slop/synonym-cycling` | Writing quality | **Resume craft** | yes |
| `kw/over-repetition` | AI/ML relevance | **Resume craft** | yes |
| `kw/skills-dump` | AI/ML relevance | **Resume craft** | yes |
| `kw/soft-skill-padding` | AI/ML relevance | **Resume craft** | yes |
| `content/bullet-invariants` | Impact | **Resume craft**, conditional on 12 | yes, §3 |
| `content/quantification` | Impact | **Resume craft**, conditional on 12 | yes, §3 |
| `cred/unlinked-projects` | Credibility | **Resume craft**, conditional on 12 | yes |
| `contact/no-github` | Credibility | **Structure** — rejoins `contact/no-<field>` | yes |
| `jd/missing-core` | AI/ML relevance | advice-only (§2) | **no** |
| `jd/missing-secondary` | AI/ML relevance | advice-only (§2) | **no** |
| `jd/missing-named-tools` | AI/ML relevance | advice-only (§2) | **no** |
| `kw/thin-<group>` ×7 | AI/ML relevance | advice-only (§2) | **no** |
| `kw/unsupported-skills` | Credibility | advice-only (§2) | **no** |
| `cred/no-named-models` | Credibility | **retired** (§4) | — |

`contact/no-github` is the one entry that needed no argument: it is built by the same
loop as `contact/no-email` and `contact/no-phone` and was filed apart from them only
because a contact field happened to read as credibility. Its siblings' category
survived 04; it goes back with them.

## 2. Tool coverage keeps firing and stops deducting

04 settled ownership — `ats/keywords.py` keeps nouns, the judged categories take verbs
— and that settlement, followed through, removes tool coverage from the score
entirely. Three reasons, in the order they bind:

1. **No category measures nouns.** Filing `jd/missing-core` into `Agentic systems`
   would put term presence into a band whose evidence is *"which tools it could call,
   what decided the next step, what guardrails bounded it"*. The map's evidence rule
   forbids that: a category's deductions have to answer the same question its criteria
   ask, or the band and the rule channel are scoring two different things and the
   blend is meaningless.
2. **The corpus is disjunctive, so a missing term is not a missed requirement.** 02
   recorded it and the ticket preserved it: `jd/missing-core` firing on *python*
   against *"Python, Go, or TypeScript"* is a false finding, and document frequency
   over terms cannot represent an *or*. A signal whose false-positive mode is
   structural must not move a number. This is not a defect to fix later — no repair to
   the header patterns or the taxonomy makes df express a disjunction.
3. **The advice is the value, and it survives.** *"Recruiters search on exactly these"*
   is true and useful whether or not the finding costs points. This is 03's move —
   keep the reading, remove the number — applied one layer down, and it is the same
   move for the same reason.

`kw/unsupported-skills` joins them because it is the same object: a noun claimed in
Skills against the same noun absent from Experience, matched literally. Its defect is
real, but it is priced in the behaviour categories already — a skill with nothing
behind it is a criterion answered `no` wherever that skill mattered — and it fires on a
string match that cannot tell *"Kubernetes"* the claim from *"k8s"* the evidence.

**What advice-only means mechanically.** The finding is emitted with its message, fix
and evidence, and is excluded from the deduction ledger — `score.build` never adds its
cost. Findings are grouped for the report by **gate**, not by category
(`models.GATE_BY_CATEGORY`, `report.py`), so an advice-only finding needs a gate and no
category: tool coverage is `Gate.RECRUITER`, where keyword search actually happens.
That is the same shape as 10's unmet criteria, which are compared as a set and need no
key at all.

**The cost, stated.** Seven `kw/thin-*` rules, three `jd/*` rules and
`kw/unsupported-skills` stop deducting: a resume that names none of the corpus's tools
loses nothing for it. That is intended. The corpus converges on verbs and never above
4/6 on any noun (02), so the postings themselves say tool presence is the weaker
signal, and it was previously the only thing `AI/ML relevance & depth` could deduct
for.

## 3. Collisions

**Cross-channel is not a collision.** `score.py` blends
`rule_score * rule_share + band_value * (1 - rule_share)` — a convex combination, not a
sum. Two channels reading the same evidence average to the level they agree on; the
resume is not charged twice. `cred/no-production` and C1 asking the same question is
therefore *the design*, and it is what `rule_share` 0.4 buys: resolution and zero
inter-judge variance under the model's placement. 05 measured that channel directly —
53/55 criterion answers matched a model judge — so this is not an assumption.

**Within-channel is a collision**, because `deductions[category] += cost` is additive.
Two rules in one category firing on one piece of evidence charge twice. Three exist,
and one is by construction:

1. **`cred/no-production` and `cred/notebook-only`.** Both require
   `not PRODUCTION_RE.search(blob)`; `notebook-only` adds only that notebook language
   is present. They cannot fire apart, so a resume with no production language and one
   mention of a notebook pays MAJOR + MINOR for a single absence, both scaled 1.5× by
   the same `production` dimension. Resolved: **`cred/no-production` deducts;
   `cred/notebook-only` becomes advice-only.** It is a refinement of the same absence
   and its fix text (*"lead with something that ran in production"*) is the more useful
   half, so it survives as advice and stops being a second price for C1.
2. **`content/quantification` and `content/bullet-invariants`.**
   `invariants.evaluate` returns `measurability`, `bullet-invariants` fires on ≥2
   failures of which that is one, and `content/quantification` is the same predicate
   aggregated over the document. In one category they add. Resolved: **measurability
   deducts once, at document level** (`content/quantification`, the more robust of the
   two — a rate, not a per-bullet threshold); `bullet-invariants` keeps deducting for
   its other failures and its measurability failure is advice on the bullet.
3. **`content/ownership` and `content/bullet-invariants`.** `invariants.ownership` is
   `not TEAM_SUBJECT_RE.match(text)` — literally the regex `content/ownership` fires
   on. Under this mapping they land in *different* categories, so they do not add; they
   do something worse, pricing one defect in two categories of the composite. Resolved:
   **team attribution deducts once, in `Production ownership`** as C5's channel, and
   `bullet-invariants`' ownership failure is advice.

Both invariant resolutions cut the same way: `bullet-invariants` is a bundle of four
predicates, and a bundle whose members are separately priced elsewhere must not also be
priced whole. What is left to it — `outcome` and `mechanism` — is craft, and is why it
files where it does.

**The forward constraint for 11 and 12.** The collision test is *evidence*, not
category: before authoring a criterion, check whether a deducting rule in any category
already answers it. A `Resume craft` criterion about team attribution would collide
with `content/ownership` in `Production ownership`; a craft criterion about naming
things would collide with C2, which 05 already found is model-owned because
`SPECIFIC_TOKEN_RE` reads `AI-powered` as a name.

## 4. One rule retired

`cred/no-named-models` fires when a closed list of 15 model families matches nothing.
The list has no Gemini, no DeepSeek, no Cohere, and its `gpt-?\d` does not match `o3`,
so *"Fine-tuned Gemini 1.5 for classification"* fires it today. 04 named it as the
example of the rule shape that does not earn a channel — a closed proper-noun list
against the corpus's fastest-moving vocabulary — and the fix text is the real damage,
telling the candidate to name a model they named.

Nothing is lost by retiring it, because the property it gestures at now has an owner:
**C2 (named system) in `Production ownership`**, and its equivalents in the categories
11 writes. 05 measured that a regex cannot answer C2 at any wording — the one error in
53/55 was exactly there — which is the same finding arriving from the other direction.

## 5. Two categories have no rules, and only one of them may

`Agentic systems` has no deterministic rule and no `jd_dimensions.py` dimension (04's
table: *no dimension exists*). At `rule_share` 0.4 that is not a 40% rule channel — it
is a constant. `score.build` initialises `deductions = {c: 0.0 for c in weights}`, so a
category nothing deducts from holds `rule_score = 100.0` permanently, and the category
can never score below 40 whatever the judge answers. 04 found the mechanism and called
it latent; this mapping is where it stops being latent.

So: **`Agentic systems` takes `rule_share` 0 until 09 gives it a dimension**, joining
`AI-assisted coding fluency` as model-owned. That is a correction to 04's table, forced
by 04's own finding, and it makes the invariant explicit:

> `rule_share` > 0 requires at least one deducting rule in the category. A category
> with none scores against a constant, not a channel.

Resulting `rule_share`: `Production ownership` 0.4 (2 rules), `Evaluation rigour` 0.4
(1 rule), `Agentic systems` **0**, `AI-assisted coding fluency` 0, `Resume craft` 0.7
(19 rules).

## 6. `RULE_DIMENSION` is confirmed, and gains nothing

04 retired the four entries whose category weight now comes from the same document
frequency — `content/ownership`, `cred/no-production`, `cred/notebook-only`,
`cred/no-evaluation` — keeping only `title/seniority-mismatch`, whose category keeps an
authored weight. This mapping confirms it and adds two facts:

- `cred/notebook-only` no longer deducts, so its entry was doubly dead.
- **No new entries.** Every remaining scaled rule would be scaled by the df of the
  category it now sits in, which is the double count 04 closed. `RULE_DIMENSION` ends
  as a one-entry table, and the map's open question about `dimension_multiplier()` is
  answered.

## 7. What this hands downstream, and what would overturn it

- **11** — `Agentic systems` and `Evaluation rigour` have one rule between them. Their
  criteria carry the whole category, as `AI-assisted coding fluency`'s already do, so
  05's "measure the rule-share-0 category first" argument now covers three of four.
- **12** — inherits three conditional rules (`content/bullet-invariants`,
  `content/quantification`, `cred/unlinked-projects`) and must either author criteria
  whose evidence they answer or send them to advice-only. It also inherits the gate
  question, unchanged.
- **09** — a dimension for `Agentic systems` is now worth `rule_share` as well as
  weight: it is the only route by which that category gets a rule channel at all.
- **Migration** — three mechanical asks, all new: a `deducts` flag (or an equivalent
  ledger exclusion) on a rule, findings grouped by gate for the advice-only block, and
  the `rule_share` > 0 invariant asserted somewhere a test can see it.

**What would overturn this.** `Resume craft` now holds 19 of the 22 deducting content
rules at `rule_share` 0.7, while the four corpus-derived behaviours hold three between
them. The rubric's entire deterministic mass sits on the one category the corpus did
not produce and that 05 predicts will not converge. That is a faithful consequence of
where deterministic rules can actually be written — craft is countable, behaviour is
not — but if the composite turns out to be driven by craft deductions, the mapping is
where to look, and the answer would be fewer craft rules deducting, not more behaviour
rules invented.

Second: §2 rests on the corpus staying disjunctive. If postings arrive that state hard
single-tool requirements, tool coverage becomes a scoreable property again and wants a
category rather than a restored deduction.
