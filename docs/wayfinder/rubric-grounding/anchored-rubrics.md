# How anchored rubrics achieve inter-judge agreement

Findings for ticket 08. Gathered to let category design (04) and band drafting (05)
start from established practice, and to give the scoring-form fork (03) something
better than intuition to argue against.

## Read this first: sources are named but unopened

Every external host was blocked by this session's egress policy — `arxiv.org`,
`openreview.net`, `aclanthology.org`, and two practitioner sites all refused. Search
worked; fetching did not. So **every claim below comes from search-result summaries,
not from the papers themselves.** Titles, authors and identifiers are recorded so any
session with network access can verify them.

Treat the quantitative claims as leads, not as settled numbers. Two are load-bearing
enough that they should be checked against the source before anything is built on
them; they are marked **[verify]** where they appear.

## The headline: discrete levels are the precondition, and 0–100 is the worst case

The ticket asked whether continuous 0–100 scales are ever made to converge, or
whether discrete levels are a precondition. The evidence points one way.

*Grading Scale Impact on LLM-as-a-Judge* (arXiv 2601.03444) compares 0–5, 0–10 and
0–100 across six benchmarks with twelve graduate annotators and six LLMs in a fully
crossed item-rater design. Aggregated over tasks, **0–5 gives the strongest
human-LLM alignment; 0–100 the weakest** **[verify]**. The scale is not a neutral
reporting choice — changing it moves agreement even when panel reliability within a
group of judges stays high.

Three independent lines converge on the same conclusion:

- **Judges do not actually use a fine scale.** They latently encode something
  continuous but emit a coarse discretization of it, and they cluster: lots of 6s and
  7s on a 1–10 scale, few 1s or 10s. One measurement found a judge with roughly 20
  distinct score values in practice.
- **Decomposition beats gradation.** Splitting multi-dimensional Likert rubrics into
  fine-grained binary criteria raises inter-rater agreement; one reported figure puts
  the ternary→binary move at **about +20 percentage points** **[verify]**, on the
  reading that partial credit adds ambiguity without adding discriminative power.
  HealthBench's 48,562 physician-authored binary criteria (Arora et al., 2025) is the
  existence proof at scale.
- **Human psychometrics agrees, from the other side.** Reliability rises with
  response categories then falls back; Preston and Colman (2000) put the best range at
  7–10 categories, with decline past 10. Nobody in that literature recommends 100.

The catch, and it matters for us: coarse scales buy agreement with ties. A judge
using ~20 distinct values produced a 66.5% tie rate on similar candidates. Ties are
fatal if you need to *rank* resumes against each other; they are harmless if you need
to *gate* one resume against an absolute standard. This tool does the latter.

## What the acceptance test is actually asking for

MAP.md sets the bar at two judges within **5 points on a 0–100 category score**,
failing above 8. Stated in the literature's terms, that is a demand for agreement
within 1/20th of the scale — which is to say, **near-exact agreement on a 20-level
scale**, finer than the discretization judges demonstrably exhibit.

That does not make the bar wrong. It makes it a bar about the *output format* as much
as about the rubric: a 0–100 scale that judges internally quantize into ~20 buckets
will fail a ±5 test on bucket-boundary cases no matter how good the band prose is.
Two ways out, both worth putting to ticket 03:

1. **Score on 0–5 (or binary criteria) and derive the 0–100 composite.** Judges agree
   on the discrete level; the fine-grained number becomes an arithmetic consequence,
   not a thing anyone has to agree on. The acceptance test then measures exact
   level agreement, which is checkable without a tolerance at all.
2. **Keep 0–100 and expect to spend the agreement budget on scale artifacts** rather
   than on rubric quality. The observed spreads of 13, 16 and 22 that motivated this
   map are consistent with scale-induced noise, not only with vague categories.

This is the strongest argument the research offers ticket 03, and it is orthogonal to
that ticket's own framing: 03 asks *whether the model should author a number at all*;
this says *if it authors one, the number should be coarse*. Both answers can be right.

## Techniques, and what the evidence says about each

**Behaviourally-anchored rating scales (BARS).** Each scale point carries 2–3
observable behaviour examples drawn from the real job; typically 5, 7 or 9 points.
The human-rater literature is consistent: higher inter-rater reliability, less central
tendency bias, more defensible. This is the closest existing analogue to what ticket
05 will write, and it is the reason 05's instinct — write bands in evidence terms —
is sound.

**Anchor the extremes hardest.** *An Empirical Study of LLM-as-a-Judge* (arXiv
2506.13639; Yamauchi, Yano, Oyamada; GEM 2026) finds comprehensive criteria and
reference answers drive reliability, but that **intermediate score descriptions matter
less than extreme ones**. Useful budgeting advice for 05: spend the prose on what a
floor and a ceiling look like, not on agonising over the middle band.

**Few-shot calibration examples.** A rubric without exemplars collapses toward central
scores, because judges do not share a latent image of what separates a 3 from a 5.
Two to four scored examples anchor the scale. But this is judge-specific rather than
universally good: reported gains on three of four judges, with anchoring effects
*introduced* in context-sensitive models. Worth trying, not worth assuming.

**Forced evidence citation / chain-of-thought before scoring.** This one cuts against
the ticket's expectation. The same empirical study finds **CoT's benefit diminishes
when explicit scoring criteria are already present**, making direct scoring a viable
and cheaper alternative. G-Eval's gains appear to come from *decomposing* criteria
into steps, not from generating more text. The lesson for us is that evidence citation
earns its place by making findings checkable — which this codebase already requires,
per the Finding definition in CONTEXT.md — not by improving agreement on its own.

**Pairwise comparison instead of absolute scoring.** Better at matching human
preference, worse at stability: *Pairwise or Pointwise?* (arXiv 2504.14716) reports
preference flips in **~35% of cases against 9% for absolute scores** **[verify]**, and
finds pairwise more vulnerable to spurious "distractor" features. Pairwise is the
right primitive for relative quality; absolute rubric scoring is the right primitive
for gating. Scoring one resume against a standard is a gate, so pairwise is likely a
dead end here — worth recording so it is not re-proposed.

**Sample more than once.** *Rating Roulette* (arXiv 2510.27106; Haldar and
Hockenmaier; Findings of EMNLP 2025) ran judges three times on identical inputs with
identical settings and found intra-rater reliability low enough to call ratings
"almost arbitrary" in the worst case. The 2506.13639 study separately finds
non-deterministic sampling with score averaging aligns better than deterministic
decoding. **MAP.md's decision to sample twice per resume per provider is independently
supported** — and the harness in ticket 06 should treat self-inconsistency as a
first-class measurement, not only as noise to subtract.

## The measurement problem: ±5 is not an agreement statistic

*Agreement Metrics for LLM-as-Judge Evaluation: What to Report and Why* (arXiv
2606.00093) argues for chance-corrected agreement — Krippendorff's α preferred over
Cohen's and Fleiss' κ for handling multiple annotators, missing data, and scale-
appropriate distance functions. But it also warns that α approaches perfect agreement
under skewed label distributions, so raw percentage agreement and pairwise κ should be
reported alongside it, and ICC at case level used where the panel's consistency is
what matters.

MAP.md's ±5 is raw distance with no chance correction. On a category where almost
every real resume lands between 60 and 80, two judges guessing within that range will
pass a ±5 test regularly by luck. **The acceptance test as written can be satisfied by
a rubric that has taught the judges nothing** — which is precisely the failure mode a
grounded rubric is supposed to prevent.

This does not mean replacing the ±5 bar; it is legible and it is what the user
actually cares about. It means ticket 06's harness should report a chance-corrected
statistic next to it, so a pass can be distinguished from a coincidence.

## What this hands to the open tickets

1. **To 03** — a third option beyond "model scores" and "model emits findings only":
   the model authors a *coarse* level (0–5, or binary criteria), and the 0–100 number
   is derived. This preserves a score without asking judges to agree at a resolution
   they do not possess.
2. **To 04** — decomposition is the lever that buys agreement. Fewer, more separable
   categories each resolved into concrete criteria will agree better than more
   categories scored holistically. Also: `Coverage` is naturally binary per skill,
   which is the shape the evidence most favours.
3. **To 05** — write the extremes first; the middle bands matter less than the floor
   and ceiling. Expect to need 2–4 scored exemplars, and expect them to help unevenly
   across providers.
4. **To 06** — measure and report three things, not one: between-judge spread,
   within-judge spread across reruns, and a chance-corrected agreement statistic.
   Raw ±5 alone cannot distinguish a good rubric from a lucky one.
5. **Not pursued** — pairwise comparison, as a poor fit for absolute gating.

## Sources

Unopened; recorded for verification.

- [Grading Scale Impact on LLM-as-a-Judge: Human-LLM Alignment Is Highest on 0-5 Grading Scale](https://arxiv.org/pdf/2601.03444)
- [Pairwise or Pointwise? Evaluating Feedback Protocols for Bias in LLM-Based Evaluation](https://arxiv.org/abs/2504.14716)
- [Rating Roulette: Self-Inconsistency in LLM-As-A-Judge Frameworks](https://aclanthology.org/2025.findings-emnlp.1361/) (arXiv 2510.27106)
- [An Empirical Study of LLM-as-a-Judge: How Design Choices Impact Evaluation Reliability](https://arxiv.org/abs/2506.13639)
- [Agreement Metrics for LLM-as-Judge Evaluation: What to Report and Why](https://arxiv.org/html/2606.00093)
- [Autorubric: A Unified Framework for Rubric-Based LLM Evaluation](https://arxiv.org/html/2603.00077v1)
- [Ask, Don't Judge: Binary Questions for Interpretable LLM Evaluation](https://arxiv.org/html/2606.27226v1)
- [A Survey on LLM-as-a-Judge](https://arxiv.org/pdf/2411.15594)
- [Optimal Number of Response Categories in Rating Scales](https://www.researchgate.net/publication/12546546_Optimal_Number_of_Response_Categories_in_Rating_Scales_Reliability_Validity_Discriminating_Power_and_Respondent_Preferences) (Preston and Colman, 2000)
- [Behaviorally Anchored Rating Scale: reliability evidence](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9090385/)
- [G-Eval: the definitive guide](https://www.confident-ai.com/blog/g-eval-the-definitive-guide)
