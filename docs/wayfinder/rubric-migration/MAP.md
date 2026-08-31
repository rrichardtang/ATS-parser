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

## The approach: run both, replace last

The new rubric is added **beside** the old one, not in place of it. Same resume, both
scored, both printed, until the new one has been looked at on real documents.

The reason is the ordering problem the other map ran into: the new rubric cannot be
judged until it runs, and replacing outright makes the first run the moment the
comparison is lost. [baseline-agreement.md](../rubric-grounding/baseline-agreement.md)
is a recorded *before* picture; a side-by-side is the *after*, on the same documents,
with nothing to reconstruct. Retiring the old path is the last ticket, not the first.

## What exists to migrate

| the spec says | where it lives now | what the program uses |
|---|---|---|
| five judged categories, three carried over | `ats/criteria/*.json` (01) + `04`'s table | **`models.Category`, the new eight (03)** |
| criteria → band → value | `ats/rubric.py:band_of` (01) | nothing; the model emits a number |
| `rule_share` per category | `07`'s table in `rule-mapping.md` | **`score.rule_shares()`, read from each spec (03)** |
| weights, four of them derived from the corpus | `derived_weights()` in `ats/jd_dimensions.py`; budget 50 (02) | **`config.category_weights()`: four authored, four derived (03)** |
| findings keyed on criterion ids | `findings-identity.md` | `passes.py` mints an id from model text |
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
- **The test set is thin and nobody has said so before now.** Seven fixtures, four of
  which carry identical bullets; twenty-nine band probes written by the sessions that
  were also judging them; one real resume. A rubric validated on documents written by
  its validators is weakly validated, and that gap will not close by thinking harder —
  it is ticket 08, and it is unblocked from the start for that reason.

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
- **`content/bullet-invariants` is `content/no-outcome`** (04, implementing 12). It
  deducts on one predicate. The other three are priced elsewhere or nowhere —
  ownership in `Production ownership`, measurability nowhere now that
  `content/quantification` is advice — and they survive in the fix text, which costs
  nothing to give.

## Inherited, and not to be re-opened here

- The category set and what each measures — `04`.
- The criteria, band lookups and leverage tables for all five — `05`, `11`, `12`.
- Where every deterministic rule files, and which ones stop deducting — `07`.
- What makes two findings the same finding, and what `prompts.py` must emit — `10`.
- That document frequency sets four weights, and the derivation — `04`, `09`.
- `Resume craft` is `Gate.RECRUITER`, and the choice moves no number — `12`.

## Not yet specified

- **`Agentic systems` can fail the composite tolerance on its own** (raised by 02). At
  `rule_share` 0 (07 §5 — no deducting rule, so no channel to average a disagreement
  down) and weight 15, one C1 split costs 12.8 composite points against a bar of 8. No
  budget fixes it: getting under 8 by weight needs a budget near 31. Either the category
  gets a deducting rule — `jd_dimensions.py` now has an `agentic` dimension it did not
  have when 07 wrote §5, though a dimension is not a rule — or 09 measures the exposure
  and rules on whether it is real. See [weight-budget.md](weight-budget.md) §3.
- **`two_column` outranks `buried_evidence`** (observed by 02, inherited not caused): a
  resume no parser can read scores above one that parses cleanly and buries its
  evidence, under both rubrics. `parse/multi-column` costs 12 points for a
  document-wide defect. Nobody has decided what it should cost.
- **How much of the old report survives.** `report.py` groups by gate and prints a
  ledger of what each finding cost. Advice-only findings cost nothing and still need
  printing, and the old map's `07` says they need a gate and no category. Whether that
  is a new section, an existing one, or a flag on a row is undecided.
- **A word for a contested score.** Inherited open question from `03`: `score.py:127`
  currently widens a category to a range when providers disagree by 12 or more, and
  calls it *"providers disagreed; shown as a range"*. Under criteria the disagreement is
  a criterion split, not a spread of numbers, so both the mechanism and the word need
  revisiting. *Contested* is still the placeholder.
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
