type: research (AFK)
status: closed
claimed: claude
blocked-by: —

# How do anchored rubrics achieve inter-judge agreement?

## Question

The target — two independent LLM judges within 5 points — is a known hard problem with
known techniques: behaviourally-anchored rating scales, forced evidence citation before
scoring, discrete levels instead of continuous 0–100, few-shot calibration examples,
and pairwise comparison instead of absolute scoring.

Gather what actually works, with sources, so category and band design (04, 05) starts
from established practice rather than reinventing it. Pay particular attention to
whether continuous 0–100 scales are ever made to converge, or whether discrete levels
are the precondition.

Done when: findings are captured as a markdown file in the repo and linked here.

## Answer

[`../anchored-rubrics.md`](../anchored-rubrics.md).

**Caveat on the evidence, recorded because it changes how much weight this carries:**
this session's egress policy blocked every external host — `arxiv.org`,
`openreview.net`, `aclanthology.org` and two practitioner sites. Search worked;
fetching did not. Sources are named with identifiers, but none was opened. The two
load-bearing numbers are marked **[verify]** in the file. Any session with network
access can close that gap in minutes; until then these are strong leads, not
established fact.

### On the particular question: discrete levels look like the precondition

Three independent lines converge. A crossed item-rater study across six benchmarks
finds 0–5 gives the strongest human-LLM alignment and 0–100 the weakest. Judges
demonstrably emit a coarse discretization — one measurement found ~20 distinct values
in practice — and cluster mid-scale. Decomposing graded rubrics into binary criteria
raises agreement, reportedly by ~20 points ternary→binary. Human psychometrics puts
the reliability optimum at 7–10 categories, declining past 10.

### The finding that most affects this map

**±5 on a 0–100 scale is a demand for near-exact agreement on a 20-level scale** —
finer than the resolution judges actually possess. The observed 13/16/22 spreads are
consistent with scale-induced noise, not only with vague categories. So the map's
acceptance test is partly a statement about output format, not only about rubric
quality.

Second: **±5 is raw distance with no chance correction.** On a category where real
resumes cluster between 60 and 80, two judges can pass it by luck. The test as written
can be satisfied by a rubric that taught the judges nothing.

### Two expectations the research contradicts

- **Forced evidence citation may not buy agreement.** Chain-of-thought's benefit
  diminishes when explicit scoring criteria are already present; G-Eval's gains appear
  to come from decomposition, not from generating more text. Evidence citation still
  earns its place here — it makes findings checkable, per CONTEXT.md — but not as an
  agreement technique.
- **Pairwise comparison is likely a dead end for this tool.** It matches human
  preference better but flips in ~35% of cases against 9% for absolute scores. It is
  the right primitive for ranking, not for gating one resume against a standard.

### Confirmed rather than contradicted

MAP.md's decision to sample twice per resume per provider is independently supported:
judges rerun on identical inputs show low intra-rater reliability, and averaged
non-deterministic sampling aligns better than deterministic decoding.

## What this hands to the open tickets

1. **03** — a third option: the model authors a *coarse* level (0–5, or binary
   criteria) and the 0–100 composite is derived. Keeps a score without asking judges
   to agree at a resolution they do not have. Orthogonal to 03's own fork; both
   answers can be right.
2. **04** — decomposition is the agreement lever. Fewer, more separable categories
   resolved into concrete criteria beat more categories scored holistically.
   `Coverage` is naturally binary per skill, the shape the evidence most favours.
3. **05** — write the extremes first: intermediate band descriptions matter less than
   the floor and ceiling. Budget for 2–4 scored exemplars, and expect uneven help
   across providers.
4. **06** — report three numbers, not one: between-judge spread, within-judge spread
   across reruns, and a chance-corrected statistic (Krippendorff's α or case-level
   ICC) beside the raw ±5, so a pass is distinguishable from a coincidence.

## Changed

- `docs/wayfinder/rubric-grounding/anchored-rubrics.md` — new, the findings and sources.
