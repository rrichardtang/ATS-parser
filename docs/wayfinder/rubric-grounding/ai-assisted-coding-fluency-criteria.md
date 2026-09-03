# AI-assisted coding fluency: the criteria, and the band they look up

Ticket: [11](tickets/11-criteria-for-the-three-remaining-behaviour-categories.md).
Category defined by [04](tickets/04-design-the-category-set.md); format proved by
[05](tickets/05-draft-bands-for-one-category.md). Measured in
[three-categories-agreement.md](three-categories-agreement.md). Machine-readable in
[ats/criteria/ai-assisted-coding-fluency.json](../../../ats/criteria/ai-assisted-coding-fluency.json).

> **AI-assisted coding fluency** — whether the resume evidences working fluently with
> AI coding tools as a *practice*. 3/6 in the corpus, `rule_share` **0**.

Written **first** of the three, on 05's instruction and against the intuition that the
cheapest category should come last. It is the only category in the rubric with no rule
channel at all, so criterion agreement is the *only* agreement it has: nothing masks a
badly worded criterion here, which makes it the honest test of the format.

The corpus asks for it in three postings and one of them makes it a hard requirement —
ramp: *"Fluency with the latest AI coding models and agentic development workflows.
This is how the team works, and we expect you to be excellent at it."* fluidstack:
*"work fluently with AI coding tools."* amex: *"Use of AI-assisted and agentic
development tools for design, implementation, testing, debugging, and refactoring."*

## What the judge answers

### C1 — Named tooling
**Does any bullet name a specific AI coding tool, assistant or agentic development
workflow?**

*Yes* needs the tool named — Claude Code, Cursor, Copilot, Codex, an agentic coding
workflow. A named product or a named practice both count.
*No* looks like: "Familiar with modern AI tooling", "AI-first engineer" — nothing a
reader could go and look up.

### C2 — The candidate's own work
**Is the tooling used on the candidate's own engineering work, rather than being a
product they built, sold or advised on?**

*Yes* needs the bullet that names the tool to describe the candidate writing,
reviewing, testing, debugging or refactoring code with it.
*No* looks like: "Built an agent on the OpenAI Agents SDK" — real work, and it is
`Agentic systems`, not this category.

This criterion exists because of 02's warning, and it is where the corpus's three-way
split is enforced: *building* agents is category 2, *using* them on your own work is
category 4. Without C2 the two categories are answered by the same sentence, and 04's
separability test is what decides a category exists at all.

### C3 — Changed practice
**Does a bullet say what the tooling changed about how the work is done?**

*Yes* needs a stated difference — what the candidate now does that they did not
before, or stopped doing.
*No* looks like: the tool is named and nothing follows. "Used Cursor daily", a tool
sitting in the skills list.

### C4 — The change is checkable
**Is that change stated as a fact somebody could check — a number, a duration, a rate,
a before and after?**

*No* looks like: "dramatically faster", "10x engineer" — an adverb where the number
goes.

### C5 — Past their own keyboard
**Does the resume say the practice reached past the candidate's own editor — other
people, a standard, or a guardrail?**

*Yes* needs team adoption, a written guideline, a review standard for generated code, a
harness built for others, teaching or onboarding.
*No* looks like: every mention is first-person solo use. A tool the candidate built and
shipped to others is a *product*, not their practice spreading — C2 has already
answered no in that case, and so does this one.

## The band lookup

First rule that matches.

| band | name | rule | value | reads as |
|---|---|---|---|---|
| **E** | No tooling named | C1 unmet | 10 | Nothing names an AI coding tool or an agentic development practice. |
| **D** | Named, not practised | C1 met, C2 or C3 unmet | 35 | A tool is named, but it is somebody else's product, or nothing says what it changed. |
| **C** | A practice, described | C1, C2, C3; neither C4 nor C5 | 58 | The candidate says what the tooling changed about their own work, and asks the reader to take it on trust. |
| **B** | A practice, evidenced | C1, C2, C3, and exactly one of C4/C5 | 78 | The change is either measured or visible in someone else's work — one of the two. |
| **A** | Fluent, and it shows | all five | 95 | A named tool changed named work by a checkable amount, and the practice reached past this one person. |

Total and monotone, under test in `tests/test_criteria_probe.py` across all four
categories.

## Leverage

| criterion | flips the band | widest move |
|---|---|---|
| C1 named tooling | 32/32 | 4 bands |
| C2 the candidate's own work | 8/32 | 3 bands |
| C3 changed practice | 8/32 | 3 bands |
| C4 the change is checkable | 4/32 | 1 band |
| C5 past their own keyboard | 4/32 | 1 band |

`python scripts/criteria_probe.py --leverage -c ai-assisted-coding-fluency` prints it.

The gate is C1, and C1 is *"is a tool named"* — a proper noun a judge either sees or
does not. That is the arrangement 05 said to aim for: the question two judges are least
likely to split on carries the most band movement, and the two that ask for a reading
(is this the candidate's own practice; did anything actually change) sit where a split
costs one band each. This is not a category whose gate is its hardest question, so 05's
failure condition does not fire.

## The rule channel is absent, and C5 is where that is provable

04 set `rule_share` 0 here on the grounds that any rule channel would be a closed list
of proper nouns over the corpus's fastest-moving vocabulary — `cred/no-named-models`'s
failure shape, stale the day it ships. Two things measured that, rather than assuming
it:

**C5 cannot be answered by a regex at all.** Written as an alias family (team, adoption,
guidelines, harness, onboarded) it answered *yes* on `strong` — matching **"eval
harness"** in a bullet about RAG groundedness — and *yes* on `slop`, matching **"Helped
the team"** in a sentence about streamlining processes. Neither has anything to do with
AI tooling. The vocabulary of "a practice spreading" is the vocabulary of ordinary
engineering; only the subject makes it this category's evidence, and the subject is what
a regex cannot see. So the deterministic judge **abstains** on C5 rather than answering
`no`, which means it names no band at all. That is the honest shape of `rule_share` 0:
not a weak channel, an absent one.

**C1's list is checkably stale.** Band probe `8-tool-not-on-the-list` is
`7-fluent` with one word changed — `Claude Code` becomes `Goose`. The model judge reads
band **A**; the deterministic judge's alias list has never heard of the tool, answers C1
`no`, and the three criteria anchored to C1 fall with it — four criterion splits from
one substitution. 04 predicted this in the abstract; it is now a file.

## Open

- **C4 and C5 are interchangeable at band B**, deliberately: a candidate who measured
  the change and a candidate who spread the practice both read as evidenced. Whether
  those are really the same band is the first thing to revisit if judges start
  splitting there.
- **The corpus's newest requirement has the shortest half-life.** C1's alias list is
  documentation of what was current when this was written, not a channel anything
  should score from. If it is ever wired in, `8-tool-not-on-the-list` is the test that
  should fail.
