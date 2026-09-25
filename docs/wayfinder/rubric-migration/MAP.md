# Map: Migrating the rubric into the code

`wayfinder:map` — local-markdown tracker. Tickets are files in `tickets/`.
A ticket is **claimed** by setting `claimed: <name>` in its header, before any work.
The **frontier** is every ticket that is `open`, unclaimed, and whose `blocked-by` are all `closed`.

## Destination

The rubric that [rubric-grounding](../rubric-grounding/MAP.md) specified, running in
the program, on real resumes, with its acceptance test measured rather than proxied.

Done when a resume goes through `app.py` and is scored by the new category set from
criterion answers the model actually returned — and the acceptance test has been run
against two providers on documents nobody wrote in order to test it.

**This map decides nothing about what the rubric should be.** Every rubric question
was settled by the other map; where a decision is missing, this map raises it there or
records that it was forced by a code fact. What is open here is sequencing, safety and
whether the thing works.

## Why this is a second map

`rubric-grounding` says in its own Out of scope: *"Implementing the rubric in code. The
destination is the spec; implementation follows."* That map is closed on twelve tickets
and its spec half is complete. Its Destination, though, contains a claim it cannot test
without leaving its own scope — *"such that two different LLM judges scoring the same
resume land within a stated tolerance of each other."* Five categories have measured
verdicts and all five are against the same proxy: a deterministic judge against one
recorded model judge, on documents written to exercise the rubric.

Nothing has run. The specification exists as five JSON files and eight prose documents
in a docs folder; `app.py`, `score.py` and `prompts.py` still score with the five
categories 04 retired. This map is the gap.

## The approach: run both, replace last — and what actually happened

The plan was that the new rubric would be added **beside** the old one, not in place of
it: same resume, both scored, both printed, until the new one had been looked at on real
documents. The reason was the ordering problem the other map ran into — the new rubric
cannot be judged until it runs, and replacing outright makes the first run the moment
the comparison is lost.

**It was not followed, and the map records that rather than quietly restating it.** 03
swapped `models.Category` in place; 04, 05 and 06 built on the swapped enum. The five
retired categories appear nowhere in `ats/`, `scripts/` or `app.py`, so there is no old
path left in the package to run beside the new one. Nobody decided to abandon the approach; each ticket
took the shortest path through its own question and the approach expired underneath
them.

The *before* picture was briefly re-scoped to a **recording** —
[`baseline/run-summary.json`](../rubric-grounding/baseline/run-summary.json), 30 August,
redacted — because the recording no longer loads (`Finding.message` was redacted away
and is required; the old category names no longer resolve) and a recording eight weeks
old cannot tell a rubric effect from a parser change. 07 then took the third way out that
re-scope listed: it runs the old rubric from git history rather than keeping it alive in
the package (see *Decided*, below), so both sides read today's parse of each document
and the drift problem does not arise.

## What exists to migrate

| the spec says | where it lives now | what the program uses |
|---|---|---|
| five judged categories, three carried over | `ats/criteria/*.json` (01) + `04`'s table | **`models.Category`, the new eight (03)** |
| criteria → band → value | `ats/rubric.py:band_of` (01) | **the model answers criteria (05) and the band is what a category scores (06)** |
| `rule_share` per category | `07`'s table in `rule-mapping.md` | **`score.rule_shares()`, read from each spec (03)** |
| weights, four of them derived from the corpus | `derived_weights()` in `ats/jd_dimensions.py`; budget 50 (02) | **`config.category_weights()`: four authored, four derived (03)** |
| a test set worth measuring on | seven fixtures + 36 self-written probes | **30 drawn documents in `corpus/resumes/`, probes kept as a control arm (08)** |
| findings keyed on criterion ids | `findings-identity.md` | **`<slug>/<criterion id>`, from the specs (05)** |
| advice-only findings that deduct nothing | `rule-mapping.md` §2 | **`Finding.advice_only`, fourteen rules (04)** |

## Notes

- **Domain and vocabulary**: `/CONTEXT.md`. `Criterion`, `Band` and `Composite` are
  defined there and this map uses them as defined.
- **The spec documents are the requirement.** Where a ticket and a spec document
  disagree, the spec document wins, or the disagreement goes back to the other map as
  a new ticket there. Implementation is not the place to quietly re-decide a rubric
  question.
- **No provider credentials in the session that opened this map.** `ats/llm.py` reads
  `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` from the environment; neither is set. The
  30 August baseline run had them, so they exist somewhere reachable. Tickets 01–06 and
  08 need none. 07 and 09 do.
- **The test set was thin and nobody had said so before 08.** Seven fixtures, four of
  which carry identical bullets; thirty-six band probes (the ticket's *twenty-nine*
  omits `resume-craft/`'s seven) written by the sessions that were also judging them;
  one real resume. 08 built the replacement: 30 documents drawn from the posting corpus,
  the probes kept as a control arm, real resumes specified and never committed. See
  [acceptance-set.md](acceptance-set.md).

## Decisions so far

- **The rubric is `ats/rubric.py`** (01): the five specs are package data in
  `ats/criteria/`, loaded by `load_spec`, and `band_of` turns a set of criterion
  answers into a band. `leverage` moved with it, because it is a property of the
  lookup rather than of the measurement. The **deterministic judge stays in
  `scripts/criteria_probe.py`**: it answers criteria from regexes in order to measure
  agreement, and in the package it would be a second, unwired rule channel beside
  `ats/rules.py`. The probe prints the same five verdicts it printed before the move.
- **The derived block gets 50 points, split in proportion to document frequency** (02):
  15 / 15 / 12.5 / 7.5, with `Resume craft` 25 and `Parseability` 15, `Structure` 5,
  `Title` 5 unchanged — 04's illustration, adopted. 50 because it holds the authored
  block at today's numbers, so the migration moves one variable; proportional because a
  floor would put an authored constant inside the block whose stated property is
  *derived, never authored*. The measurement is
  [weight-budget.md](weight-budget.md); 03 is where the number lands in code.
- **The seven fixtures cannot validate the behaviour block** (02): `Agentic systems`
  and `AI-assisted coding fluency` are band E on every one of them — 60 recorded
  criterion answers, all `no` — so 22.5 of the composite's points are a constant on
  this test set. It is why every fixture drops ~18 points under the new rubric, and it
  is a fact about the fixtures, not the rubric. 08 is the fix; 09 must not measure
  tolerance here.
- **The new category set is what the program runs** (03). `models.Category` is the new
  eight; every rule carries the category `rule-mapping.md` §1 gives it;
  `cred/no-named-models` is gone (§4); `rule_share` is per-category data read from each
  spec, so 07 §5's zeroes are the specs' own numbers rather than a set literal. The
  authored weights are in `weights.toml` and the derived four are **computed** —
  `weights.toml` deliberately holds no number for them, only the budget, so a
  hand-edit cannot desynchronise one from the corpus.
- **A category no channel reaches is not scored** (03). Both of 04's latent bugs are
  closed and under test: a provider's entry for a category nobody asked about is
  dropped rather than blended, and a judged category with no judge answer and no rule
  channel is excluded from the composite instead of riding in at a permanent 100.
  `CategoryScore.assessed` carries it, and the report prints `n/a`. This is what the
  fixtures' rules-only human-gate score was silently inheriting.
- **A finding carries its own gate, and advice carries no category** (04).
  `Finding.advice_only` findings deduct nothing, never reach the ledger, and print
  under a gate they name themselves — fourteen rules in all: the whole of tool
  coverage (07 §2), `cred/notebook-only` (§3.1), and `content/quantification` and
  `cred/unlinked-projects` (12). `Finding.gate` is a field rather than a lookup from
  the category, which is what lets `Resume craft` hold `scan/*` findings under the
  recruiter and `slop/*` findings under the manager. A craft finding must name its
  gate; everywhere else the category still settles it.
- **The content pass asks the criteria, and a `no` produces one of two objects** (05).
  The prompt is built from the five specs, so the questions a judge answers are the
  same objects `band_of` reads; the model names no band and authors no number. A `no`
  with a quote whose locator resolves against the parsed resume is a **placed
  finding** keyed on `<slug>/<criterion id>`; every other `no` is an **unmet
  criterion**; a `yes` produces neither, because its quote is evidence and not a fix.
  `content_user` lists the locators an answer may name, which is the other half of
  the defence against the baseline's 10% unresolvable ones. The report channel is
  unioned on 10's key of record; the answers themselves are deliberately **not**
  folded, because what a criterion split buys is 06's.
- **A document whose roles did not parse is withheld before any call** (05).
  `passes.withholding_reason` is checked by `content_pass` and by
  `agreement.judge_resume`, so neither the report nor the agreement table carries a
  judged number for `two_column`, `hidden_text` or `scanned` — all three of which
  parse to zero roles. What a withheld category does to the *composite* is untouched
  here and is 06's third item.
- **The lower band wins, and a withheld category is not assessed** (06). Each judge is
  banded from its own answers and the category takes the lower band where two judges
  split; `ensemble.combine_bands` replaces `combine_scores`, and `BAND_THRESHOLD` and
  `score.py`'s duplicate `>= 12` are both gone — all five specs share one value ladder,
  so the narrowest disagreement expressible is 17 points and a 12-point test fires on
  every split there is. Adjacency in bands replaces it. The two rejected rules were
  rejected on measurements ([criterion-scoring.md](criterion-scoring.md)): averaging puts
  back the model-authored number 04 removed, and intersecting the *answers* inverts on
  `Resume craft`, whose band is a count rather than a ladder — 100 of the 115 pairs where
  its judges agree get marked down for a disagreement neither reported. A contested
  category names its two readings rather than printing a range. A **withheld** category
  is excluded from the composite, which renormalises over what was checked, and
  withholding is resolved from the *document* so the deterministic-only path is fixed
  too. Side effect, on the recorded judge only: `two_column` no longer outranked
  `buried_evidence`. Live, it did again (07). **The exclusion is superseded** by
  grounding 13: a withheld category now scores as no evidence.
- **`content/bullet-invariants` is `content/no-outcome`** (04, implementing 12). It
  deducts on one predicate. The other three are priced elsewhere or nowhere —
  ownership in `Production ownership`, measurability nowhere now that
  `content/quantification` is advice — and they survive in the fix text, which costs
  nothing to give.
- **The old rubric is run from git, not kept alive in the package** (07). 03 replaced
  `models.Category` outright, so `scripts/side_by_side.py` materialises the tree at
  **`1418f0a`** — the commit that recorded baseline-agreement.md — and runs it in a
  subprocess. The pin is load-bearing: 02 reads as a documentation ticket and removed
  four `RULE_DIMENSION` entries, so a later commit would have moved the *before*
  picture silently. Three judge channels: recorded (the fixtures), rules-only (any
  document), live (run 25 September on the seven fixtures and the owner's resume).
  [both-rubrics.md](both-rubrics.md).
- **The rubric is measured on a drawn set, and bands are observed rather than
  targeted** (08). Three tiers: 30 invented documents in `corpus/resumes/synthetic/`,
  written from briefs a seeded sampler draws out of `corpus/jds/` before any prose
  exists; real resumes, consented, **never committed** and handled like
  `baseline/run-summary.json`; and the 36 band probes kept as a control arm, because the
  gap between agreement there and agreement on the drawn set measures what a self-written
  test set was buying. Nothing in the sampler names a category, criterion or band, and
  the set freezes on a hash manifest — a document that changes after a judge has read it
  invalidates its numbers silently. The fixtures' defect is closed: all 19
  rule-answerable criteria in the four behaviour categories now vary. What the
  deterministic floor cannot certify is band spread, and that is 09's.
  [acceptance-set.md](acceptance-set.md).

## Inherited, and not to be re-opened here

- The category set and what each measures — `04`.
- The criteria, band lookups and leverage tables for all five — `05`, `11`, `12`.
- Where every deterministic rule files, and which ones stop deducting — `07`.
- What makes two findings the same finding, and what `prompts.py` must emit — `10`.
- That document frequency sets four weights, and the derivation — `04`, `09`.
- `Resume craft` is `Gate.RECRUITER`, and the choice moves no number — `12`.

- **A gate holding a withheld category reports no score** (06, after the fixtures made
  it visible; **superseded** by grounding 13, under which the gate averages the withheld
  categories at their no-evidence value, so `two_column`'s human gate is 15.6). `score._subscore` returns `None` rather than a number, and the report
  prints `n/a`. Measured on the fixtures before the fix: `two_column` printed **human
  gate 100** at composite 86.6, and `hidden_text` printed **human gate 100** at
  composite 40.0 and grade F — in both cases off `Title & seniority alignment` alone,
  5 of the human gate's 80 points, undeducted, standing in for five withheld
  categories. (An earlier note here said 45 points; the human gate is 80 — 5 + 25 +
  15 + 15 + 12.5 + 7.5 — and the wrong figure understated the problem.) The rule is
  deliberately narrower than *any unassessed category*: a judged category with no judge
  answer is a degraded run, already flagged partial, and declining there would take the
  gate away on every deterministic-only run. The `unreadable` path still zeroes both
  subscores outright rather than declining — a prior decision with its own rationale,
  left alone here, though zero is also a claim and `n/a` is arguably the honest answer
  there too.

## Not yet specified

- **`Resume craft`'s rule channel is a constant 0 on realistic documents** (found by
  07). Its deterministic deductions run 120–436 (median 242) over 08's thirty documents
  against a category that floors at 0, so it is floored on 30 of 30 — the same value for
  a good resume and a bad one — and `rule_share` 0.7 then caps the category at **28.5**
  whatever a judge answers, on the heaviest authored weight in the rubric. Inherited
  rather than caused: the old rubric floored `Impact & quantification` on 28 of 30 with
  the same blend. What the migration changed is that the mass is concentrated in one
  category and that category is the heaviest. Either per-occurrence costs need a cap, or
  `rule_share` needs to mean something other than a fixed share when the rule channel
  saturates. The other map's, raised from here.
  **Seen on a real resume** (07's first live run): judged band C (58), scored 17.4, and
  the floor alone costs about 10 composite points, turning a D into an F.
- **`Resume craft` C4 and C5 stop discriminating on full-length documents** (found by
  08). C5 fails a document if *any* bullet is portable and C2 needs an outcome in
  *every* role, so both get strictly harder with length: across all 66 documents that
  exist, C5 is `yes` on 5 of the 36 probes with six bullets or fewer and on 0 of the 30
  with seven or more. The category was calibrated on two-role, four-bullet probes. This
  is evidence for 12's open item that C4 and C5 are not independent, and the repair is
  the other map's. 09 must not fold the two constants into a tolerance verdict without
  saying so.
- **`Agentic systems` can fail the composite tolerance on its own** (raised by 02). At
  `rule_share` 0 (07 §5 — no deducting rule, so no channel to average a disagreement
  down) and weight 15, one C1 split costs 12.8 composite points against a bar of 8. No
  budget fixes it: getting under 8 by weight needs a budget near 31. Either the category
  gets a deducting rule — `jd_dimensions.py` now has an `agentic` dimension it did not
  have when 07 wrote §5, though a dimension is not a rule — or 09 measures the exposure
  and rules on whether it is real. See [weight-budget.md](weight-budget.md) §3.
- **What `parse/multi-column` should cost.** 12 points for a document-wide defect, still
  nobody's decision. The price of the rule itself is untouched.
- **A withheld category costs nothing, so a parse failure outranks a good resume**
  (found by 07's live run). 06 appeared to close 02's inversion: `two_column` at 86.6
  against `buried_evidence` at 90.1, but on the recorded judge. Live, `buried_evidence` is
  65.6 and `strong` 72.4, because both providers mark the behaviour block down on every
  readable document. `two_column` escapes it: its roles do not parse, all five judged
  categories are withheld, and the composite renormalises over the three it checked.
  It ranks first of the seven fixtures, 14.2 above `strong`. **Decided in grounding
  13**: a withheld category scores what its spec gives a document with every criterion
  `no` (band E, 10). `two_column` is 29.1 and ranks sixth of seven. The move is
  deterministic, so it is measured without a live run.
- **`Production ownership` C4 is where the providers disagree** (found by 07). Six
  one-band splits in 25 live category readings, four of them `Production ownership`,
  three of those on C4. 09 should report agreement per criterion, not only per
  category, or this will read as a category-wide tolerance problem.
- **What the report does with an unmet criterion.** 05 produces them — one per
  criterion per resume, carrying the absence the candidate most needs to hear — and
  stops there, because nothing in the report renders a non-finding today. They ride
  in `content_pass`'s meta, unread. This is the same undecided question as the row
  below, arriving from the other side.
- **How much of the old report survives.** `report.py` groups by gate and prints a
  ledger of what each finding cost. Advice-only findings cost nothing and still need
  printing, and the old map's `07` says they need a gate and no category. Whether that
  is a new section, an existing one, or a flag on a row is undecided.
- **A word for a contested score.** Inherited open question from `03`. The *mechanism*
  is settled by 06 — band adjacency, the lower band scoring, both readings named — so
  what is left is only the word, and it is the other map's to choose. *Contested* is
  still the placeholder, now in `/CONTEXT.md` and in the report.
- **What happens to the rewrite pass.** Pass 3 reads findings and rewrites bullets.
  Findings keyed on criterion ids change what it is handed. Not looked at yet.
- **Whether the acceptance test's bar survives contact.** *Two providers within 5 points
  per category* was set against a rubric that emitted numbers. Under a band lookup the
  smallest possible disagreement is one band, which on `Production ownership` is 17–23
  points. The bar may need restating in bands rather than points — a question for the
  other map, raised from here, once 09 has a number.

## Out of scope

- Changing any rubric decision. See *Inherited*, above.
- The parser and the deterministic rule set, except where a rule's disposition changes
  because `07` said so.
- The web UI beyond what printing a second score requires.
