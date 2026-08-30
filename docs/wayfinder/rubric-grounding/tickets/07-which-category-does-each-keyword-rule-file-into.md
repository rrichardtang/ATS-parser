type: grilling (HITL)
status: open
claimed: claude
blocked-by: 04

# Which category does each keyword rule file into?

## Question

The original question — does a `Coverage` category duplicate the deterministic keyword
rules — was answered by 04 dissolving `Coverage`. The ownership split is settled:
`ats/keywords.py` keeps tool coverage (nouns), the judged categories take behaviour
evidence (verbs), and they are genuinely different things because the corpus converges
on verbs and never above 4/6 on any noun.

What is not settled is the mapping. 04 retired all five judged categories, and every
rule that filed into them now has nowhere to go:

- `jd/missing-core` (was Credibility), `jd/missing-secondary`, `jd/missing-named-tools`,
  `kw/over-repetition`, `kw/skills-dump`, `kw/soft-skill-padding`,
  `kw/unsupported-skills` (were AI/ML relevance)
- `content/bullet-invariants`, `content/weak-opener`, `content/ownership`,
  `content/quantification` (were Impact)
- `cred/no-evaluation`, `cred/no-production`, `cred/notebook-only`,
  `cred/unlinked-projects`, `cred/no-named-models`, `contact/no-github` (were
  Credibility)
- `content/passive-voice`, `content/first-person`, `content/long-bullet`,
  `content/duplicate-bullet`, `scan/*` (were Writing quality / Recruiter scan)

This is spec, not implementation detail, because `rule_share` makes it load-bearing:
a rule's category decides which band's 40% it is half of, and a category with no rules
filed into it scores against a constant rather than a channel (04's Q11 finding).

Two things to settle, and the second is the one with teeth:

1. **The mapping itself.** Which of the five new categories each rule files into.
   Several are obvious (`cred/no-production` → Production ownership,
   `cred/no-evaluation` → Evaluation rigour). Several are not: `jd/missing-core` fires
   on a missing *term*, which is tool coverage, and no new category measures tool
   coverage — so where does it go, or does it stop deducting?
2. **Whether any rule duplicates a band criterion.** 03's constraint survives verbatim:
   whichever layer owns a property, only one of them may move the number. A rule that
   fires on the same evidence a criterion asks about is the double count 03 closed,
   reopened one layer down. `cred/no-production` and a Production ownership criterion
   reading "evidences a system reaching production" are the obvious collision to test
   first.

Note that 02 recorded a live defect here that is not 04's to fix and should not be
lost: `jd/missing-core` firing on "python" against a posting that said "Python, Go, or
TypeScript" is a false finding, because document frequency over terms cannot represent
a disjunction. Whatever category these rules land in, that stays wrong.

Done when: every deterministic rule has a named category under the new set, each
collision with a band criterion is either resolved or explicitly ruled not a
collision, and no category is left with zero rules except `AI-assisted coding fluency`,
which 04 set to `rule_share` 0 deliberately.
