# What the model actually authors today

Prep for ticket 03. This describes the current scoring path as built, adds what
tickets 02 and 08 found, and lays out the options. **It does not decide** — 03 is a
grilling, and the fork is the user's to settle.

## The headline number: the model authors 40.5 of the composite's 100 points

MAP.md describes "the current five" categories. There are in fact **eight**, and the
model scores five of them. The other three never reach a model at all.

| category | weight | model-scored? | rule share | model's contribution |
|---|---|---|---|---|
| Impact & quantification | 22 | yes | 0.4 | **13.2** |
| AI/ML relevance & depth | 18 | yes | 0.4 | **10.8** |
| Credibility & verifiability | 10 | yes | 0.4 | **6.0** |
| Writing quality | 10 | yes | 0.4 | **6.0** |
| Recruiter scan | 15 | yes | **0.7** | **4.5** |
| Parseability | 15 | no | — | 0 |
| Structure & formatting | 5 | no | — | 0 |
| Title & seniority alignment | 5 | no | — | 0 |
| | | | | **40.5 / 100** |

Two things follow that reframe 03's question:

1. **The precedent already exists.** Three categories worth 25 points are scored
   with no model involvement whatsoever. "Should the model author scores at all" is
   not a leap into the unknown — a quarter of the composite already works that way.
2. **The model's number is never used raw.** `ats/score.py` blends it against the
   deterministic rule score for the same category:
   `blended = rule_score * rule_share + model_mean * (1 - rule_share)`.
   Rules carry 0.7 on the mechanical categories and 0.4 elsewhere, so the model's
   opinion is damped to 60% (or 30% on Recruiter scan) before it reaches the
   composite.

The 0.7 group is `{PARSEABILITY, STRUCTURE, RECRUITER_SCAN}` — note **Recruiter scan
is model-scored but rules-dominated**, the only category in both sets.

## What the observed spreads actually cost

The 13, 16 and 22 that motivated this map are **raw model spreads**. After blending,
they land very differently depending on the category:

| raw spread | category-space | verdict vs MAP.md's ±5/>8 | composite movement |
|---|---|---|---|
| 13 | 7.8 (Impact/Relevance/Cred/Writing) | 5–8: "wants another look" | 0.78–1.72 |
| 13 | 3.9 (Recruiter scan) | **pass** | 0.59 |
| 16 | 9.6 | fail | 0.96–2.11 |
| 16 | 4.8 (Recruiter scan) | **pass** | 0.72 |
| 22 | 13.2 | fail | 1.32–**2.90** |
| 22 | 6.6 (Recruiter scan) | "wants another look" | 0.99 |

**The worst disagreement ever observed moves the headline score by 2.9 points.** The
blend is already absorbing most of it.

Whether that is reassuring or damning depends on something only the user can settle:
the per-category scores are **user-visible in the report**, with a "providers
disagreed; shown as a range" note. So the disagreement is invisible in the composite
and fully visible in the thing directly above it.

## The ambiguity this exposes in the acceptance test

MAP.md sets the bar at "two providers within **5 points** on every category, above
**8** is a failure". The table above shows this is underdetermined, in two ways:

1. **Which number is measured?** The raw model score, or the blended category score?
   They differ by 1.7× on four categories and 3.3× on Recruiter scan. A raw spread of
   16 fails on the raw number and *passes* on Recruiter scan's blended number.
2. **The same rubric quality gets different verdicts per category**, purely because
   `rule_share` differs. Recruiter scan gets a 3.3× easier test than Impact does, for
   reasons that have nothing to do with the rubric.

**Ticket 06 cannot be built until this is settled**, and it is arguably 03's to
settle, since it is a question about what the model's number *is*.

A third gap: `weights.toml` sets `content_samples = 1` in all three modes. MAP.md's
acceptance test requires sampling **twice** per provider so sampling noise separates
from provider disagreement. Today's code never does that. `ats/passes.py` already
averages repeated samples per provider, so raising the number is the small part; the
harness in 06 is the real work.

## What 02 and 08 say about the fork

Both closed tickets point the same way, from different directions.

**Ticket 08 (agreement research)**: judges cannot agree at 0–100 resolution. A ±5 bar
on a 0–100 scale is near-exact agreement on a ~20-level scale, finer than the
discretization judges actually exhibit. Anchored *discrete* levels are the technique
with evidence behind them; binary decomposition reportedly gains ~20 points of
agreement over graded scoring.

**Ticket 02 (corpus inventory)**: what the six postings actually agree on is
behaviours, at 5/6 and 6/6 — shipped-to-production-and-owned-after, agentic systems,
reliability, end-to-end ownership, evaluation. Every named tool sits at or below 4/6.
The strongest signal in the corpus is naturally **binary per behaviour**: has this
person shipped and owned a production LLM system, evidenced or not.

Put together: the corpus's real signal is binary, and the research says binary is what
judges agree on. That is a coincidence worth taking seriously — but it is a coincidence
about *format*, and 03's question is about *authorship*. They are separable.

## The options

### A. Model emits findings only; composite is fully deterministic

03's stated alternative. Cross-provider score disagreement disappears by construction.

- **Costs**: the 40.5 points the model currently authors have to come from finding
  counts and severities. Every finding is already `MAJOR` (`passes.py` hardcodes
  `Severity.MAJOR` for LLM findings), so severity carries no signal today and would
  have to be made real. `ensemble.combine_scores` and `BAND_THRESHOLD` become dead.
- **Risk**: a resume with few findings scores well by default. Absence of evidence
  becomes evidence of quality — the opposite of what 02 says matters, where the
  question is whether a resume *evidences* production ownership, not whether it
  avoids defects.

### B. Model authors a coarse level; the 0–100 number is derived

The option 08 surfaced, not in 03 as written. The model returns 0–5 (or per-behaviour
binary); code maps it to the 0–100 category score.

- **Costs**: the acceptance test changes from a tolerance to exact level agreement,
  which is simpler to measure. The report's band display needs rework.
- **Fits**: 02's behaviours are natively binary; 08's evidence favours discrete.
- **Open**: whether 5 levels or per-behaviour binary, and whether the derived number
  is honest or false precision.

### C. Keep 0–100, fix the categories only

The implicit status quo — 04 replaces the categories, format unchanged.

- **Costs**: 08 says the format itself is a source of disagreement, so some of the
  13/16/22 will survive any category redesign.
- **In its favour**: the blend already absorbs the disagreement down to ≤2.9
  composite points, and the machinery all works today.

## Two defects found while reading

1. **The 12-point band threshold is duplicated.** `ats/ensemble.py:35` defines
   `BAND_THRESHOLD = 12.0`; `ats/score.py:126` hardcodes `12`. Tuning one silently
   leaves the other disagreeing — `combine_scores` would report a disagreement the
   report does not band, or vice versa.
2. **`digest_text` still labels the list "Required in most"** (`prompts.py:200`).
   Ticket 01 flagged the 3/6 ceiling; 02 sharpened it — exactly one posting requires
   Python unconditionally, two offer it as one of several. The model is being told
   "required in most" about something one posting requires.

## What only the user can answer

1. Do the **per-category scores** matter as output, or only the composite? If only
   the composite, the observed disagreement is already within 3 points and 03 is
   nearly moot. If the categories are the product, ±5 on them is the real bar.
2. Is the acceptance test measured on the **raw** model number or the **blended**
   one? 06 is blocked on this.
3. Is `rule_share` (0.4/0.7) a considered position or an inherited default? It
   currently makes the acceptance test 3.3× easier on Recruiter scan than on Impact.

**My read, offered as a lean and not an answer**: B is the strongest fit for the
evidence — it keeps a score, matches what the corpus actually signals, and is the one
option with research behind its format. But it only pays off if the answer to (1) is
that the categories are the product. If the composite is what matters, C is nearly
free and the disagreement is already absorbed.
