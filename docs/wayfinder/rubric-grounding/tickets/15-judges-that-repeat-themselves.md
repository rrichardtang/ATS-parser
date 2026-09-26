type: decision + build
status: open
claimed: claude
blocked-by: —

# Judges that give the same answer twice

## Question

Raised by rubric-migration 09. Over 875 criterion readings, a provider changed its own
answer between two identical calls 107 times; the two providers disagreed 59 times.
Five criteria carry most of it: `production-ownership/C2`, `/C3`, `/C4` and
`resume-craft/C2`, `/C3`. What change makes a judge answer them the same way twice?

## What the flips show

The owner printed every flip on those five criteria from the 25 September run: 43 in
all (12, 5, 7, 11 and 8). Read one by one, they fall into three patterns.

1. **The `no` run did not search (33 of 43).** Each criterion asks whether *any* bullet,
   or *every* role, shows something. A `yes` needs one example; a `no` needs every bullet
   checked, and the models do not check them. On `12-returning-rag` both providers said
   `no` on one sample and found "our claims assistant" on the other. On
   `20-genai-product-senior` one sample found "the customer-facing routing assistant" and
   the other judged a different bullet. Many `no` answers quote nothing.
2. **Same quote, opposite answer (10 of 43).** The criterion does not say where the line
   is. `strong`'s "Cut GPU spend 34% ... by profiling the serving path" was `no` then
   `yes` for post-launch work. "It was picked up again a year later and is still in use"
   went both ways from both providers. "We stayed on afterwards" split twice. "The
   pipeline" split as a named system; "enterprise partners" split as a purpose.
3. **The criterion's own rule misread.** Three `production-ownership/C2` flips turned on
   whether a name two bullets from the destination counts (C2 says same bullet). One
   `resume-craft/C2` run said `yes` for "satisfying the requirement for at least one role"
   on a criterion that says *every* role. One called "Helped the team to streamline
   various processes" a change.

## Decided, 25 September (the owner)

The boundaries for pattern 2, to be written into each criterion's `yes_requires` and
`no_looks_like` as worked examples:

1. **"Stayed on afterwards" with no work described is `no`** for
   `production-ownership/C4` (post-launch work). Staying is not work.
2. **"Still in use" is `yes` for `production-ownership/C3` (operational fact) and `no`
   for C4.** It says the system survived, not what the candidate did, so it earns credit
   once, where it belongs.
3. **A descriptive name is a named system; a bare category noun is not**
   (`production-ownership/C2`). The test: could an interviewer say "tell me about X" and
   both know which system? "The forecasting service", "the claims assistant", "the
   retrieval pipeline": `yes`. "The pipeline", "the service", "the system", "the model":
   `no`.
4. **Who paid is not what it was for** (`resume-craft/C3`). "Clients", "enterprise
   partners", and "customers" or "users" on their own: `no`. A user doing a task or a
   problem solved ("for dispatchers", "so support agents could answer without
   escalating", "for ticket triage"): `yes`. The deterministic judge's alias list, which
   counts "customers" and "users", changes to match.
5. **A system named elsewhere in the same role counts** for `production-ownership/C2`.
   A name in the skills section or in a different role does not. This loosens C2's
   "same bullet" rule on purpose: the rule was there to stop a listed tool counting as
   shipped, and a name two bullets up in the same role is the same system to any reader.

## Proposed, not yet decided

- **Pattern 1: ask per bullet, let the program count.** Instead of "does any bullet...",
  the content pass answers the criterion for each bullet (or each role, for
  `resume-craft/C2`), and the code derives *any* or *every*. The model stops doing the
  search; the program does the counting, the same way each time. This is a change to
  `ats/prompts.py`, the reply parser and the answer shape, so it is a build, and it
  changes what `rubric.band_of` is handed. It also fixes pattern 3's quantifier misreads
  as a side effect.

## Done when

The five boundaries are in the specs and the deterministic judge; pattern 1 is decided
and, if adopted, built; and the acceptance run (migration 09's command) is repeated with
unstable readings on the five criteria measurably down.
