type: prototype (HITL)
status: open
claimed:
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
