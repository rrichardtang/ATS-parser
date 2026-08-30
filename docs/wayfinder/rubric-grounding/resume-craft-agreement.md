# Resume craft: the measurement, and why its LOOK is not the same LOOK

Ticket: [12](tickets/12-criteria-for-resume-craft.md). Criteria under test:
[resume-craft-criteria.md](resume-craft-criteria.md).

```
python scripts/criteria_probe.py -c resume-craft
python scripts/criteria_probe.py -c resume-craft --grid
python scripts/criteria_probe.py --leverage
```

## Judge setup

Unchanged from 05 and 11, and named because the ticket requires it: **the acceptance
test was not run.** No provider credentials in this environment, so `deterministic`
against one recorded model judge, over eleven answerable documents — four PDF fixtures
and seven band probes, with `two_column`, `hidden_text` and `scanned` withheld.

The deterministic judge here is unusual and worth stating: all five criteria are answered
by the repository's **own predicates**, not by alias families written for the probe.
`ROLE_IDENTITY_RE` for C1, `invariants.evaluate(...).outcome` for C2,
`_duplicate_bullets`' token overlap raised to the role for C4, and `slop/portable`'s
threshold for C5. Only C3 needed a vocabulary, because nothing in the repository asks
what the work was for. At `rule_share` 0.7 that is the right shape: the rule channel is
the majority owner of this category's score, so the floor under the model judge is the
shipped rule set rather than an approximation of it.

## The measurement

| document | deterministic | model-claude | agree |
|---|---|---|---|
| strong | A Edited (95) | A (95) | yes |
| slop | E Not written for a reader (10) | E (10) | yes |
| no_phone | A (95) | A (95) | yes |
| buried_evidence | B One thing left (78) | B (78) | yes |
| 1-nothing-for-a-reader | E (10) | E (10) | yes |
| 2-two-of-five | D Needs a rewrite (35) | **E Not written for a reader (10)** | **NO** |
| 3-readable-unedited | C Readable, unedited (58) | C (58) | yes |
| 4-one-thing-left | B (78) | B (78) | yes |
| 5-edited | A (95) | A (95) | yes |
| 6-same-job-twice | B (78) | B (78) | yes |
| 7-no-identity | B (78) | B (78) | yes |

```
criteria: 54/55 answered the same; split on 2-two-of-five/C4
bands: 10 exact, 1 adjacent, 0 far, over 11 documents -> LOOK
```

**05's prediction is wrong on this evidence.** `Resume craft` converged as well as
`Agentic systems` (54/55, LOOK) and better than `Production ownership` (53/55, LOOK),
the category chosen as the format's easiest case. Nothing here had to be weighed rather
than pointed at.

## But it is a harder LOOK, and the leverage table says by how much

The band is a defect count, so every criterion moves the band from 30 of 32 answer sets
and none moves it by more than one. There is no gate and there are no cheap seats.

| | how a split costs | worst case |
|---|---|---|
| gated categories (the other four) | a split on C5 costs nothing, on C1 costs up to 4 bands | 05 spent two splits and still reached LOOK |
| `Resume craft` | every split costs exactly one adjacent band | one split is LOOK; **two splits anywhere is FAIL** |

So 54/55 is not merely a good result here — it is the best result short of perfect.
05's prediction was directionally right and wrong about the mechanism: the difficulty is
not that craft criteria are hard to answer, it is that a category with no gate has to
answer more of them identically to reach the same verdict.

That is a fact about the lookup shape, not about craft, and it generalises: any future
category whose subject cannot be absent inherits both the count shape and its harsher
scale.

## The one split, and what it actually found

`2-two-of-five` holds two roles of different filler — *"Responsible for utilising modern
frameworks to facilitate data-driven insights"* against *"Involved in delivering robust
and scalable solutions that supported strategic transformation."*

The deterministic judge computes token overlap between the roles, finds it low, and
answers C4 *"roles read differently"* **yes**. The model judge answers **no**: neither
role reads as a job at all, so nothing distinguishes them. Different filler is not a
different job.

This is not a vocabulary gap like 05's `req/min` or 11's *"before each release"*. It is a
**dependency between two criteria in the same set**: when C5 fails — every bullet could
be anyone's — C4 has no answer, because interchangeable filler is neither the same job
nor a different one. 04 and 08 both name separability as the agreement lever, and it has
always been applied *between categories*. This is the first time it has bitten *within* a
criteria set.

The repair is one line — make C4 conditional on C5, exactly as 11 made `Agentic systems`
C3–C5 conditional on C1. **It is deliberately not applied.** 05 left its own C5 wording
unpatched for the same reason: a criterion fixed against the judge that found the problem
produces a number that means nothing, and the fix needs the second judge 06 supplies.

## Which of the ticket's three outcomes

The ticket named three, and said none of them is a bad result:

1. **Criteria that converge.** ✅ This one, on the proxy available.
2. Criteria that do not converge, measured — the model's 0.3 share dropped or fixed.
3. No model channel at all, `rule_share` 1.0.

Outcome 1, with the caveat above about what the LOOK is worth. Two things make it a
narrower win than the number suggests:

- **The criteria are not the category 04 described.** Every piece of evidence 04 named
  for `Resume craft` is answered by a deterministic rule that already ships. What the
  criteria hold is the three readings that survive the subtraction — a bullet that names
  a change, a resume that says what the work was for, roles that read as different jobs
  — and only the middle one is invisible to the current rule set. This category's model
  channel is worth its 0.3 because of one criterion, not five.
- **Outcome 3 was live and is now closed by measurement rather than by preference.** The
  argument for it was that craft is taste; the measurement says the pointable part is
  not, and 10 makes the cost of choosing silence explicit — C3 is the only thing in the
  entire rubric that asks what the work was *for*, and dropping the model channel would
  delete that reading from the report entirely.

## What this hands the next work

- **06** — a fifth recorded-verdict set, and the first category whose acceptance
  threshold is materially harsher than the others'. When the real two-provider run
  happens, `Resume craft` is where it will fail first, and the C4/C5 dependency is the
  pre-registered hypothesis for why.
- **The migration** — three concrete asks, all of them narrowings of things already on
  the list: `content/bullet-invariants` deducts on one predicate and should be renamed;
  `content/quantification` and `cred/unlinked-projects` become advice-only; and findings
  need their own gate, after which `CATEGORY_GATE[Resume craft]` is read by nothing.
- **04** — its gate question was half a false alarm. `_subscore` takes the union of
  `RECRUITER` and `MANAGER`, so the choice moves no number; only report placement.
