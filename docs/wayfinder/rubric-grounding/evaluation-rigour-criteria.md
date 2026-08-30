# Evaluation rigour: the criteria, and the band they look up

Ticket: [11](tickets/11-criteria-for-the-three-remaining-behaviour-categories.md).
Category defined by [04](tickets/04-design-the-category-set.md); format proved by
[05](tickets/05-draft-bands-for-one-category.md). Measured in
[three-categories-agreement.md](three-categories-agreement.md). Machine-readable in
[criteria/evaluation-rigour.json](criteria/evaluation-rigour.json).

> **Evaluation rigour** — whether the resume evidences measuring model quality with
> something that could have returned a negative answer. 5/6 in the corpus,
> `rule_share` 0.4.

Second of the three, and the one whose vocabulary was not invented here. The baseline
run recorded what two providers reached for unprompted on real resumes, and both
converged on the same terms: *evaluation methodology* (15 findings), *eval
methodology*, *evaluation detail*, *evaluation context*, *baseline*, *benchmark
context*, *dataset detail*, *measurement context*. Roughly 30 of the baseline's 198
findings are this category asking to exist. The criteria below are those readings given
a fixed form.

fluidstack states the bar the top band is written to: *"You've built evaluation
harnesses that told you the truth about model quality before users did."*

## What the judge answers

### C1 — A measurement happened
**Does any bullet say the quality of a model or its output was measured — an eval, a
benchmark, a test set, an A/B test, human annotation, a quality metric?**

*Yes* needs a quote naming the act of measuring. The measurement may be crude; this
criterion only asks that one exists.
*No* looks like: every bullet stops at building or shipping. And **serving numbers are
not a quality measurement** — latency, throughput, cost and uptime say how the system
ran, not whether its answers were any good. Those are `Production ownership`'s C3, and
keeping them out of this gate is what keeps the two categories separable.

### C2 — Named metric and number
**Is the measurement stated as a named metric with a number?**

*Yes* needs a metric a reader could recompute and the value it took — "F1 0.82",
"pass@1 from 41% to 63%".
*No* looks like: "improved model quality", "strong benchmark results". Also a number
attached to something other than quality — a token count, a GPU count — standing in for
a result.

### C3 — What it was run on
**Does the resume say what the measurement was run on?**

*Yes* needs a named dataset, a held-out or golden set, a count of annotated examples,
production traffic, or named raters — the provenance of the number, not only its value.
*No* looks like: "hit 92% accuracy" — on what, chosen how, how many examples.

### C4 — Compared to something
**Is the number compared with something — a baseline, a prior model, a before and
after, a target?**

*No* looks like: a single standalone number. "0.87 F1" is unreadable without knowing
what 0.87 replaced or beat.

### C5 — Could have returned a negative answer
**Does any bullet show the measurement was capable of coming back bad — and say what
happened when it did?**

*Yes* needs a regression caught, a failure mode found, a model rejected on the numbers,
a launch gated, or an eval that ran on every change.
*No* looks like: every number is a win. The evals appear only where they confirmed the
work, and nothing was ever turned down because of one.

## The band lookup

First rule that matches. The shape is `Production ownership`'s, transferred as 05
predicted it would be: a gate, a naming criterion, a pair that splits the middle, and
the judgment call on top.

| band | name | rule | value | reads as |
|---|---|---|---|---|
| **E** | Nothing measured | C1 unmet | 10 | Nothing says anyone checked whether the work was any good. |
| **D** | Measured, not reported | C1 met, and either C2 unmet or neither C3 nor C4 | 35 | Evaluation is claimed, but no metric and number arrive, or the number stands alone. |
| **C** | A number | C1, C2, and exactly one of C3/C4 | 58 | A named metric with a value, and half of what makes it readable. |
| **B** | A readable result | C1, C2, C3, C4; C5 unmet | 78 | Number, subject and comparison all present — and every measurement came back a win. |
| **A** | Evaluation that could say no | all five | 95 | A measurement that was allowed to fail, and what changed when it did. |

## Leverage

| criterion | flips the band | widest move |
|---|---|---|
| C1 a measurement happened | 32/32 | 4 bands |
| C2 named metric and number | 12/32 | 3 bands |
| C3 what it was run on | 8/32 | 2 bands |
| C4 compared to something | 8/32 | 2 bands |
| C5 could have returned a negative answer | 2/32 | 1 band |

The gate is *"did anyone measure anything"*, which is the easiest question in the set,
and the criterion that carries fluidstack's whole standard — did the eval have the
power to say no — sits in the cheapest seat. That inversion is uncomfortable and it is
the correct arrangement: C5 is where two careful readers are most likely to differ, and
here a difference costs one adjacent band. 05's failure condition does not fire.

## Two alias families that had to be cut, and why it matters

The deterministic judge is the rule channel this category's `rule_share` 0.4 pays for,
so its vocabulary is spec, not test scaffolding. Two families were wrong on first
writing and were caught by running them:

- **C5 contained `ci`, `continuous` and `nightly`.** On `strong` they matched
  **"vLLM with continuous batching"** and **"a nightly Airflow batch job"** — serving
  vocabulary, scoring the category's top criterion off a sentence about inference
  latency. Replaced with phrase forms (`continuous integration`, `on every change`,
  `every pull request`).
- **C4 contained `from` and `to`.** They are the fixed tokens of the commonest
  comparison a resume states — *"raised groundedness from 71% to 88%"* — and also of
  every other sentence in English. Cutting them lost the phrasing; keeping them
  answered C4 `yes` everywhere. Resolved with `alias_patterns`, raw regexes beside the
  word list, matching `from <number>` and `<number> to <number>` and nothing else.

Both are the same lesson in opposite directions: a criterion's rule channel fails on
vocabulary long before it fails on judgment, and the only way to find out is to run it
over text that was not written to please it.

## Open

- **`before each release` is C5 and the alias list does not know it.** Probe
  `3-eval-claimed-no-number` says an eval harness "ran it before each release"; the
  model judge reads that as the suite standing between the work and a release and
  answers C5 `yes`, the deterministic judge does not. It cost no band there, and it is
  the same shape as 05's `req/min` gap: a vocabulary defect in the criterion, fixable,
  and worth fixing before it lands on a resume where C3 and C4 both fire.
