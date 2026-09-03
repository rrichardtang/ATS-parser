type: prototype (HITL)
status: closed
claimed: claude
blocked-by: 03

# Findings carry a gate, and advice-only findings stop deducting

## Question

07 gave eleven rules a disposition the code has no way to express: they fire, they
carry their message and fix, and they deduct **nothing**. Seven `kw/thin-<group>`
rules, `jd/missing-core`, `jd/missing-secondary`, `jd/missing-named-tools` and
`kw/unsupported-skills` — the whole of tool coverage — plus `cred/notebook-only` (07
§3), and `content/quantification` and `cred/unlinked-projects` (12).

Today every finding deducts. `score.build` adds `finding._raw_cost` to
`deductions[finding.category]` and there is no flag that says otherwise.

## The second half, which is what makes it more than a flag

An advice-only finding needs **a gate and no category** — it is not evidence for any
band and it must not appear in any category's ledger, but it still has to print
somewhere. `Finding.gate` is a property derived from `CATEGORY_GATE[self.category]`
(`models.py:83`), so a finding cannot have a gate without a category today.

So findings carry their own gate. Two consequences worth taking on purpose:

- Tool coverage prints under `Gate.RECRUITER`, per 07 — *"where keyword search actually
  happens"*.
- **`CATEGORY_GATE[Resume craft]` stops being read at all.** 12 chose `Gate.RECRUITER`
  for it and recorded the choice as provisional for exactly this reason: once findings
  carry a gate, the category's own gate is used by nothing, and `Resume craft`'s
  `scan/*` findings can print under the recruiter while its `slop/*` findings print
  under the manager, which is where each belongs.

## One rename

`content/bullet-invariants` fires on two or more failures of a four-predicate bundle.
07 §3 priced `measurability` and `ownership` elsewhere; 12 sent `mechanism` to advice
because no criterion asks about naming. It now deducts on **one** predicate, `outcome`,
and a name that reads as a bundle describes something that no longer exists.

Done when: a finding can declare that it deducts nothing and the ledger excludes it; a
finding carries its own gate and the report groups on that; the eleven advice-only
rules from 07 and 12 deduct nothing while still printing their fix; and
`content/bullet-invariants` is named for the one thing it now checks.

## What was done

`Finding` gained two fields and a validator.

`advice_only` findings deduct nothing. `score.build` splits the findings into
`charged` and the rest before anything else happens, and every later step —
deductions, the composite-space points, the fraud and unreadable checks, the ledger —
reads `charged`. The one place that has to know advice exists is that split; the rest
follows from the points staying at zero.

`gate` is a field rather than a property derived from the category, and `category` may
be None. The validator refuses the two shapes that would be incoherent — an advice-only
finding with a category (a cost with nowhere to go) and a finding with neither a
category nor a gate (nothing could print it) — and fills the gate from `CATEGORY_GATE`
where the category settles it.

### Where the gates came from

Not invented. Each finding's gate is the gate its **pre-04 category** had, so the
category swap does not silently move findings between the two readers. `scan/*` was
`Recruiter scan`; `slop/*` and the `content/*` bullet rules were `Writing quality` and
`Impact`, both MANAGER; `cred/*` was `Credibility`, MANAGER. The single change is 07's:
tool coverage moves from MANAGER to **RECRUITER**, *"where keyword search actually
happens"*.

That leaves `Resume craft` as the one category whose gate cannot be defaulted, since it
now holds both kinds. A finding filed there must name its gate, and the validator
raises if it does not — so a craft rule added later cannot quietly inherit the wrong
reader.

### `CATEGORY_GATE[Resume craft]`: nearly what 12 predicted

12 expected the entry to be read by nothing once findings carried a gate. No *finding*
reads it. But `score._subscore` still does, to place the category's own score — and
that is where 12's other finding does the work: `_subscore` is called with the **set**
`{RECRUITER, MANAGER}`, so craft lands in the same bucket whichever value it holds.
The entry is required and inert, and there is now a test that flips it on a scoring
document and asserts the composite, both sub-scores and both gates' finding lists are
unchanged. If that ever stops being true it fails rather than moving somebody's score.

### Fourteen rules, not eleven

The ticket says eleven and then lists fourteen: eleven is the whole of tool coverage
(one `kw/thin-*` per taxonomy group — seven — plus `kw/unsupported-skills` and three
`jd/missing-*`), and `cred/notebook-only`, `content/quantification` and
`cred/unlinked-projects` are the other three. The test derives the `kw/thin-*` half
from `taxonomy.json` rather than listing it, so adding a taxonomy group does not
silently leave a new rule deducting.

### The rename, and what happened to the other three predicates

`content/bullet-invariants` fired on two or more failures of a four-predicate bundle.
It is now **`content/no-outcome`** and fires on one: `not result.outcome`. The message
says what it checks — *"Says what you were assigned, not what changed"*.

The other three are priced once and elsewhere, per 07 §3 and 12: ownership deducts in
`Production ownership` via `content/ownership`; measurability deducts **nowhere**, now
that `content/quantification` is advice; mechanism was sent to advice by 12 because no
criterion asks about naming.

I did not mint a rule for the mechanism advice. 12 says the mechanism failure *is*
advice, not that it needs its own id, and the advice already survives: `_invariant_fix`
names every failed predicate, so a bullet with no outcome and no mechanism still reads
*"State what changed, not what you were assigned; name the model, tool or technique."*
One rename, no new rule. The cost of the choice, stated: a bullet that states an
outcome but names no mechanism now says nothing about the mechanism at all, where
before it could reach the bundle. That is the intended shape — mechanism is not priced,
and the ticket asked for one rename.

## What this changes on the fixtures

Composites rise, because fourteen rules stopped deducting and the bundle narrowed to
one predicate: `strong` 93.5 → 96.1, `buried_evidence` 83.7 → 90.1, `two_column`
90.5 → 95.7. `slop` is unchanged at 62.8 — its deductions are `slop/*` and `scan/*`,
none of which is advice.

That rise is 07 §2's stated cost arriving: *"a resume that names none of the corpus's
tools loses nothing for it. That is intended."* It also widens the ranking problem
already on the map — `two_column`, which no parser can read, is now an A. Still not
this ticket's to fix, and still recorded there.

## Changed

- `ats/models.py` — `Finding.gate`, `Finding.category | None`, `Finding.advice_only`,
  the validator, and the corrected note on `CATEGORY_GATE[Resume craft]`.
- `ats/score.py` — `charged` versus the rest, and the ledger skipping advice.
- `ats/rules.py` — `_finding` takes a gate and an advice flag; `content/no-outcome`;
  `content/quantification` advice; the craft rules name their gates.
- `ats/human.py`, `ats/keywords.py`, `ats/slop.py`, `ats/passes.py` — gates on every
  craft finding, and the advice dispositions.
- `ats/report.py`, `templates/report.html` — all three exports print `advice` where a
  finding costs nothing. A row reading `−0.0` says "this cost you nothing" in the
  vocabulary of costs; the point is that it is not in that vocabulary at all.
- `tests/test_scoring.py` — eleven new tests: advice costs nothing at every severity,
  has no ledger row, never dilutes a real finding, still prints under a gate; the
  fourteen dispositions checked on the fixtures; a craft finding must name its gate;
  the two incoherent shapes are refused; and the craft category gate is inert.
- `CONTEXT.md` — *advice-only finding* defined. `README.md` — tool coverage is advice,
  and each bullet invariant is priced once.
