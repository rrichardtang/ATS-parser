# Map: Grounding the rubric in the JD corpus

`wayfinder:map` — local-markdown tracker. Tickets are files in `tickets/`.
A ticket is **claimed** by setting `claimed: <name>` in its header, before any work.
The **frontier** is every ticket that is `open`, unclaimed, and whose `blocked-by` are all `closed`.

## Destination

A rubric specification for the content pass: a category set grounded in what the
target job descriptions actually require, where each category defines its score
bands in concrete evidence terms — such that two different LLM judges scoring the
same resume land within a stated tolerance of each other.

This map produces the **spec and the decisions behind it**. Implementing it in
`ats/prompts.py`, `ats/score.py` and the digest pipeline is a separate effort.

## Spec so far

- [production-ownership-criteria.md](production-ownership-criteria.md) — the first
  category's criteria and its band lookup (05).
- [production-ownership-agreement.md](production-ownership-agreement.md) — what they
  measured, and the verdict on the format (05).
- [criteria/](criteria/) — the criteria as data, the band probes, and the recorded
  judge answers the measurement ran on.
- [findings-identity.md](findings-identity.md) — what makes two findings the same
  finding, and what `prompts.py` has to emit for it (10).
- [baseline-agreement.md](baseline-agreement.md) — the first real two-provider run,
  against the rubric still in the code. The *before* picture every change is judged
  from, with [baseline/run-summary.json](baseline/run-summary.json) so its arithmetic
  stays checkable.

## Notes

- **Domain**: resume scoring against AI-engineering job postings. Glossary in `/CONTEXT.md`.
- **Corpus inventory**: `inventory.md` — what the six postings require, in their own
  language. **Scoring mechanics**: `scoring-mechanics.md` — what the model authors today
  (40.5 of the composite's 100 points, across five of eight categories) and the three
  code facts 04/05/06 will hit.
- **The acceptance test is runnable**: `scripts/agreement_harness.py` (06). Judge a
  category set or a band draft with a sweep before and after, not by argument.
- **The noise floor is not adjustable.** `temperature` never reaches either current
  model — `weights.toml`'s own comment says so — which makes the within-judge spread
  each provider's default sampling. 06's addition is what that means for the test:
  between-judge spread has to clear the floor, and the floor cannot be lowered to
  help it.
- **Skills every session should consult**: `grilling` and `domain-modeling` by default;
  `research` for AFK reading tickets; `prototype` for tickets that need something concrete
  to react to.
- **Acceptance test** (restated by 03, now that the model emits a band rather than a
  number): per category, two providers must name the **same band**; one adjacent-band
  disagreement per resume is a pass that wants another look, and any non-adjacent
  disagreement — or more than one adjacent — is a failure. The **5 points / above 8 fails**
  bar survives as the composite-level statement. Measured on all seven fixtures in
  `tests/fixtures/` plus the user's real resume, sampling twice per resume per provider so
  sampling noise is separable from genuine provider disagreement. Per 08, a
  chance-corrected statistic is reported beside the raw agreement: judges agreeing on a
  band nearly every resume lands in is a coincidence, not a rubric.
- **Evidence rule**: every category must be scoreable from observable evidence in the
  resume. A category no judge can point at evidence for is what produces a 22-point spread.
- Corpus is personal data (`corpus/jds/user/`), six verbatim postings.
- **Execution rides in `task` tickets only.** This map plans; the two tickets that
  build are both `task`, which is the type that does rather than decides:
  [Build the inter-judge agreement harness](tickets/06-build-the-agreement-harness.md),
  because 05 cannot be verified by argument, and
  [Teach the dimension scan the behaviours the categories name](tickets/09-derive-category-weights-from-the-corpus.md),
  because 04 made category weight a corpus derivation the digest cannot yet compute.
  Everything else about implementation stays out of scope.

## Decisions so far

- **Destination named**: the deliverable is a rubric spec, not an implementation.
- **Agreement is the bar**: two judges must land in the same place on every category, and
  within 5 composite points, >8 fails. A rubric that cannot hit this is not a good rubric,
  whatever it reads like. (The per-category half of this was a point tolerance until 03
  replaced the model's number with a band; see the acceptance test above.)
- **Categories are replaced, not evolved**: the current five (`Impact & quantification`,
  `AI/ML relevance & depth`, `Credibility & verifiability`, `Recruiter scan`,
  `Writing quality`) are not a starting point. The new set is derived from what the
  postings actually ask for.
- **Discrete levels are the precondition** (08): 0–100 is the worst-performing scale
  tested, judges quantize a fine scale into ~20 buckets whatever range they are given,
  and reliability peaks at 7–10 categories. Sources are named but were unopened — see
  `anchored-rubrics.md` — so the numbers are leads, not settled. This is the evidential
  basis 03 rests on.
- **The model authors no number** (03): it names one **band** per category and cites the
  evidence placing it there; the band's value is a rubric lookup. Findings-only was
  rejected on arithmetic — a finding count is unbounded and unanchored, so two judges
  splitting the same defects 3 ways vs 7 move the composite 34 points, against 2.9 for the
  worst score spread observed. Continuous movement comes from the deterministic rules
  (zero inter-judge variance); the band supplies placement.
- **One opinion, one channel** (03): findings from the model are evidence for the band and
  the fix list, and no longer deduct. Band definitions must therefore be phrased as
  evidence *present*, not defects *found*, or the double count returns.
- **Stable bands, living inputs** (provisional): band definitions are prose that changes
  only on deliberate revision; the corpus supplies which skills get checked. Revisited
  only if future postings consistently clash with the bands.
- **The category set** ([Design the category set](tickets/04-design-the-category-set.md)): five
  judged categories — **Production ownership** (6/6), **Agentic systems** (6/6),
  **Evaluation rigour** (5/6), **AI-assisted coding fluency** (3/6) and **Resume
  craft** — plus the three deterministic categories unchanged. Separability decides
  what exists; document frequency decides what it is worth. `Coverage` dissolves into
  the behaviours; cross-functional collaboration stays out at 6/6 on the sentence-shape
  collision `jd_dimensions.py` already records.
- **The judge answers criteria, not bands** ([Design the category
  set](tickets/04-design-the-category-set.md)): binary, individually quotable evidence
  questions, each with the quote that settles it. The band is a lookup from the
  criteria and the score a lookup from the band — the output-form decision taken to
  the limit it explicitly sanctioned.
- **Category weight is corpus-derived** ([Design the category
  set](tickets/04-design-the-category-set.md)): document frequency sets the weight of
  the four behaviour categories; the other four stay authored, having no df to derive
  from. So `dimension_multiplier()` retires for its four double-counting rules and
  keeps only `title/seniority-mismatch`, whose category keeps an authored weight.
- **`rule_share` is a claim, per category** ([Design the category
  set](tickets/04-design-the-category-set.md)): 0.7 Resume craft, 0.4 the behaviour
  categories, **0** for AI-assisted coding fluency — the first model-owned category,
  because only a brittle proper-noun list could give it a rule channel. Two facts
  found: 0.7 reaches only `Recruiter scan` in normal operation (though nothing filters
  a provider's response, so the other two members of its set are not inert by
  construction), and a category with no rules blends against a constant 100, not a
  channel.
- **Criteria work, and their cost is positional** ([Draft score bands for one
  category](tickets/05-draft-bands-for-one-category.md)): `Production ownership` written
  as five binary criteria and a band lookup measured **53/55 criterion answers
  identical, 10 exact bands, 1 adjacent, 0 far → LOOK** between a deterministic judge
  and a model judge over eleven documents. 04's criteria-are-more-diagnosable claim
  holds and does real work: the two splits are indistinguishable at band level and need
  opposite fixes — one a vocabulary gap in the criterion, one a channel defect no regex
  can fix. And a criterion costs what its *position in the lookup* costs, not what it
  costs to answer: the gate criterion moves the band from all 32 answer sets, while the
  most judgment-laden one moves it from 2 and never by more than a band. Spend the
  wording budget on the gate. Every category needs its own leverage table, and one whose
  gate is its hardest question will not converge however it is worded.
- **A category is withheld, never guessed, where the parse cannot carry it** (05).
  Every criterion asks about a bullet inside a role, so on a document whose roles did
  not survive extraction the judges disagree about what the document is rather than
  about the rubric — and the parser gate has already found and charged for that defect.
- **The fixture set cannot exercise a content rubric** (05). Four of the seven carry the
  same bullets, three carry almost nothing, and every one that can be answered lands at
  one end of the ladder — three of five bands unreachable. 05 wrote seven band probes
  (`criteria/probes/`) for the boundaries; they test the rubric, not the parser, so they
  are text rather than PDFs and live outside `tests/fixtures/`.
- **The old rubric's failure is mostly calibration** ([baseline-agreement.md](baseline-agreement.md)):
  the first real run puts openai above anthropic in **34 of 35** category-resume cells,
  mean **+18.0**, while the two rank resumes almost identically (Spearman 0.75–0.96) —
  and their written justifications for cells 19 points apart say the same thing in
  different words. The disagreement is about turning a shared reading into a number,
  which is the one failure mode 04's output form removes by construction. Removing each
  category's offset still leaves **7.9 points** on average, so the offset is about half
  the problem, not all of it; that residual sits on top of readings that already agree.
  Two smaller findings: `rule_share` 0.7 *masks* `Recruiter scan`'s disagreement rather
  than resolving it, and 03's no-deduct column widened the composite spread on 5 of 6
  resumes — a datum 03 did not have.
- **A finding is the evidence for one criterion** ([What makes two findings the same
  finding](tickets/10-what-makes-two-findings-the-same-finding.md), spec in
  [findings-identity.md](findings-identity.md)): the content model gets no findings
  vocabulary of its own — `rule_id` becomes the criterion id, ~25 fixed strings, and the
  108 names the judges invented for 198 findings become a design-time input for wording
  criteria rather than a runtime output. A criterion answered `no` yields an **unmet
  criterion** (a pure absence: no quote, no locator, one per criterion per resume, what
  the band reads and the report leads with) or a **placed finding** (present-but-weak
  text: quote and locator required), split on whether there is anything to point at.
  Locators are resolved against the parsed resume, not trusted — 10% of the baseline's
  named nothing that exists.
- **Raw finding overlap is not agreement** (same ticket): a resume has 5–9 bullets plus
  the summary and each judge flags 4–11, so the tempting `locator` key's **0.51** sits
  *below* its 0.58 chance line (kappa −0.16, negative on 6 of 7 resumes) and the
  `(rule_id, locator)` key's 0.03 is kappa −0.48. `ats/agreement.py` and
  `scripts/baseline_analysis.py` now print `chance` and `kappa` beside every `between`,
  which is 08's chance-correction requirement reaching the findings table. The
  baseline's "the judges agree on about half the places" is corrected there.
- **The bar can be measured** (06): [Build the inter-judge agreement harness](tickets/06-build-the-agreement-harness.md)
  — `scripts/agreement_harness.py` runs the corpus past both providers twice with the
  samples kept apart, and prints between-judge spread, within-judge spread and
  Krippendorff's alpha per category, plus the composite against the 5 / >8 bar and
  findings agreement under each candidate key with its chance line (10). It reads a number, a band, or
  both, so it measures today's prompt and 05's experiment without a change. Its
  refusals carry the point: alpha is `n/a` rather than 1.00 where no resume varies,
  no between-judge figure is printed with one judge, and a composite pinned by a cap
  is marked rather than counted as agreement.

## Not yet specified

- **Whether the acceptance test has ever passed on the rubric being designed.** It has
  been run once, against the rubric still in the code, and failed —
  [baseline-agreement.md](baseline-agreement.md). The new one has never been run: it
  needs criteria for the other four categories, a prompt that emits them, and a harness
  that reads criterion answers rather than `score` and `band`. 05 measured a two-judge
  proxy and says so.
- **Whether the criteria can carry the report as well as the score.** 10 made the
  criteria the only vocabulary the content model has, so a defect no criterion asks
  about is now unreportable — and a category with no criteria at all is silence rather
  than a vague score, which is what turns 11 from tidy-up into the critical path. 04 chose categories on separability and document frequency;
  exhaustiveness over defects is a demand neither 04 nor 05 was asked to meet, and it is
  the likeliest reason 10 gets reopened. The baseline names what the judges keep
  reaching for — evaluation methodology, deployment reach, scale/latency/cost — so the
  remaining criteria have a target to hit.
- ~~**Criteria for the other four categories.**~~ Now tracked, and it was the largest
  untracked piece of work on the map:
  [Criteria for the three remaining behaviour categories](tickets/11-criteria-for-the-three-remaining-behaviour-categories.md)
  and [Criteria for Resume craft](tickets/12-criteria-for-resume-craft.md). Split
  because 05 predicts `Resume craft` will not converge and the other three should not
  wait on it. 11 takes `AI-assisted coding fluency` **first** per 05 — `rule_share` 0
  means criterion agreement is the only agreement it has, so nothing masks a bad
  criterion — then `Evaluation rigour`, then `Agentic systems`.
- **03's second experiment** — band-only versus band-plus-a-point-inside-it. Specified
  in `production-ownership-criteria.md`, one prompt variant and one harness run, not
  yet executed.
- **C5's wording.** `Production ownership`'s ownership criterion asks about the
  destination bullet, so a resume that hedges the ship and then evidences sole
  operation of the live system answers `no`. Left open by 05 rather than patched,
  because resolving it needs the second judge 06 supplies.

- **A new word for the report's "banded"**. 03 leaves **band** meaning only what
  `/CONTEXT.md` defines it as, so the display of two judges disagreeing needs its own
  term — *contested* is the placeholder.
- **When the rubric gets revised.** Deferred: the trigger is "future inputs consistently
  clash with the rubric", which isn't yet a testable condition.
- **Nice-to-have bonus mechanics.** Nice-to-haves should add "a slight bonus" to coverage;
  how much, and whether it can compensate for a missing requirement, is unspecified.
- **Which gate `Resume craft` belongs to.** It merges `Recruiter scan`
  (`Gate.RECRUITER`) with `Writing quality` (`Gate.MANAGER`) and must pick one.
  `report.py` groups findings by gate and `score.py` derives the parser and human
  sub-scores from it, so this moves visible output. A reporting question, not a rubric
  one, which is why 04 left it — carried by
  [12](tickets/12-criteria-for-resume-craft.md), the ticket with the context to close it.
- **The weight arithmetic.** 04 fixed the principle (df sets the derived block, the
  rest is authored) but not the numbers: how the 100 points split between the derived
  and authored blocks, and whether df maps to weight proportionally or through tiers.
- **Whether the slop pass folds into a quality category** or stays a separate pass with
  its own findings.
- **How the spec migrates into code** without a flag day: the composite, the ledger and
  the report all read today's five categories.

## Out of scope

- Implementing the rubric in code. The destination is the spec; implementation follows.
- Pass 3 (rewrite generation) and its judge/polish machinery.
- The report UI and score-derivation rendering.
- The deterministic rule set (`ats/human.py`, `ats/keywords.py`) except where a new
  category demonstrably overlaps it — see ticket 07.
