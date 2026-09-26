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

## Decided, 26 September (the owner): ask per bullet

- **Pattern 1: ask per bullet, let the program count.** Approved by the owner. Instead of "does any bullet...",
  the content pass answers the criterion for each bullet (or each role, for
  `resume-craft/C2`), and the code derives *any* or *every*. The model stops doing the
  search; the program does the counting, the same way each time. This is a change to
  `ats/prompts.py`, the reply parser and the answer shape, so it is a build, and it
  changes what `rubric.band_of` is handed. It also fixes pattern 3's quantifier misreads
  as a side effect.

### How it is built

Scoped to the five criteria this ticket is about; the other twenty keep one answer.

- Each of the five specs gains a `scope`: `any_bullet` for `production-ownership/C2`,
  `/C3`, `/C4` and `resume-craft/C3`, `every_role` for `resume-craft/C2`.
- For a scoped criterion the model returns an answer **for every bullet in PLACES**
  rather than one answer. The code derives the criterion: `any_bullet` is `yes` when
  any bullet is `yes`; `every_role` is `yes` when each role has at least one `yes`.
- A reply that leaves bullets out has not answered: the criterion is dropped as an
  abstention, as an unreadable answer is today, rather than read as `no`. Reading a
  missing bullet as `no` would rebuild the search failure this change removes.
- A derived `yes` carries the first `yes` bullet's quote and locator. A derived `no`
  is an unmet criterion, not a placed finding: there is no single bullet that is the
  defect.

## Done when

The five boundaries are in the specs and the deterministic judge; pattern 1 is decided
and, if adopted, built; and the acceptance run (migration 09's command) is repeated with
unstable readings on the five criteria measurably down.

## Built, 26 September

Both parts, each built by bob-the-builder and approved by felix-the-fixer.

- **Round A** (1de8759, b29be5e): the five boundaries are in the specs' `yes_requires`
  and `no_looks_like`. `resume-craft/C3` lost its bare "customer(s)" and "user(s)"
  aliases; `production-ownership/C3` gained "still in use" and "still running". The
  probe's `named_in` now searches the anchor's role, tracked with the anchor rather than
  looked up by bullet text, which felix caught mis-resolving a bullet repeated across
  roles.
- **Round B** (2d4a83c, 047ec1d): `production-ownership/C2`, `/C3`, `/C4` are `any_bullet`
  (role bullets only), `resume-craft/C3` is `any_place` (summary and bullets, because its
  question is about the resume) and `resume-craft/C2` is `every_role`. The model answers
  each place; `passes.derive_scoped`, called from `content_judgments`, derives one answer,
  so everything downstream is unchanged and saved runs still load.
  - A scoped criterion answered the old way (one answer) is an abstention on the live
    path, so the model cannot fall back to the unsearched answer.
  - A missing place abstains only when it could change the result: one `yes` settles
    `any_*`; one role answered all `no`, or with no bullets, settles `every_role`.
  - A place answered both `yes` and `no` counts as unanswered.
  - A derived `no` is an unmet criterion, never a placed finding, and shows the
    criterion's own `no_looks_like` (for `every_role`, the role that fell short).
  - The model quotes only on `yes` places, to keep the reply inside the token limit.

## Known gaps

- **The deterministic judge cannot see decision 3.** `SPECIFIC_TOKEN_RE` in
  `scripts/criteria_probe.py` matches tokens like `vLLM`, not descriptive names like
  "the forecasting service". The model is now told those count; the probe still says
  `no`. Expect the probe and the model to disagree on `production-ownership/C2`.
- **Reply size is unmeasured.** Felix estimated 6–7k output tokens for a 15-bullet
  resume and 10–11k for 30, against a 16,000 cap that OpenAI's reasoning tokens also
  count against. A truncated reply fails loudly, not silently. Only a live run can
  confirm it.

## Left

Rerun migration 09's acceptance test (owner's machine, both keys) and compare unstable
readings on the five criteria against 25 September: `production-ownership/C2` 11,
`/C3` 5, `/C4` 6, `resume-craft/C2` 10, `/C3` 7. Then this ticket closes.
