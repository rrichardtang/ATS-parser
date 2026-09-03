type: prototype (HITL)
status: closed
claimed: claude
blocked-by: 02

# Swap the category set

## Question

`models.Category` is an eight-member enum whose five judged members were retired by 04.
Replace them, and repair everything keyed on them.

```python
class Category(str, Enum):          # today
    PARSEABILITY, RECRUITER_SCAN, IMPACT, RELEVANCE, CREDIBILITY, WRITING,
    STRUCTURE, TITLE
```

`Parseability`, `Structure & formatting` and `Title & seniority alignment` carry over
untouched. The other five become `Production ownership`, `Agentic systems`,
`Evaluation rigour`, `AI-assisted coding fluency` and `Resume craft`.

## What is keyed on the enum, all of which moves

- **`weights.toml` `[categories]`** — keyed by display string. Four of the eight
  numbers become derived output (02), which the file's own header contradicts: *"Edit
  these — every number here is a judgment call."* 04 requires the header to say which
  block is which, because hand-editing a derived number silently desynchronises it from
  the corpus.
- **`models.CATEGORY_GATE`** — eight entries. `Resume craft` is `Gate.RECRUITER` per 12,
  and 12 also established that the choice moves no number: `score.py:162` reads
  `_subscore(categories, {Gate.RECRUITER, Gate.MANAGER}, weights)`, a set, so only
  `PARSER` versus the rest is load-bearing.
- **Every `category=Category.X` in `ats/rules.py`, `ats/human.py`, `ats/keywords.py`,
  `ats/slop.py`** — the mapping is `rule-mapping.md` §1, rule by rule, already decided.
- **`score.py:122`** — `rule_share` is a hardcoded set literal, `0.7 if category in
  {PARSEABILITY, STRUCTURE, RECRUITER_SCAN} else 0.4`. 07 replaced it with a per-category
  value: `Production ownership` 0.4, `Evaluation rigour` 0.4, `Agentic systems` **0**,
  `AI-assisted coding fluency` **0**, `Resume craft` 0.7.
- **`prompts.CATEGORY_NAMES`** — the five names sent to the model. Changes here, and
  changes again in 05 when the prompt stops asking for scores.

## Two latent bugs this must not carry across

Both were found by 04 and neither has been hit yet, because today's five judged
categories all have rules and the provider happens to obey the prompt.

1. **A category with no deducting rule blends against a constant.** `score.build`
   initialises `deductions = {c: 0.0 for c in weights}`, so a category nothing deducts
   from holds `rule_score = 100.0` permanently and can never score below its
   `rule_share`. Two of the new categories have no deducting rule at all, which is why
   07 set them to `rule_share` 0 — but the invariant should be asserted where a test can
   see it, not left as a comment: **`rule_share` > 0 requires at least one deducting
   rule in the category.**
2. **Nothing filters a provider's response to the categories that were requested.**
   `passes.CATEGORY_BY_NAME` is built over the whole enum (`passes.py:23`) and
   `score.py:113` blends anything present in `llm_categories`. A provider that returns a
   `Parseability` entry has it accepted and blended at 0.7, silently converting a
   deterministic category into a judged one. Only the model's obedience prevents it.

Done when: the new category set is the one the program uses; `rule-mapping.md` §1's
dispositions are what the rules carry; `rule_share` is per-category data with the
invariant under test; a provider's unrequested category is dropped rather than blended;
`weights.toml` states which block is derived; and the existing test suite passes.

## What was done

`models.Category` is the new eight. `Parseability`, `Structure & formatting` and
`Title & seniority alignment` carry over untouched; the other five are gone and are not
renamed into anything — `rule-mapping.md` §1 redistributes their evidence rule by rule,
and that mapping is what every `category=Category.X` now carries.

`cred/no-named-models` was retired outright (§4) rather than refiled: a closed list of
15 model families against the corpus's fastest-moving vocabulary, with no Gemini, no
DeepSeek and a `gpt-?\d` that does not match `o3`. C2, the named system in `Production
ownership`, owns the property now.

### Weights: the derived block has no numbers to edit

`weights.toml` holds the authored four — `Parseability` 15, `Structure` 5, `Title` 5,
`Resume craft` 25 — and **no number at all** for the derived four. What it holds
instead is `[derived] budget = 50`, and `config.category_weights()` computes the split
with `jd_dimensions.derived_weights` over the digest.

That is stronger than the header change the ticket asked for. 04's concern was that
hand-editing a derived number silently desynchronises it from the corpus; a header
saying "don't edit these" relies on being read. There is nothing to edit now, and the
weights are 15 / 15 / 12.5 / 7.5 because six postings say 6:6:5:3, not because anyone
typed them.

`[derived.fallback_document_frequency]` records the six-posting scan so a checkout with
no personal corpus still scores by the corpus the repo shipped with, rather than the
derived block collapsing to zero. It is not a second set of weights — it is the same
derivation over a recorded count.

### `rule_share` is the specs' own number

`score.rule_shares()` reads `rule_share` from each category's spec in `ats/criteria/`,
so `Production ownership` 0.4, `Evaluation rigour` 0.4, `Resume craft` 0.7,
`Agentic systems` 0 and `AI-assisted coding fluency` 0 are 07 §5's values at their
source rather than a copy of them. `rubric.slug_by_category()` builds the lookup from
what each spec calls itself, which keeps `ats/rubric.py` importing nothing from the
rest of the package.

## The two latent bugs, and a third the first one was hiding

**Bug 2, the unfiltered provider response.** Closed on both sides.
`passes.CATEGORY_BY_NAME` is built over `JUDGED_CATEGORIES` rather than the whole enum,
so a model naming `Parseability` no longer resolves to a category, and `score.build`
drops any `llm_categories` entry outside the judged five before blending. Either half
alone would leave the other open — the parser map also decides where a *finding* files
— so both are there, with a test asserting that the prompt asks for exactly the set the
parser accepts.

**Bug 1, the constant behind a rule_share.** The invariant is under test, and the test
reads the rule modules' source, because whether a category *has* a rule is a structural
fact rather than something a run can observe. It is checked in both directions: a share
above 0 with no rule is the bug, and a rule in a category with share 0 is a deducting
channel the blend ignores.

**And the third, which the swap surfaced immediately.** `rule_share` 0 only protects
the *blend*. A run with no provider credentials never reaches the blend at all, and
`deductions` starts every category at 0.0 — so `Agentic systems` and `AI-assisted
coding fluency` came out of the swap scoring a permanent **100**, carrying 22.5 points
of the composite, on every document. `tests/test_pipeline.py` caught it as a
human-gate score that would not fall: `slop` scored 64.3 where the test wanted under
60, and the missing 30 points were two categories reporting "nothing wrong here" about
questions nobody had asked.

The threshold was not what was wrong. `CategoryScore.assessed` is now false when no
judge answered a judged category *and* no rule can deduct from it *and* nothing did;
an unassessed category is printed, shown as `n/a`, and left out of the composite, the
sub-scores and the points denominator alike. It is the same refusal the unreadable-
document path already makes, applied per category. `slop` falls to 50.3 on the human
gate, and a clean resume still scores 100 because the excluded weight leaves the
denominator with it.

The last clause keeps it self-correcting: if a finding does deduct into one of those
categories, the category is assessed after all and its deduction counts.

## Changed

- `ats/models.py` — the new `Category`, `DERIVED_CATEGORIES`, `JUDGED_CATEGORIES`, the
  new `CATEGORY_GATE`, and `CategoryScore.assessed`.
- `ats/weights.toml` — authored block only, plus `[derived]` budget and the recorded
  fallback counts. `ats/config.py` — `derived_document_frequency()`, and
  `category_weights()` computing the derived half.
- `ats/rules.py`, `ats/human.py`, `ats/keywords.py`, `ats/slop.py`, `ats/passes.py` —
  §1's mapping, and `cred/no-named-models` retired. The eleven advice-only rules sit in
  `Resume craft` **provisionally**: they still deduct, because nothing can yet express
  a finding with a gate and no category. That is 04, and `ats/keywords.py` says so
  where the rules are.
- `ats/score.py` — `rule_shares()` from the specs, the judged-category filter, and the
  assessed/unassessed arithmetic. `ats/rubric.py` — `slug_by_category()`.
- `ats/prompts.py` — `CATEGORY_NAMES` from the enum, so it cannot drift from the parser.
- `templates/report.html` — an unassessed category renders `n/a`, not a zero bar.
- `tests/test_scoring.py` — the weights, the derived block having no authored numbers,
  both latent-bug invariants, and the unassessed-category rule. Category substitutions
  in `test_agreement.py`, `test_jd_digest_wiring.py`, `test_llm_passes.py` (whose stub
  was returning retired category names, which the new filter correctly discarded).
- `scripts/weight_budget.py` — reduced. Its mapping, weight sets and composite
  arithmetic were a model of what this ticket implemented; keeping them would have left
  a second copy to drift. What remains reads `config.category_weights()` and
  `score.rule_shares()` and prints the tolerance table, which a single run cannot
  produce because it needs two judges. It reproduces 02's numbers exactly (12.8 worst,
  on `Agentic systems`) from the live program. `weight-budget.md` says which of its
  tables are the pre-swap record.
