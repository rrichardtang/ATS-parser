type: task (AFK)
status: open
claimed:
blocked-by: —

# One rule for where a fact may come from

## Question

May a rewrite use a fact that the resume states somewhere other than the bullet being
rewritten?

## Why it matters

`NO_INVENTION` says yes: "information present in the resume". `ensemble.audit_score`
says no: a quantity absent from the original bullet is an "invented figure" and costs 60
points, which fails the candidate. Once 02 shows the writer the rest of the role, this
contradiction will throw out more good candidates.

## What to build

Make the fact-check read against the source the prompt allows. The proposal: a figure or
specific is allowed if it appears in the bullet **or the same role**, since a number from
another job attached to this one is a false claim even though the resume contains it.
`audit_clean` and `select_rewrite` take that wider source; the prompt says the same thing
in the same words.

The proper-noun padding and dropped-specifics checks stay measured against the bullet.

## Done when

Prompt and fact-check state one rule, tests cover a figure borrowed from the same role
(passes) and from a different role (fails), and Felix has approved it.

## Found
