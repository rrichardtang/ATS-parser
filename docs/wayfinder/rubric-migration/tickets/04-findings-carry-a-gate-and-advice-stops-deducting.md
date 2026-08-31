type: prototype (HITL)
status: open
claimed:
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
