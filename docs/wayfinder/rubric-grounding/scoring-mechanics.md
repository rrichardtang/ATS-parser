# The scoring path as built

A reference for the tickets that implement ticket 03's decision (the model names a
band, not a number). Written by reading `ats/score.py`, `ats/ensemble.py`,
`ats/prompts.py`, `ats/passes.py` and `ats/weights.toml`. Facts about today's code,
not proposals.

Ticket 03 settled *what the model emits*. This records *what the number is made of*,
which 04, 05 and 06 all have to work against and which the decision does not restate.

## There are eight categories, and the model scores five

MAP.md names "the current five". `weights.toml` defines eight; `prompts.CATEGORY_NAMES`
sends five to the model.

| category | weight | model-scored | rule share | model's share of composite |
|---|---|---|---|---|
| Impact & quantification | 22 | yes | 0.4 | 13.2 |
| AI/ML relevance & depth | 18 | yes | 0.4 | 10.8 |
| Credibility & verifiability | 10 | yes | 0.4 | 6.0 |
| Writing quality | 10 | yes | 0.4 | 6.0 |
| Recruiter scan | 15 | yes | **0.7** | 4.5 |
| Parseability | 15 | **no** | — | 0 |
| Structure & formatting | 5 | **no** | — | 0 |
| Title & seniority alignment | 5 | **no** | — | 0 |
| | **100** | | | **40.5** |

Two facts worth carrying forward:

- **The model authors 40.5 of the composite's 100 points.** That is the size of what
  ticket 03 just moved from a number to a band.
- **Three categories worth 25 points already score with no model at all.** The
  deterministic channel is not hypothetical; a quarter of the composite is already
  nothing else.

## The blend, and the asymmetry inside it

`score.py` never uses the model's value raw:

```
blended = rule_score * rule_share + model_value * (1 - rule_share)
```

`rule_share` is 0.7 for `{PARSEABILITY, STRUCTURE, RECRUITER_SCAN}` and 0.4 for
everything else — a two-value rule, not a per-category judgement.

**Recruiter scan is the anomaly**: the only category that is both model-scored and
rules-dominated. Its band would own 30% of the category where every other band owns
60%.

This survives ticket 03's decision intact, because the decision changes what the model
*emits*, not how `score.build` weighs it. So it is a live question for 04 and 05:

- A band's authority over its own category varies 2× by an inherited constant.
- Under the old ±5 test this made Recruiter scan 2× easier to pass than Impact: a
  category score moves by `(1 - rule_share)` × the model's disagreement, so Recruiter
  scan absorbed 16.7 raw points of it against Impact's 8.3. (2×, the same factor as the
  bullet above — an earlier draft said 3.3×, which measured Recruiter scan against a
  category the model owns outright. No category is like that.) The restated test is
  exact band agreement, so that particular distortion is gone — but the underlying
  asymmetry in how much a band is worth is not.

If Recruiter scan survives 04's redesign, someone should decide whether 0.7 is a
position or an accident.

## Three things in the code that the implementing tickets will hit

### 1. The band threshold is duplicated, and one copy is a literal

`ats/ensemble.py:35` defines `BAND_THRESHOLD = 12.0`. `ats/score.py:126` hardcodes
`if band_high - band_low >= 12:`. Tuning one silently leaves the other disagreeing.

Under 03's decision both sites become band-adjacency logic — `combine_scores` is
replaced rather than deleted, and `score.build`'s `(mean, low, high)` interface holds
— so whoever does that work touches both. They should end up as one constant.

### 2. The code never samples twice

`weights.toml` sets `content_samples = 1` in the base block and in **both** the
`economy` and `thorough` modes. MAP.md's acceptance test requires sampling twice per
provider so sampling noise separates from genuine disagreement, and ticket 08's
evidence (judges rerun on identical inputs show low intra-rater reliability) makes
that a measurement requirement, not a nicety.

**Resolved by 06, and not the way this section first read it.** The config stays at 1.
Sampling twice is a measurement requirement, and shipping it doubles the cost of every
user's run to buy them nothing — `content_pass` averages the samples away again before
the report sees them. `scripts/agreement_harness.py` takes `--samples` itself (default
2) and calls `passes.content_judgments()`, the per-(provider, sample) seam extracted
out of `content_pass` for it. Averaging was the obstacle, not the config.

And the within-judge spread that sampling twice buys is each provider's **default**
sampling noise, not a temperature anyone chose: `weights.toml`'s comment on `temperature`
already records that the parameter reaches neither current model. It is therefore a floor
for between-judge spread to clear, not a knob to turn.

### 3. The digest still tells the model "Required in most"

`prompts.py:200` labels the digest list "Required in most: python (3/6)". Ticket 01
found the 3/6 ceiling; ticket 02 sharpened it — **exactly one posting requires Python
unconditionally**, two offer it as one of several ("Python, Go, or TypeScript").

So the model is being told "required in most" about a term one posting requires. Under
03's decision the model no longer authors a number, but it still receives this text as
grounding for the band it names, so the mislabel outlives the decision.

## How today's numbers were derived

For anyone re-checking the 40.5 or the per-category shares: model contribution to the
composite is `(1 - rule_share) * weight`, since `composite = Σ(category_score *
weight) / 100` and the model's value enters each category at `(1 - rule_share)`.
Weights from `ats/weights.toml`, `rule_share` from `ats/score.py:122-124`, the
model-scored set from `ats/prompts.py:180`.
