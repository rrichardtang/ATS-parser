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
`ats/prompts.py`, `ats/score.py` and the digest pipeline is a separate effort, and it
is now a separate map: [rubric-migration](../rubric-migration/MAP.md).

**One clause of that destination cannot be tested from inside this map.** *Two judges
within a stated tolerance* needs a prompt that emits criterion answers and a harness
that reads them, which is implementation. All five categories have verdicts and all
five are the same proxy — a deterministic judge against one recorded model judge, on
documents written to exercise the rubric. The real number is
[rubric-migration 09](../rubric-migration/tickets/09-run-the-acceptance-test.md).

## Spec so far

- [production-ownership-criteria.md](production-ownership-criteria.md) — the first
  category's criteria and its band lookup (05).
- [production-ownership-agreement.md](production-ownership-agreement.md) — what they
  measured, and the verdict on the format (05).
- [ai-assisted-coding-fluency-criteria.md](ai-assisted-coding-fluency-criteria.md),
  [evaluation-rigour-criteria.md](evaluation-rigour-criteria.md) and
  [agentic-systems-criteria.md](agentic-systems-criteria.md) — the other three
  behaviour categories' criteria and band lookups (11).
- [three-categories-agreement.md](three-categories-agreement.md) — what those three
  measured, every category's leverage table, and the check on whether the criteria can
  carry the report as well as the score (11).
- [resume-craft-criteria.md](resume-craft-criteria.md) — the fifth category's criteria,
  the count lookup that replaces the ladder, and rulings on 07's three conditional
  rules (12).
- [resume-craft-agreement.md](resume-craft-agreement.md) — what it measured, and why a
  category with no gate is held to a harsher bar (12).
- [ats/criteria/](../../../ats/criteria/) — the criteria as data. The migration map's
  01 moved the five specs into the package, where the program can load them;
  [criteria/](criteria/) keeps the band probes and the recorded judge answers the
  measurement ran on.
- [findings-identity.md](findings-identity.md) — what makes two findings the same
  finding, and what `prompts.py` has to emit for it (10).
- [rule-mapping.md](rule-mapping.md) — where every deterministic rule files under the
  new categories, which ones stop deducting, and the collisions found (07).
- [dimension-scan.md](dimension-scan.md) — the behaviour scan that computes 04's
  category weights, the phrase behind every count, and how it is kept from
  overfitting to six postings (09).
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
  because 04 made category weight a corpus derivation the digest could not compute.
  Both are now closed.
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
- **The format generalises, and its proxy does not** ([Criteria for the three remaining
  behaviour categories](tickets/11-criteria-for-the-three-remaining-behaviour-categories.md)):
  `Evaluation rigour` **54/55 criterion answers, 11 exact bands → PASS**; `Agentic
  systems` **54/55, 10 exact, 1 adjacent → LOOK**, both transferring `Production
  ownership`'s lookup shape and leverage table unchanged. `AI-assisted coding fluency`
  is **unmeasured**: its C5 cannot be answered by a rule channel at any wording — as an
  alias family it fired on "eval harness" and "Helped the team" — so the deterministic
  judge abstains and 05's two-judge proxy has only one judge. `rule_share` 0 was 04's
  decision about scoring; this is what it costs the measurement, and it is the strongest
  case on the map for provider credentials.
- **A category whose subject cannot be absent gets a different lookup** ([Criteria for
  Resume craft](tickets/12-criteria-for-resume-craft.md)): the gated shape assumes band
  E means *the evidence is not there*, and craft is never absent — every resume is
  written somehow — so `Resume craft`'s band is the **number of criteria met**, with no
  gate. The consequence is the whole of its cost: leverage is uniform at 30/32 and one
  band, so there is nowhere cheap to disagree, and **two criterion splits anywhere is a
  failure** where a gated category survives two. Measured **54/55, 10 exact, 1 adjacent →
  LOOK**, which is the best result short of perfect on that scale. 05 predicted this
  category would not converge; it converged as well as `Agentic systems` and better than
  `Production ownership`, and 05's stated reason — that craft is weighed rather than
  pointable — is not what makes it hard. The lookup shape is.
- **Separability bites inside a criteria set, not only between categories** (12). The one
  split is `Resume craft` C4 against C5: when every bullet could be anyone's, *"do the
  roles read as different jobs"* has no answer, and the rule channel's token overlap says
  yes while a reader says no. 04 and 08 both name separability as the agreement lever and
  both apply it between categories. Left unpatched on 05's precedent, because a criterion
  fixed against the judge that found the problem measures nothing.
- **The band lookups are data, not code** (11). Each band declares a `when` clause and
  `band_of` evaluates them in order; four hand-written lookups would have been four
  totality arguments nobody could check by reading. Every property 05 pinned for one
  category is now parametrised over all four, so the fifth inherits the suite by
  existing.
- **10 does not get reopened** (11). Grouped by the reading behind the name, the
  baseline's 198 findings all land on a criterion, a deterministic rule, or `Resume
  craft` — nothing recurring is unreportable, and no criterion was added to make that
  true. Two readings land outside the three behaviour categories: "activity, not
  outcome" (18 findings) rides on 12 authoring a criterion that
  `content/bullet-invariants` answers, and "missing role or product context" is held by
  `invariants.py`'s Mechanism check. Caveat carried: the baseline ran the *old* prompt's
  open-ended question, so this is evidence about what judges reach for, not about what
  these criteria surface.
- **A category is withheld, never guessed, where the parse cannot carry it** (05).
  Every criterion asks about a bullet inside a role, so on a document whose roles did
  not survive extraction the judges disagree about what the document is rather than
  about the rubric — and the parser gate has already found and charged for that defect.
- **The fixture set cannot exercise a content rubric** (05). Four of the seven carry the
  same bullets, three carry almost nothing, and every one that can be answered lands at
  one end of the ladder — three of five bands unreachable. 05 wrote seven band probes
  (`criteria/probes/`) for the boundaries; they test the rubric, not the parser, so they
  are text rather than PDFs and live outside `tests/fixtures/`. 11 wrote 22 more, one
  set per category, and two of them are written to fail rather than pass.
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
- **Every rule files, and tool coverage stops deducting** ([Which category does each
  keyword rule file into](tickets/07-which-category-does-each-keyword-rule-file-into.md),
  spec in [rule-mapping.md](rule-mapping.md)): three dispositions — deducts against a
  named category, fires as advice with no cost, or retired. All three `jd/*` rules, the
  seven `kw/thin-*` and `kw/unsupported-skills` become advice-only, because no category
  measures nouns, because 02's disjunction defect is structural rather than a bug (df
  over terms cannot express *"Python, Go, or TypeScript"*), and because the advice
  survives without the number — 03's move one layer down. `cred/no-named-models` is
  retired outright; C2 owns naming and 05 measured that no regex can answer it.
- **Cross-channel is a blend, within-channel is a sum** (same ticket): a rule answering
  the same question as a criterion is the design — `rule_score * share + band * (1 -
  share)` averages, it does not double-charge — while `deductions[category] += cost`
  adds. Three real collisions found and resolved on *one property, one deducting rule*:
  `cred/no-production`/`cred/notebook-only` cannot fire apart (both require
  `not PRODUCTION_RE`), `content/quantification`/`content/bullet-invariants` are the same
  `measurability` predicate, and `invariants.ownership` is literally
  `content/ownership`'s regex — the last of these priced one defect in two categories.
  The test 11 and 12 inherit is on *evidence*, not category.
- **`rule_share` > 0 requires at least one deducting rule** (same ticket): `Agentic
  systems` has neither a rule nor a dimension, so at 0.4 it would blend against a
  constant 100 and never score below 40 — 04's latent mechanism, reached. It drops to
  **0**, making three of five judged categories model-owned where 04 had one. A
  dimension for it (09) is now worth building for the channel, not only for the weight.
- **The weights are computed, not transcribed** ([Teach the dimension scan the
  behaviours the categories name](tickets/09-derive-category-weights-from-the-corpus.md),
  record in [dimension-scan.md](dimension-scan.md)): `jd_dimensions.py` reproduces 02's
  four hand-read counts exactly — 6/6, 6/6, 5/6, 3/6 — from eight behaviour dimensions,
  four of them new, and every hit fires on the sentence `inventory.md` quotes for that
  posting. Categories are unions of dimensions, so the count weight derives from is
  computed per category at build time (`category_document_frequency` in the digest) and
  cannot be summed from the per-dimension totals. `derived_weights` takes the point
  budget as a parameter, because 04 left that number authored. A seventh posting moves
  the weights with no file edited, which is demonstrated rather than asserted.
- **Patterns are families, not sentences** (same ticket): the guard against fitting six
  postings is that each pattern is a verb set crossed with an object set, with the ship
  and destination families shared across dimensions, and that the tests attack from both
  ends — verbatim corpus text on one side, phrasings that appear nowhere in the corpus
  on the other, plus a posting that must hit nothing. The residual risk is a false
  negative on a behaviour phrased in words no family anticipated, which is the same
  defect family as 01 and 02 and will not be the last of it.
- **`dimension_multiplier()` survives with an effect no user can see** (same ticket):
  the four double-counting entries are gone and a test now asserts they return exactly
  1.0. The survivor, `title/seniority-mismatch`, sits in a category weighted 5 of 100,
  so the mechanism's largest possible composite movement is **0.05 points** — under the
  report's own rounding. Kept because 04 kept the entry deliberately; recorded as the
  case for retiring the mechanism.

## Not yet specified

- **Whether the acceptance test has ever passed on the rubric being designed.** It has
  been run once, against the rubric still in the code, and failed —
  [baseline-agreement.md](baseline-agreement.md). The new one has never been run, and
  after 11 and 12 the criteria are no longer what is missing: what remains is a prompt
  that emits criterion answers and a harness that reads them rather than `score` and
  `band`. Five recorded-verdict sets now exist in the shape 06 would have to emit. 05,
  11 and 12 all measured the same two-judge proxy and all say so. **`Resume craft` is
  where the real run should be expected to fail first** — its count lookup gives it no
  cheap seats, so it fails at two criterion splits where a gated category survives them.
- **Whether the criteria can carry the report as well as the score.** 10 made the
  criteria the only vocabulary the content model has, so a defect no criterion asks
  about is now unreportable — and a category with no criteria at all is silence rather
  than a vague score, which is what turns 11 from tidy-up into the critical path. 04 chose categories on separability and document frequency;
  exhaustiveness over defects is a demand neither 04 nor 05 was asked to meet, and it is
  the likeliest reason 10 gets reopened. 11 checked the three behaviour categories
  against the baseline and found nothing recurring unreportable; 12 closed the remainder
  by authoring `Resume craft` C2 for the "activity, not outcome" reading (18 findings)
  and C3 for "what was the work for" (8 findings, and nothing in the repository had ever
  checked it). **Every recurring baseline reading now has a criterion or a rule.** The
  caveat 11 recorded stands: the baseline ran the old open-ended prompt, so this should
  be repeated on the first run of the new one.
- ~~**Criteria for the other four categories.**~~ All five judged categories now have
  criteria, a total and monotone lookup, a leverage table, band probes and a measured
  verdict — [11](tickets/11-criteria-for-the-three-remaining-behaviour-categories.md) and
  [12](tickets/12-criteria-for-resume-craft.md), both closed. 07's three conditional rules
  are ruled on: `content/bullet-invariants` deducts on one predicate and is no longer a
  bundle, `content/quantification` and `cred/unlinked-projects` become advice-only.
  **The spec's rubric half is complete; what is unbuilt is the measurement and the
  migration.**
- **03's second experiment** — band-only versus band-plus-a-point-inside-it. Specified
  in `production-ownership-criteria.md`, one prompt variant and one harness run, not
  yet executed.
- **C5's wording.** `Production ownership`'s ownership criterion asks about the
  destination bullet, so a resume that hedges the ship and then evidences sole
  operation of the live system answers `no`. Left open by 05 rather than patched,
  because resolving it needs the second judge 06 supplies.
- **Two alias families that a criterion's prose rules out and its regex cannot** (11).
  `Agentic systems` C3 answered yes off `ticket` inside *a ticket-triage agent*, and
  `Evaluation rigour` C5's alias list does not know "before each release". Both are the
  vocabulary-versus-channel distinction 05 named, and both are cheap to fix — but only
  worth fixing once 09 decides whether these categories get a rule channel at all.

- **A new word for the report's "banded"**. 03 leaves **band** meaning only what
  `/CONTEXT.md` defines it as, so the display of two judges disagreeing needs its own
  term — *contested* is the placeholder.
- **When the rubric gets revised.** Deferred: the trigger is "future inputs consistently
  clash with the rubric", which isn't yet a testable condition.
- **Nice-to-have bonus mechanics.** Nice-to-haves should add "a slight bonus" to coverage;
  how much, and whether it can compensate for a missing requirement, is unspecified.
- **The weight arithmetic.** 04 fixed the principle (df sets the derived block, the
  rest is authored) and 09 supplies the input and a proportional derivation, but the
  budget is still authored: how many of the 100 points the derived block gets, and
  whether proportional or tiered is the right map from df to weight. 09 takes the budget
  as a parameter rather than choosing for it.
- ~~**How the spec migrates into code**~~ — now tracked on its own map,
  [rubric-migration](../rubric-migration/MAP.md), which takes the approach of running
  both rubrics side by side and retiring the old one last. It also opens the one
  question neither map had a ticket for: **the rubric has been validated almost entirely
  on documents written by the sessions validating it** — seven fixtures, twenty-nine
  self-authored band probes, one real resume. That is
  [rubric-migration 08](../rubric-migration/tickets/08-where-the-real-resumes-come-from.md),
  and it is unblocked from the start because no amount of software finishes it.
  The original note, for the record: the composite, the ledger and
  the report all read today's five categories. 07 adds three mechanical
  asks: a `deducts` flag (or an equivalent ledger exclusion), advice-only findings
  grouped by gate rather than category, and the `rule_share` invariant asserted where a
  test can see it. 12 adds one more and settles a question: `content/bullet-invariants`
  now deducts on a single predicate and should be renamed rather than left reading as a
  bundle; and the gate question is answered — `Resume craft` is `Gate.RECRUITER`, which
  moves **no number** (`score.py:161` takes the union of `RECRUITER` and `MANAGER`, so
  only `PARSER` versus the rest is load-bearing) and is read by nothing at all once
  findings carry their own gate.

## Out of scope

- Implementing the rubric in code. The destination is the spec; implementation follows,
  on [rubric-migration](../rubric-migration/MAP.md).
- Pass 3 (rewrite generation) and its judge/polish machinery.
- The report UI and score-derivation rendering.
- The deterministic rule set (`ats/human.py`, `ats/keywords.py`) except where a new
  category demonstrably overlaps it — settled by
  [07](tickets/07-which-category-does-each-keyword-rule-file-into.md), which changed
  which rules deduct but wrote no new ones.
