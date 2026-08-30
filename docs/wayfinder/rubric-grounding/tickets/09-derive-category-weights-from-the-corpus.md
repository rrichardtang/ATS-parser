type: task (AFK)
status: open
claimed:
blocked-by: 04

# Teach the dimension scan the behaviours the categories name

## Question

Ticket 04 made category weight a function of document frequency: how many postings
state the behaviour a category measures. The digest cannot currently compute that.

| category | inventory (02, hand-read) | `jd_digest.json` now |
|---|---|---|
| Production ownership | 6/6 | production 6/6, ownership **1/6** |
| Agentic systems | 6/6 | **no dimension exists** |
| Evaluation rigour | 5/6 | **3/6** |
| AI-assisted coding fluency | 3/6 | **no dimension exists** |

`ats/jd_dimensions.py` is five regex sets — ownership, production, evaluation,
seniority, leadership — and two of the four new categories have no pattern at all.
Ownership reads 1/6 against a corpus that is 6/6 because the regexes require `own`
adjacent to production/lifecycle/end-to-end, and the corpus says it many other ways.

This is the same defect family as 01 (headers the vocabulary never saw) and 02 (a
57-noun taxonomy against a corpus that converges on verbs), one layer further down.
02's inventory is the ground truth to reproduce: every count there is recorded with
at least one verbatim quote, so each is checkable by hand.

Two things this must do, not one:

1. **Reproduce 02's counts on the current six postings.** A pattern set tuned until
   the numbers match is worth little on its own — the counts are the test, not the
   goal.
2. **Compute weights for postings added later.** The whole point of deriving weight
   from the corpus is that a seventh posting moves it with nobody editing anything.
   Patterns fitted to these six specifically would defeat that, so the failure mode
   to design against is overfitting to the corpus that exists.

Also in scope, because 04's decision makes them wrong to leave: `RULE_DIMENSION` drops
its four double-counting entries (`content/ownership`, `cred/no-production`,
`cred/notebook-only`, `cred/no-evaluation`) and keeps `title/seniority-mismatch`,
whose category retains an authored weight. `leadership` is tracked with no scoring
target and should be reconsidered or removed while the file is open.

Note on scope: this is execution, and the map's destination is a spec. It is carried
here by the exception recorded in the map's Notes, because it is the precondition for
04's weights being computed rather than transcribed.

Done when: `jd_dimensions.py` reproduces 02's counts for all four behaviours on the
current corpus, the patterns are covered by tests using verbatim posting text, the
weight derivation is demonstrated on a corpus with a posting added, and
`RULE_DIMENSION` no longer double-counts.
