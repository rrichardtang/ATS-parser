type: prototype (HITL)
status: closed
claimed: claude
blocked-by: 05

# Score from criterion answers

## Question

`score.py` reads `llm_categories[category]` as `(mean, band_low, band_high)` — a mean of
the numbers providers returned, and the spread between them. After 05 there are no
numbers to average. Replace the path.

Per category, per provider sample: criterion answers → band (the lookup from 01) →
the band's value → blended with the rule channel at that category's `rule_share` (03).

## Three things that change meaning, not just shape

1. **Ensembling.** Today two providers' numbers are averaged. Under criteria, two
   providers answer the same questions; what is combined is *answers*, and the natural
   unit is per-criterion agreement, not a mean. Whether disagreeing judges average their
   bands, take the lower, or mark the category contested is a real decision and it is
   **not** inherited from the other map — raise it there if it turns out to be a rubric
   question rather than an implementation one.
2. **The disagreement range.** `score.py:127` widens a category to a low/high range when
   providers differ by 12 or more, noted as *"providers disagreed; shown as a range"*. A
   band gap is not a point gap: on `Production ownership` the smallest possible
   disagreement — one adjacent band — is 17 to 23 points, so the existing threshold
   would fire on every single split. The mechanism and its wording both need revisiting,
   and the other map's open question about a word for this (*contested* is its
   placeholder) lands exactly here.
3. **Withheld categories.** A withheld category is not a zero and not a 100. What it
   does to the composite, and what the report says in its place, has never been
   specified because nothing could withhold before. 05 built the withholding itself:
   `content_pass` returns `meta["withheld"]` naming the five judged categories and
   the reason, and spends no call. `score.build` has not been told, so today the
   three judged categories that have a rule channel ride at 100 on a document whose
   roles never parsed — which is the shape of the bug, ready to be measured.

Also arriving from 05: `ensemble.combine_scores` is no longer reached by the
pipeline, and the unfolded answers are on each `ContentJudgment`, reachable as
`passes.criterion_answers(j.categories)`.

Done when: a category's judged value is a lookup from criterion answers rather than a
number the model chose; the blend uses the per-category `rule_share`; two providers
splitting on a criterion produces something defensible and named; and a withheld
category neither inflates nor deflates the composite.


---

## Resolution

Three decisions, all three taken by the human this ticket's HITL type exists for, against
`prototype/06-criterion-scoring.html`, kept on branch `prototype/06-criterion-scoring`
(it is throwaway, so it does not ride on the default branch). The measurements behind them are
[criterion-scoring.md](../criterion-scoring.md); nothing below re-decides a rubric
question, and the one that turned out to belong to the other map is raised there rather
than answered here.

### 1. Ensembling: the lower band wins

Each judge is banded from **its own** answer set by `rubric.band_of`, and the category
takes the **lower** band where two judges land on different ones. `ensemble.combine_bands`
replaces `combine_scores`; one judge is one `(provider, sample)` reply, not one provider,
so sampling noise and provider disagreement stay the same shape the agreement harness
measures them in.

The ticket asked whether disagreeing judges average their bands, take the lower, or mark
the category contested, and said the answer was not inherited. It is not a rubric
question — it is a question about arithmetic over the lookup the rubric already fixed —
so it was settled here, and the two rejected rules were rejected on measurements rather
than taste:

- **Averaging** puts back the model-authored number 04 removed by construction. Between
  C's 58 and B's 78 there is no band, so 68 is a value no rubric names.
- **Intersecting the answers** — the most literal reading of *"what is combined is
  answers, and the natural unit is per-criterion agreement"* — inverts on `Resume craft`.
  Craft bands on the *count* of criteria met (12), not a ladder of preconditions, so two
  judges who each met three of five but not the same three both say band C and intersect
  to band D. Over all 496 answer-set pairs that is **100 of the 115 pairs where craft's
  judges agree**, against 4 or fewer in each gated category. A rule that holds for four
  categories and inverts on the fifth is not a rule.

Every criterion the judges answered differently rides on `JudgedCategory.split_criteria`
whether or not it moved the band. A split the lookup absorbs is what agreement actually
cost, and 04's claim that criteria are more diagnosable than a label is only checkable
while the absorbed ones are still visible.

### 2. The disagreement range: band adjacency, and two readings rather than two numbers

`score.py:127`'s `band_high - band_low >= 12` is gone, and so is `ensemble.BAND_THRESHOLD`
— the two copies scoring-mechanics.md §1 said should end as one constant end as none. All
five specs share one value ladder (10 / 35 / 58 / 78 / 95), so the narrowest disagreement
the rubric can express is **17 points**: a 12-point test fires on every split there is,
in every category. What replaces it is the quantity the specs define, `gap` in bands.

A contested category **scores the lower band** and names the other one in words:

> Production ownership — contested — the judges read this differently: Built, not
> operated, or Shipped (split on production-ownership/C3)

rather than `41.2–54.4`. The blended endpoints are still on `CategoryScore.low`/`.high`
for anything that wants them, but they sit *beside* the score, never instead of it. The
report's word is still **contested**, still the other map's placeholder: naming it is
that map's [open question](../../rubric-grounding/MAP.md), and this ticket changed the
mechanism under it rather than pre-empting the name.

### 3. A withheld category is not assessed

`score.build` takes `withheld: dict[Category, str]` and marks those categories
`assessed=False` with their reason. The composite renormalises over what was actually
checked, which on a document whose roles did not parse is the parser gate's 25 points.

Not a zero — the parser gate has already found and charged for the defect, and scoring it
again charges one fault twice. Not a constant either: 50 on five categories is a number
nobody measured sitting on 52.5 of the composite's points.

Two details the shape forced:

- **Withholding outranks `assessed`'s self-correcting clause.** That clause exists so a
  category a rule *did* deduct from counts after all; withholding says the criteria have
  no subject on this document, which a stray `slop/*` finding does not make untrue. So it
  is checked first, and a finding in a withheld category reports **0 points** and takes no
  ledger row rather than quoting a cost the composite never paid.
- **Withholding is a property of the document, not of the run.** `pipeline.analyze`
  resolves `passes.withholding_reason(resume)` once, before the provider check, so the
  deterministic-only path is fixed too. Deciding it inside the content pass alone would
  have left the worst composite in the system unfixed for every run without a key.

## Measured

Every fixture, deterministic channel only (`analyze` with no key):

| fixture | roles | withheld | composite before | composite after |
|---|---|---|---|---|
| two_column | 0 | yes | 95.7 | **86.6** |
| hidden_text | 0 | yes | 40.0 | 40.0 (fraud cap) |
| scanned | 0 | yes | 0.0 | 0.0 (unreadable cap) |
| buried_evidence | 1 | no | 90.1 | 90.1 |
| slop / strong / no_phone | 2 | no | unchanged | unchanged |

**This closes an inherited observation.** The map recorded, from 02, that *"`two_column`
outranks `buried_evidence`: a resume no parser can read scores above one that parses
cleanly and buries its evidence, under both rubrics."* It no longer does — 86.6 against
90.1 — and the fix was telling the composite what it was not assessing, not repricing
`parse/multi-column`. What that rule *should* cost is still nobody's decision.

## Left open, and raised where it belongs

- **`_subscore` renormalises over as little as one category.** A withheld document prints
  *human gate 100* off `Title & seniority alignment` alone, the only human-gate category
  a document with no roles can assess. Not invented — Title really did pass — but a
  headline number over 5 of 45 points reads as a verdict it is not. The `unreadable` path
  already special-cases this by zeroing the subscore; withholding wants something less
  blunt, and choosing it is a decision, not an implementation. Recorded on the map.
- **The word for *contested*** stays the rubric-grounding map's, unchanged.
- **The unmet criteria** still ride in `content_pass`'s meta, unread by the report. 06
  scores from answers; where a non-finding renders is the map's other open row.

## Changed

- `ats/models.py` — `JudgedCategory` (the value, both bands, the gap, the splits, and
  why the lower band wins); `CategoryScore.contested`.
- `ats/ensemble.py` — `combine_bands` replaces `combine_scores`; `BAND_THRESHOLD` is
  gone; `PassResult.judged` carries the content pass's second channel.
- `ats/passes.py` — `judge_categories` folds the scoring channel 05 left unfolded;
  `content_pass` fills `judged` and records `contested` and `criterion_splits` in meta.
- `ats/score.py` — `build` blends a band's value, prints the two readings, takes
  `withheld`, and reports no points for a finding in an unassessed category.
- `ats/pipeline.py` — withholding resolved from the document on every path; the interim
  "not wired yet" note is gone; a contested run says so.
- `ats/agreement.py` — `score_judgment` bands a live judgement through the same lookup
  the report uses, keeping the numeric path for pre-05 recordings.
- `templates/report.html` — a contested category shows its score with the two readings
  on the chip, not a range instead of a score.
- `tests/test_scoring.py`, `tests/test_ensemble.py`, `tests/test_llm_passes.py` — the
  lower band wins; an absorbed split is recorded and contests nothing; the intersection
  case that rules intersection out; an incomplete answer set names no band; a withheld
  category is excluded, is not rescued by a deduction, and cannot also carry a judged
  value; two judges splitting reach the report as one contested category.
- `CONTEXT.md` — *contested*, *criterion split* and *withheld* defined.
  `README.md` — pass 1 bands per judge rather than averaging.
