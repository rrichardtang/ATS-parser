# Baseline: the first real run of the acceptance test

Ticket: [06](tickets/06-build-the-agreement-harness.md) built the harness; this is what
it found on the rubric that is still in the code. Run 2026-08-30,
`anthropic:claude-sonnet-5` and `openai:gpt-5.6-luna`, 2 samples each, the seven
fixtures plus the owner's real resume.

```
python scripts/baseline_analysis.py baseline/run-summary.json
```

**What this measures is today's shipped rubric, not the one this map is designing** —
the five categories 04 retired, with the model emitting 0–100 numbers. It is the
*before* picture, and the first time the spread the map opens with has been measured
rather than remembered.

The raw run quotes resumes verbatim and is gitignored for that reason.
[baseline/run-summary.json](baseline/run-summary.json) is the same run with every span
of resume text, every finding message and every category justification removed, so the
arithmetic below stays checkable. `scripts/baseline_analysis.py --extract` produced it.

## Headline

The rubric fails its own test on every axis. Between-judge spread is 16–21 points mean
against a 5-point bar, up to 37.5. `AI/ML relevance & depth` exceeds the bar on **7 of
7** resumes. Within-judge spread — one provider against itself on a rerun — reaches
**20.0**, past the 8-point failure line on its own.

`Recruiter scan` looks better than the rest (3/7 over the bar) purely because
`rule_share` 0.7 scales its model disagreement by 0.3. Its raw spread, 16.9, is the
same as everything else's. The rule channel is masking that category, not fixing it —
worth knowing before [07](tickets/07-which-category-does-each-keyword-rule-file-into.md)
sets `rule_share` per category.

## The disagreement is mostly directional

```
openai scores above anthropic in 34/35 category-resume cells, mean +18.0 points
```

Per-category offsets sit in a tight band (+16.2 to +20.6), so this is a property of the
provider, not of any resume. And the judges rank almost identically — Spearman 0.75 to
0.96. They order the same resumes the same way and put the numbers in different places.

## But the offset is only half of it

An earlier reading of the printed tables said "subtract the offset and everything
passes". That is true of the **composite** (largest residual 2.4) and false of the
**categories**, which is what the acceptance test gates on:

| category | offset | resid mean | resid max | spearman | within 5 |
|---|---|---|---|---|---|
| Impact & quantification | +18.2 | 8.5 | 16.7 | 0.96 | 3/7 |
| AI/ML relevance & depth | +20.6 | 7.7 | 16.9 | 0.75 | 3/7 |
| Credibility & verifiability | +18.1 | 6.1 | 13.6 | 0.96 | 3/7 |
| Recruiter scan | +16.9 | 6.8 | 14.1 | 0.93 | 3/7 |
| Writing quality | +16.2 | 10.1 | 20.3 | 0.93 | 2/7 |

Remove each category's own offset and **7.9 points of disagreement remain on average**,
with only 14 of 35 cells inside the bar. Category residuals partly cancel when they are
weighted into a composite, which is why the composite looked clean and the categories
are not.

## The residual sits on top of an identical reading

This is the result that matters, and it is qualitative. `strong` /
`Credibility & verifiability` — anthropic 62/58, openai 79/79, a 19-point gap:

> **anthropic s0** — metrics "stated without the eval set, metric definition, or
> measurement method"
> **anthropic s1** — "no stated methodology for the eval numbers... unverifiable as
> written"
> **openai s0** — "metric definitions, benchmark provenance, and deployment reach are
> not verifiable"
> **openai s1** — "several metrics lack evaluation protocols, benchmark conditions,
> baselines, or deployment context"

Four independent judgements, one identical reading, nineteen points apart. The same
holds on `two_column` / `Writing quality`, the worst residual in the run: all four
samples say the bullets are telegraphic and omit context, and the numbers land 50, 55,
57, 48.

**The disagreement is not about the resumes. It is about turning a shared reading into
a number.**

## The findings table was measuring the wrong thing

06 keys findings on `(rule_id, locator)`, per 03. Both halves of that key are text the
model invents. Re-keyed:

| key | within judge | between judges |
|---|---|---|
| `(rule_id, locator)` — what the harness reports | 0.09 | **0.03** |
| `locator` alone | 0.57 | **0.51** |
| quoted evidence span | 0.45 | 0.36 |

The judges agree on about **half the places** they flag and on **3%** of the (name,
place) pairs. The near-zero in the harness output is a naming artifact, not a
measurement of disagreement.

Why: **108 distinct `rule_id`s across 198 findings**, only **5** used by both
providers. `missing-evaluation-methodology`, `-detail`, `-context`, `-method` and
`missing-eval-methodology` are five spellings of one defect, 33 findings between them.
`prompts.CONTENT_SYSTEM` asks for a name "reused verbatim across every finding of that
kind"; the models invent a fresh synonym each time. `Report.grouped` and the ledger both
key on `rule_id`, so today one defect renders as five cards.

Note also that within-judge barely beats between-judge on locator (0.57 vs 0.51).
Finding *localisation* is unstable inside a single judge, not between providers — so
ensembling two providers buys nothing there.

## What this changes for the rubric being designed

**04's output-form decision is now evidence-backed rather than argued.** A model that
never emits a number cannot carry a +18 calibration offset, and — per the `why` lines —
most of the 7.9-point residual goes with it, because that residual sits on top of
readings that already agree.

**Criteria fix the localisation problem, for a reason neither 03 nor 04 gave.** Today's
prompt says *find defects* — an open-ended search, and search is where the instability
lives (within ≈ between). A criterion asks a fixed question about the whole document:
*does any bullet say the work reached production*. There is no localisation choice left
to be unstable about.

**A closed vocabulary is mandatory, and criteria already are one.** `C1`–`C5` are fixed
strings by construction. The findings channel needs the same treatment — see
[ticket 10](tickets/10-what-makes-two-findings-the-same-finding.md).

**The judges supplied criteria vocabulary for free.** Unprompted, both converge on the
same terms: *evaluation methodology / protocol*, *deployment context / reach*, *scale,
traffic, latency, cost, adoption*. That maps almost exactly onto `Production
ownership`'s C3 and onto `Evaluation rigour`. It is better evidence for wording the
remaining categories' criteria than intuition is.

**Two of 05's predictions have their first evidence.** `Writing quality` has the worst
residual (10.1 mean, 20.3 max) — 05 predicted `Resume craft` is the category that will
not converge. `AI/ML relevance & depth` has the lowest rank agreement (0.75) and fails
on 7/7 — it is the one category where the judges genuinely order resumes differently,
and 04 dissolved it into behaviours.

**None of this validates 05's own measurement.** That compared a regex to one model
judge on documents largely written for the purpose. What this run supports is the
*design premise* underneath it — a weaker and different claim than "the criteria
converge across providers", which remains unmeasured.

## What it hands each ticket

- **10 (new)** — the findings key and the invented vocabulary are one question: what
  makes two findings the same finding.
- **07** — `rule_share` 0.7 masks rather than fixes `Recruiter scan`. A rule channel
  that hides model disagreement is not the same as one that resolves it, and the
  distinction should be explicit when `rule_share` is set per category.
- **06** — report finding overlap on locator and on the evidence span alongside the
  `(rule_id, locator)` key; on this run the choice moved the answer by 17×.
- **03** — one datum it did not have: removing the model's findings deductions (its
  `no deduct` column) *widened* the composite spread on 5 of 6 resumes. The two channels
  were partly cancelling. It does not refute 03, whose argument rested on finding-count
  arithmetic, but it should be recorded against it.
- **08** — the judges quantize consistently *relative to each other* (ρ 0.75–0.96) while
  differing by a near-constant offset. That is the shape 08's sources predict; it is
  also the first local evidence for them, and the map still flags those sources as
  unopened.
