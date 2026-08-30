# Coverage bands: what the fixtures measured, and whether the format generalises

Ticket: [05](tickets/05-draft-bands-for-one-category.md). Bands under test:
[coverage-bands.md](coverage-bands.md).

Reproduce with:

```
python scripts/coverage_band_probe.py                    # the measurement
python scripts/coverage_band_probe.py --score-degraded   # the failing variant
python scripts/coverage_band_probe.py --scheme B         # the three-level variant
python scripts/coverage_band_probe.py --budget --grid    # arithmetic, and every level
```

## What was measured, and what was not

Ticket 05 asks for the agreement harness (06). It does not exist — 06 is blocked on
03 — and this environment has no provider credentials, so **the map's acceptance test
(two providers, two samples each, seven fixtures plus the real resume) has not been
run and this document does not claim it has.**

What was run instead is the part of the question that does not need providers.
Agreement between two judges is the product of two things: how often they read a
requirement differently, and what one such difference costs. The second is
arithmetic — fixed by the scoring shape, computable exactly, and it turned out to be
the binding constraint. The first was measured between two judges that could both be
run here:

- **`deterministic`** — the bands applied using only facts a parser can check:
  does an alias of the requirement appear, is the appearance inside a role, does
  that bullet carry a metric. Code in `scripts/coverage_band_probe.py`.
- **`model-claude`** — one model judge (this session) reading each fixture's
  extracted text and applying the same band prose, without sight of the
  deterministic output. Verdicts recorded with their evidence in
  [coverage/judgments/model-claude.json](coverage/judgments/model-claude.json).

That is a real two-judge measurement of the band prose, and it is not the
two-provider test. Its value is that it isolates *where* the bands leave room to
differ. What 06 must still supply is whether two providers, both reading freely,
diverge in places neither of these two judges does.

## The measurement

Scheme A (the four levels in the spec), degraded documents withheld:

| fixture | deterministic | model-claude | spread |
|---|---|---|---|
| strong | 54.8 | 54.8 | 0.0 |
| slop | 12.7 | 7.7 | **5.0** |
| two_column | withheld | withheld | — |
| hidden_text | withheld | withheld | — |
| scanned | withheld | withheld | — |
| no_phone | 54.8 | 54.8 | 0.0 |
| buried_evidence | 31.0 | 31.0 | 0.0 |

Four scored fixtures, max spread 5.0, mean 1.2, one level disagreement — a **PASS**
against the ≤5 target, sitting exactly on the line.

The single disagreement is `slop`, `cross-functional-work`: "Helped the team to
streamline various processes, highlighting my ability to empower cross-functional
stakeholders." The deterministic judge sees the alias inside a role bullet and calls
it L2. The model judge applies the spec's *naming is not placing* rule — no action,
no partner named — and calls it L1. The model judge is right, and the deterministic
floor cannot get there. One judgment call, 5.0 of the 5.0 points available.

## Two variants, both worse

**Scoring degraded documents instead of withholding them** (`--score-degraded`):

| fixture | deterministic | model-claude | spread |
|---|---|---|---|
| slop | 12.7 | 7.7 | 5.0 |
| two_column | 10.7 | 30.4 | **19.7** |
| hidden_text | 3.6 | 14.3 | **10.7** |

Max spread 19.7 → **FAIL**, and close to the 22-point spread the map opens with.
The cause is not taste. In `two_column` the columns interleave and no role parses,
so the deterministic judge finds every requirement outside a role and bands the
whole resume at L1, while the model judge reads across the interleaving, recovers
"Cut p99 latency 380ms to 95ms" under "AI Engineer, Northwind Data", and bands it
L3. Both applied the prose correctly. They disagreed about what the document *is*.

Two bands out of three are statements about structure, so on a document whose
structure did not survive extraction the bands have nothing to bind to. Withholding
is not a convenience; it is the only reading under which the two judges are looking
at the same resume. This is now rule 3 in the spec.

**Fewer levels** (`--scheme B`: L0=0.00, L1=0.35, L2=1.00, three levels, no
outcome-attached boundary):

Max spread 9.3 on one level disagreement → **FAIL**. Collapsing L2 and L3 removes
the only boundary that needs real judgment, and still fails — because it makes every
surviving step bigger. Worst single step goes from 5.7 points to 9.3.

This is the counterintuitive result worth carrying forward: **on a fixed 0–100
scale, coarser bands do not buy agreement, they cost it.** The intuition that
discrete levels converge better than a continuous scale is about *the judge's
decision*, not about the reported number. Fewer levels means fewer decisions to get
wrong and more damage when one is.

## The budget, which is the real finding

```
requirement                df    pts   one-step disagreement costs
production-llm-systems      6   14.3   L0->L1  3.6  L1->L2  5.0  L2->L3  5.7
agents-tool-use             6   14.3   L0->L1  3.6  L1->L2  5.0  L2->L3  5.7
cross-functional-work       6   14.3   L0->L1  3.6  L1->L2  5.0  L2->L3  5.7
evaluation                  5   11.9   L0->L1  3.0  L1->L2  4.2  L2->L3  4.8
reliability-guardrails      5   11.9   L0->L1  3.0  L1->L2  4.2  L2->L3  4.8
backend-language            5   11.9   L0->L1  3.0  L1->L2  4.2  L2->L3  4.8
prompt-context              4    9.5   L0->L1  2.4  L1->L2  3.3  L2->L3  3.8
ai-assisted-dev             3    7.1   L0->L1  1.8  L1->L2  2.5  L2->L3  2.9
retrieval-rag               2    4.8   L0->L1  1.2  L1->L2  1.7  L2->L3  1.9
worst single step 5.7 points -> 0 such disagreement(s) fit under the 5-point target, 1 under the 8-point failure line
```

**Zero.** Not "few" — the worst single level-step exceeds the entire tolerance. The
PASS above survives only because the one disagreement that occurred was an L1/L2
step costing exactly 5.0.

So the 5-point acceptance test is not a "judges may differ a bit" allowance. At this
granularity it says: *the judges must agree on essentially every requirement.* Which
tells you where to spend design effort — not on the wording of the levels, but on
making every boundary decidable from something a second judge would see the same way.

Headroom is bought by widening and flattening the requirement set, and only there.
Nine requirements weighted 6…2 give the heaviest 14.3 points. Fifteen weighted
evenly would give each 6.7, and two full disagreements would still land inside the
8-point line.

## Verdict: does the format generalise?

**To Coverage, yes — under the four rules in the spec, and with no headroom.**

**To the rest of the rubric, only where the same test can be met**, which is a
sharper constraint than "write the bands carefully":

> A band boundary generalises when it can be settled by a fact both judges can
> point at — a span is present or absent; it sits inside a role or outside one.
> It does not generalise when it asks a judge to weigh something — is this
> impressive, is this deep, does this read as senior.

Coverage passes because "is this evidenced, and is it evidenced in work" is
countable. Applying the same format to a weighed category does not make it
countable; it puts a 14-point price on a matter of taste. On that test:

- **Likely to generalise**: anything asking *is X present, and where* — evidence of
  scale, evidence of evaluation, named artifacts, quantification. Same shape,
  different subject.
- **Unlikely to generalise**: "Writing quality", "Recruiter scan", any
  seniority-fit judgment. No boundary in them is a fact two judges point at. The
  same band format there produces prose that reads well and numbers that will not
  converge — which is the failure mode the current five categories already exhibit.

The honest consequence: **the remaining four categories should not be written as
0–100 band sets by default.** For the countable ones, reuse this shape. For the
weighed ones, the finding is that they should emit evidenced findings and no score
at all — which is exactly the fork [ticket 03](tickets/03-should-the-model-author-scores.md)
is open on, now with a measurement behind it rather than an intuition.

## What this hands the next tickets

- **03** — the case for findings-only is now measured, not argued: on the one
  category most favourable to scoring, the tolerance affords zero judgment calls per
  requirement. A category with no countable boundary has no chance.
- **04** — design for a wide, flat requirement set, and sort candidate categories by
  whether their boundaries are countable before naming them. Three of the five
  heaviest requirements found here (`production-llm-systems`,
  `cross-functional-work`, `reliability-guardrails`) have no term in
  `ats/skill_groups.py`, so the taxonomy does not currently cover what these
  postings most want.
- **06** — three things the harness needs that this probe exposed. It must withhold
  rather than score degraded documents, or it will report structural failures as
  rubric disagreement. It should record per-requirement levels with evidence, not
  just category scores, so a spread can be attributed to the requirement that caused
  it — the recorded-verdict file shape here is a candidate. And **the fixture set
  cannot exercise a content rubric**: four of the seven carry the same underlying
  bullets, three carry almost nothing, and none has agent, prompt, or customer-facing
  content at all. Every fixture that scored here landed between 12.7 and 54.8. 06
  needs content fixtures built to span the range, not the parser-mechanics fixtures
  that exist.
- **07** — the deterministic judge in the probe *is* the keyword layer, applied to
  the Coverage question. It matched the model judge on 35 of the 36 requirement
  readings across the four scored fixtures — every one but the `slop` bullet above.
  That is the concrete version of "does Coverage duplicate the keyword rules": it
  mostly does, and the model's contribution is specifically the two things listed
  under "Where a judge still has to judge".
- **08** — one finding to check against the literature: coarser discrete levels made
  agreement *worse* here, because the tolerance is stated in points on a fixed
  scale. If the research says discrete levels are the precondition for convergence,
  the reconciliation is probably that those results report agreement *on the level*,
  not on a number derived from it — which would be an argument for changing what the
  acceptance test measures.
