# What two judges' criterion answers are worth

Ticket [06](tickets/06-score-from-criterion-answers.md). The measurements the three
decisions rest on, made against `ats/rubric.py`, `ats/criteria/*.json`,
`config.category_weights()` and `score.rule_shares()` — the shipped objects, not a model
of them. The prototype that makes them pressable is `prototype/06-criterion-scoring.html`,
kept on branch `prototype/06-criterion-scoring`.

## 1. Every band gap is wider than the threshold that fires on it

All five specs share one value ladder, so the arithmetic is the same everywhere:

| band | E | D | C | B | A |
|---|---|---|---|---|---|
| value | 10 | 35 | 58 | 78 | 95 |
| gap to the next | | 25 | 23 | 20 | 17 |

`score.py:127` widens a category to a low/high range when the providers' values differ
by **12 or more**. The narrowest disagreement the rubric can express is one adjacent
band, worth **17 points at its narrowest**. The threshold therefore fires on every
split there is, in every category, and a test that always fires measures nothing. It is
not a number to retune: under criteria the comparable quantity is *how many bands
apart*, and the point spread is downstream of it.

What one adjacent band costs the composite, per category — `gap × (1 − rule_share) ×
weight / 100`:

| category | weight | rule_share | composite cost of one band step |
|---|---|---|---|
| Production ownership | 15 | 0.4 | 1.53 – 2.25 |
| Agentic systems | 15 | **0** | **2.55 – 3.75** |
| Evaluation rigour | 12.5 | 0.4 | 1.27 – 1.88 |
| AI-assisted coding fluency | 7.5 | **0** | 1.27 – 1.88 |
| Resume craft | 25 | 0.7 | 1.28 – 1.88 |

`Agentic systems` is the outlier for the reason the map already records under *Not yet
specified*: full weight, and no rule channel to absorb a judge's disagreement.

## 2. The band lookups are monotone, and that is what makes intersecting answers tempting

Over all 32 answer sets × 5 criteria for each of the five specs — 80 removals per
category, 400 in all — **taking a met criterion away never raises the band**. So
intersecting two judges' met sets can only produce a band at or below the lower of the
two. The merge cannot surprise upward.

## 3. It surprises downward, and on `Resume craft` it does so most of the time

Over all 496 unordered pairs of answer sets per category, counting only the pairs where
**both judges land on the same band** — that is, where there is nothing to resolve:

| category | same-band pairs | intersection drops the category below that band |
|---|---|---|
| Production ownership | 171 | 4 |
| Agentic systems | 171 | 4 |
| Evaluation rigour | 171 | 4 |
| AI-assisted coding fluency | 187 | 1 |
| **Resume craft** | **115** | **100** |

`Resume craft` bands on the *count* of criteria met (12: the category's subject cannot
be absent, so there is no gate and no ladder of preconditions). Two judges who each met
three of five — the same band, `Readable, unedited` — but not the same three intersect
to two, which is `Needs a rewrite`. The merge marks a category down for a disagreement
**neither judge reported**, and on craft that is 87% of the agreeing pairs.

This is the measured case against combining answers rather than bands. The gated four
survive it (4 pairs in 171) only because their lookups are ladders; craft's is not, and
a rule that holds for four categories and inverts on the fifth is not a rule.

## 4. The only two-judge data that exists says splits are cheap

`scripts/criteria_probe.py` against the recorded model judge in
`docs/wayfinder/rubric-grounding/criteria/judgments/`, over the 22 band probes and 7
fixtures — the deterministic channel and one model, which is the proxy the other map
measured against:

| category | criterion agreement | band agreement |
|---|---|---|
| Production ownership | 33/35 | 6 exact, 1 adjacent |
| Evaluation rigour | 34/35 | 7 exact |
| Agentic systems | 34/35 | 6 exact |
| Resume craft | 34/35 | 6 exact, 1 adjacent |
| AI-assisted coding fluency | 28/32, C5 unanswerable by a rule channel | not comparable |

**Not one non-adjacent disagreement, and two criterion splits on `Production ownership`
produced one band split.** The shared lookup is absorbing criterion disagreement exactly
as 04 designed it to — which is the argument for reading the splits *through* the
lookup, per judge, rather than around it.

The caveat the other map already carries applies undiminished: one of these two judges
is a regex channel and the other is a recording, on documents written by the sessions
judging them. This is a floor, not a measurement of two providers.

## 5. What a withheld category does today

`content_pass` withholds all five judged categories on a document whose roles did not
parse, and spends no call. `score.build` has never been told. With no entry in
`llm_categories` and a positive `rule_share`, `assessed` stays true and `deductions`
starts at 0.0, so `Production ownership`, `Evaluation rigour` and `Resume craft` — 52.5
of the composite's 100 points — **ride at 100** on a document no parser can read. The
prototype's last walkthrough is that composite beside the three alternatives.
