type: prototype (HITL)
status: open
claimed: claude
blocked-by: 03

# The content prompt asks the criteria

## Question

`prompts.CONTENT_SYSTEM` asks the model two things: score five categories 0–100, and
find what is missing. 03 removed the first and 10 removed the second. Neither removal
has reached the file.

The model now answers **criteria** — for each category, five binary questions, each
with the quote that settles it. It names no band and no number; the band is a lookup
and the value is a lookup from the band.

## What 10 specified, restated so it needs no second decision

- `CONTENT_SYSTEM` stops asking *"what critical information is MISSING?"* — the
  open-ended search — and asks the criteria, one question at a time.
- **`"pattern"` leaves the schema.** Nothing in the reply names a kind of defect; the
  criterion being answered is the kind. `passes.py:104`'s
  `_rule_id("llm", item.get("pattern"), "content")` becomes a lookup of the criterion
  id and can no longer mint a new id from model text. That single line produced 108
  distinct names for 198 findings in the baseline.
- Each answer returns `yes`/`no` plus, where there is one, the quote and the locator.
- **A reply naming a criterion that does not exist is dropped**, exactly as an
  unevidenced finding is dropped today.
- **Locators are resolved, not trusted.** 10% of the baseline's locators named nothing
  in the parsed resume — `interests.bullet[0]`, `exp[0]`, `skills`, and one compound
  `exp[0].bullet[0] / exp[1].bullet[0]` that breaks "one defect in one place" outright.
  `passes.py` already resolves locators against real bullet text for the rewrite pass;
  that resolution moves earlier and applies to all of them. A finding whose locator does
  not resolve is **demoted to an unmet criterion, not discarded** — the reading survives,
  the fictional address does not.

## The two objects a `no` produces

10 §3, and the schema has to carry both:

- **Unmet criterion** — the absence case. No locator, no quote, because there is nothing
  to point at. *"Nothing in the resume says any work reached production."* This is what
  the band lookup reads and what the report leads with.
- **Placed finding** — present-but-weak, where the resume does say something and what it
  says is the problem. Quote and locator required.

A criterion answered `yes` may also carry placed findings; they are evidence, not
advice, and the report must not render them as fixes.

## Withholding

05's rule, and it is not optional: every criterion asks about a bullet inside a role, so
a document whose roles did not survive extraction has its judged categories **withheld**,
not guessed and not zeroed. The parser gate has already found and charged for that
defect; scoring it as well charges one fault twice. `two_column`, `hidden_text` and
`scanned` are the fixtures that exercise it.

Done when: the content pass sends criteria and parses criterion answers; ids come from
the specs rather than from model text; locators resolve or the finding demotes; unmet
criteria and placed findings are separate objects; and a document whose roles did not
parse is withheld.
