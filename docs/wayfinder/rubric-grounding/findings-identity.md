# What makes two findings the same finding

Ticket: [10](tickets/10-what-makes-two-findings-the-same-finding.md). Measured against
the baseline run in [baseline-agreement.md](baseline-agreement.md). Categories and
criteria from [04](tickets/04-design-the-category-set.md); the worked example is
[production-ownership-criteria.md](production-ownership-criteria.md).

> **A finding is the evidence for one criterion. Its `rule_id` is the criterion id.**

The content model gets no findings vocabulary of its own. It already has a closed
vocabulary — the criteria — and inventing a second one is what produced 108 names for
198 findings.

## 1. The key

Key of record: **`(rule_id, locator)`**, unchanged from 03. What changes is that both
halves stop being free text — `rule_id` is drawn from the criteria, and `locator` must
resolve against the parsed resume (§4).

Locator alone was the tempting alternative, at 0.51 against the key of record's 0.03. It
is rejected, and not on taste. A resume has 5–9 bullets plus the summary, and each judge
flags 4–11 of them, so two judges marking most of a short list overlap heavily for no
reason at all. Corrected for that:

| key | between | chance | kappa |
|---|---|---|---|
| `(rule_id, locator)` | 0.03 | 0.34 | **−0.48** |
| `locator` alone | 0.51 | 0.58 | **−0.16** |

Locator agreement is *below* the rate two judges would hit by flagging at random, on 6
of the 7 resumes. The 17× swing the ticket opens with is real, but it is not a choice
between a bad key and a good one: it is a bad key and a key that looks good because its
pool is small. Reporting 0.51 as "the judges agree on half the places" would have been
the same naming artifact pointing the other way.

`ats/agreement.py` now reports all three keys per resume with a `chance` line and a
`kappa` beside each `between`, so no future run can read a raw overlap as agreement.
This is 08's chance-correction requirement reaching the findings table.

## 2. The vocabulary

The criteria. Roughly 25 ids of the form `<category>/C<n>` — `production-ownership/C1`
and so on — fixed by construction, because the criteria are authored prose that the
model is answering rather than naming.

The 108 invented names are not waste. They are a design-time input: the terms both
judges reached for unprompted (*evaluation methodology*, *deployment reach*, *scale,
latency, cost, adoption*) are evidence for how to word the criteria that do not exist
yet, as the baseline already noted. The vocabulary moves from a runtime output to a
design-time input, which is the whole of the change.

## 3. Two objects, split on quotability

`/CONTEXT.md` requires a finding to carry a quote, and 05 requires that a criterion
answered with no quote is a `no`. Those two rules meet on defects that are pure
absences: nothing anywhere in the resume says the work reached production, so there is
nothing to quote and nowhere to point. That defect is real, it is the most important
thing the candidate could be told, and it is not a finding.

So a criterion answered `no` yields one of two things, decided by whether the defect has
text to point at:

- **Unmet criterion** — the absence case. No locator, no quote. One per criterion per
  resume, id = the criterion id. *"Nothing in the resume says any work reached
  production."* This is what the band lookup reads and what the report leads with.
- **Placed finding** — the present-but-weak case, where the resume does say something
  and what it says is the problem. Quote and locator required, `rule_id` = the criterion
  id. C5 is the clean example: *"We shipped the ranking service"* is a quotable, placeable
  reason C5 is unmet.

A criterion answered `yes` may also carry placed findings — the quote that settles it is
already a locator and a span — but they are evidence, not defects, and nothing in the
report renders them as advice.

Agreement measurement follows the split. Unmet criteria are compared as a set of
criterion ids and need no key at all; two judges either answered C1 the same way or they
did not, which is the criteria agreement 04 and 05 already measure. Only placed findings
go through `(rule_id, locator)`.

## 4. What this means for `prompts.py`

Stated so the change needs no second decision:

- `CONTENT_SYSTEM` stops asking "what critical information is MISSING?" — the
  open-ended search — and asks the criteria instead, one question at a time.
- `"pattern"` leaves the schema. Nothing in the reply names a kind of defect; the
  criterion being answered is the kind.
- Each criterion answer returns `yes`/`no` plus, where there is one, the quote and the
  locator that settle it. `_rule_id("llm", item.get("pattern"), "content")` in
  `passes.py` becomes a lookup of the criterion id, and can no longer mint a new id from
  model text.
- A reply naming a criterion that does not exist is dropped, exactly as an unevidenced
  finding is dropped today.
- **Locators are resolved, not trusted.** 10% of the baseline's locators named nothing
  in the parsed resume — `interests.bullet[0]`, `exp[0]`, `skills`, and one compound
  `exp[0].bullet[0] / exp[1].bullet[0]` that breaks "one defect in one place" outright
  (anthropic 16%, openai 6%). `passes.py` already resolves locators against real bullet
  text for the rewrite pass; that resolution moves earlier and applies to all of them. A
  placed finding whose locator does not resolve is demoted to an unmet criterion rather
  than discarded — the reading survives, the fictional address does not.

The slop pass and the deterministic rules are untouched. Their ids are code-authored and
already closed; they were never the source of the 108.

## What is given up

A substantive content defect that no criterion asks about becomes unreportable. Three
things bound that cost:

- Per 03, model findings no longer deduct, so an unreportable defect costs the candidate
  a piece of advice, not points.
- Slop and the deterministic rules still cover writing quality and structure, which is
  where most defects outside the behaviour criteria live.
- The criteria are authored, not fixed by nature. A defect the judges keep reaching for
  and no criterion holds is an argument for a criterion, and feeds back into 04.

The honest version of the third point: this makes the criteria set load-bearing for
report *quality*, not just for the score. 04 chose the categories on separability and
document frequency — criteria that were never asked to be exhaustive over defects. That
is a new demand on them, and it is the thing most likely to make this decision look
wrong.
