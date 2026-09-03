# What the dimension scan now sees

Ticket: [09](tickets/09-derive-category-weights-from-the-corpus.md). Ground truth is
[inventory.md](inventory.md), read by hand from `corpus/jds/user/`. The categories the
counts feed are [04](tickets/04-design-the-category-set.md)'s; the rule mapping that
decides what else a count may scale is [rule-mapping.md](rule-mapping.md).

> **`ats/jd_dimensions.py` reproduces 02's four hand-read counts exactly — 6/6, 6/6,
> 5/6, 3/6 — from eight behaviour dimensions, four of which are new. Categories are
> unions of dimensions, so the count 04 derives weight from is computed per category,
> not summed per pattern.**

## 1. The counts, and what fired

| category | dimensions | 02, hand-read | before | now |
|---|---|---|---|---|
| Production ownership | `production` ∪ `ownership` ∪ `reliability` | 6/6 | production 6/6, ownership **1/6** | **6/6** |
| Agentic systems | `agentic` | 6/6 | **no dimension** | **6/6** |
| Evaluation rigour | `evaluation` | 5/6 | **3/6** | **5/6** |
| AI-assisted coding fluency | `ai_assisted_coding` | 3/6 | **no dimension** | **3/6** |

Per dimension: `production` 6/6, `ownership` 6/6, `reliability` 6/6, `agentic` 6/6,
`evaluation` 5/6, `ai_assisted_coding` 3/6, `seniority` 2/6, `experience_gate` 3/6.

The match is worth exactly as much as the phrase behind each hit, so here is every
hit that carries a category, as the matched text:

| posting | ownership | production | agentic | evaluation | ai-assisted |
|---|---|---|---|---|---|
| amex | *operate what you build after launch* | *in production* | *agentic* | *evaluation* | *AI-assisted* |
| anthropic | *from technical discovery through successful deployment* | *production applications* | *agent* | *evaluation frameworks* | — |
| edra | *from discovery and solution design through production* | *shipped something meaningful to production* | *agentic* | *evaluation frameworks* | — |
| fluidstack | *owned*, *end to end* | *shipped ML or LLM features to production* | *Agentic* | *evaluation harnesses* | *with AI coding tools* |
| openai | *end-to-end* | *in production* | *tool-using* | *measure agent performance, regressions* | — |
| ramp | *owning*, *end to end* | *production-grade* | *agentic* | — | *coding models* |

Every one of these is the sentence `inventory.md` quotes for that posting, which is the
check that matters: the patterns hit for the reason the human reader counted it, not
by finding the word somewhere else in the document.

**The two counts that are not 6/6 are the load-bearing ones.** Evaluation must miss
ramp — a frontend role that says nothing about evals — and AI-assisted coding must hit
exactly amex, fluidstack and ramp. A pattern set generous enough to read 6/6 on both
would reproduce nothing; it would just be matching the corpus's general vocabulary.
Both are asserted directly.

## 2. Designing against overfitting

Six postings is a small corpus and the counts are published, so tuning until the
numbers match is easy and nearly worthless — the point of deriving weight from a corpus
is that the seventh posting moves it with nobody editing anything.

The rule adopted: **a pattern is a family, not a sentence** — a verb set crossed with
an object set. `_SHIP` and `_DESTINATION` are shared across dimensions so that
"shipped" and "deployed" cannot be spelled out in one dimension and forgotten in
another. Anything that only matches one posting's phrasing belongs in the test file,
not in `DIMENSIONS`.

`tests/test_jd_dimensions.py` enforces this from both ends. The corpus tests use
verbatim posting text. The generalisation tests use phrasing that appears nowhere in
the six — *"steward each initiative from kickoff to rollout"*, *"carry the pager"*,
*"benchmark candidate models"*, *"Pair with Cursor and Copilot daily"* — and a negative
case (a WordPress marketing role) that must hit nothing at all.

The honest limit: generalisation is tested against phrasings I wrote, and I wrote them
knowing the patterns. It is a guard against the narrowest overfitting, not proof of
coverage. The real test is the seventh real posting, and the failure it would show is
a *false negative* — a behaviour stated in words no family anticipated — which is
exactly the defect this ticket was opened to fix and will not be the last of.

## 3. Two dimensions that are not category weights

**`reliability` is split out of `production`.** It was one alternative inside the
production pattern list (`\breliability\b`), which meant a posting could read
"production" on the strength of the word *reliable* alone. They are separate
behaviours, both 6/6 in the corpus, and 04 merges them at the *category* level — which
is a judgement about separability for a judge, not a reason to conflate them in the
scan. Splitting them costs nothing (the category is a union) and makes each count
mean one thing.

**`experience_gate` is recorded and never scored.** 02 found three postings gate on
years — amex and anthropic 4+, edra 3+ — and the `seniority` dimension read 0/6,
"right about titles and wrong about the corpus". Adding years to `seniority` would have
silently changed what `title/seniority-mismatch` costs, since that rule reads that
dimension. So the numeric gate is its own dimension with no scoring target. It exists
so the digest stops being blind to half the corpus, and it is inert until something
decides what a years gate should cost.

**`leadership` is removed.** No scoring target, 0/6 on the real corpus, and a dimension
nothing consumes is an invitation to wire it up without deciding what it should cost.

## 4. The weight derivation

`derived_weights(counts, total, budget)` splits a point budget across the behaviour
categories in proportion to document frequency. On the current corpus at a budget of
40: Production ownership 12.0, Agentic systems 12.0, Evaluation rigour 10.0,
AI-assisted coding fluency 6.0 — or whatever budget the map's open question settles
on. **`budget` is a parameter, not a constant, on purpose.** 04 settled that df
sets these weights and left how many of the composite's 100 points the derived block
gets explicitly open. This is the derivation; the number it divides is still authored.

A category no posting states gets 0 and consumes no budget: the corpus saying nothing
about a behaviour is the corpus saying it is not worth points.

Demonstrated on a corpus with a posting added, per the ticket:
`test_a_seventh_posting_moves_the_weights_with_nobody_editing_anything` adds a seventh
posting that asks for evals and nothing agentic. `Evaluation rigour` goes 5/6 → 6/7 and
its weight rises; `Agentic systems` stays 6 and its weight falls, because the budget is
shared. Nothing in `jd_dimensions.py` or `weights.toml` changes.

The digest now carries this as `category_document_frequency`, computed at build time
rather than derived from the per-dimension counts — a category is a union, so a posting
stating two of its behaviours must still count once, and that cannot be recovered from
the totals.

## 5. `RULE_DIMENSION` is down to one entry, and that entry is nearly inert

The four double-counting entries are gone (`content/ownership`, `cred/no-production`,
`cred/notebook-only`, `cred/no-evaluation`), per 04. `test_jd_digest_wiring.py` now
asserts it rather than trusting it: with every behaviour dimension at 6/6, all four
must return a multiplier of exactly 1.0. `cred/notebook-only` was doubly dead — 07 had
already stopped it deducting at all.

What survives is `title/seniority-mismatch`, whose category keeps an authored weight so
nothing else spends the seniority count. Measuring it turned up something the ticket
did not ask for: **`Title & seniority alignment` is weighted 5 of 100, so the largest
composite movement the entire multiplier mechanism can now produce is 0.05 points** —
below the report's own rounding, which is why that test had to be rewritten to assert
on the category score instead. `dimension_multiplier()` is 40 lines of machinery, a
digest field and a scoring hook, for an effect no user can see.

Not removed here, because 04 kept the entry deliberately and this ticket's brief was to
stop the double count, not to decide the mechanism's future. Recorded as the case for
retiring it: if `title/seniority-mismatch` is the only rule it will ever scale, the
mechanism costs more to keep than it is worth.

## 6. What this hands downstream

- **04's weights are now computed rather than transcribed.** The four numbers in its
  table come out of the corpus, and a seventh posting moves them.
- **The weight arithmetic is still open** — the budget, and proportional versus tiers.
  This supplies the input to both; it does not choose between them.
- **09's failure mode is a false negative**, and the only thing that surfaces one is a
  new posting whose phrasing no family anticipated. Worth re-running the counts against
  `inventory.md` whenever a posting is added, which is what
  `scripts/build_user_corpus.py` now prints.
