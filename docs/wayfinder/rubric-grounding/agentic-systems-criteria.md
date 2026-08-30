# Agentic systems: the criteria, and the band they look up

Ticket: [11](tickets/11-criteria-for-the-three-remaining-behaviour-categories.md).
Category defined by [04](tickets/04-design-the-category-set.md); format proved by
[05](tickets/05-draft-bands-for-one-category.md). Measured in
[three-categories-agreement.md](three-categories-agreement.md). Machine-readable in
[criteria/agentic-systems.json](criteria/agentic-systems.json).

> **Agentic systems** — whether the resume evidences *building* systems that reason
> over context, call tools and take actions. 6/6 in the corpus, `rule_share` **0** per
> [07](tickets/07-which-category-does-each-keyword-rule-file-into.md).

Universal in the corpus and written last of the three, which is 05's ordering: last
because it was expected to be uneventful, not because it matters least. It was
uneventful — the structure transferred from `Production ownership` almost unchanged.

The corpus is literal about the mechanism. amex: *"Build and extend agentic AI
workflows that reason over context, call tools, and perform actions."* fluidstack:
*"Ship agentic systems with real guardrails, authorization, audit, and evals, so agents
act on company systems instead of just advising."* Those two sentences are C3, C4 and
C5.

## What the judge answers

### C1 — A system that acts
**Does any bullet say the candidate built a system that takes actions on its own — an
agent, an agentic workflow, a tool-calling loop, a pipeline that decides its own next
step?**

*Yes* needs the thing built named, and the fact that it acts rather than answers.
Calling a model in a loop and doing something with the result counts; the word "agent"
is not required.
*No* looks like: a model that returns text and stops — a classifier, a summariser, a
chatbot. **And using someone else's coding agent on your own work is
`AI-assisted coding fluency`**, which is the conflation 02 warns about: three postings
mean building agents, one means using them, and a rubric that scores "agentic
experience" as one thing conflates shipping an agent with running Claude Code.

### C2 — Named system
**Is the agentic system named specifically enough to ask about in an interview?**

*No* looks like: "Built agentic AI solutions", "delivered autonomous workflows" —
portable to any candidate.

### C3 — What it could do
**Does the resume say what the system could actually do — which tools, APIs or systems
it reached, or what actions it took in the world?**

*Yes* needs the action surface named: the ticketing system it wrote to, the search
index it queried, the refund it issued, the PR it opened.
*No* looks like: "reasons over context and takes actions" — the job description's own
words handed back with no tools in them. Two near-misses that are **not** an action
surface: the domain noun inside the system's own name (*a ticket-triage agent* does not
evidence reaching a ticketing system), and the escalation path, which is C4's question.

### C4 — What decided the next step
**Does the resume say what drove the system from one step to the next?**

*Yes* needs the control named: a planner, a router, a state machine, a retry or
fallback policy, a confidence threshold, an escalation path, a step budget.
*No* looks like: the system is described as a single call.

### C5 — What bounded it
**Does any bullet say what kept the system inside its limits?**

*Yes* needs guardrails, authorization or scoping, an approval step, an audit trail, a
sandbox, a rate or spend cap, or an eval that gated its behaviour.
*No* looks like: the agent is described as capable and nothing says what it was not
allowed to do.

## The band lookup

| band | name | rule | value | reads as |
|---|---|---|---|---|
| **E** | No agentic system | C1 unmet | 10 | Nothing says the candidate built a system that acts. |
| **D** | Claimed, not described | C1 met, and either C2 unmet or neither C3 nor C4 | 35 | An agent is claimed, but unnameable, or nothing says what it reached or how it decided. |
| **C** | Half a mechanism | C1, C2, and exactly one of C3/C4 | 58 | A named agent with either its tools or its control described — not both. |
| **B** | Mechanism, unbounded | C1, C2, C3, C4; C5 unmet | 78 | What it reached and what drove it are visible; nothing says what it was not allowed to do. |
| **A** | Bounded agent in the world | all five | 95 | A named system that reached real tools, decided its own next step, and had stated limits. |

## Leverage

| criterion | flips the band | widest move |
|---|---|---|
| C1 a system that acts | 32/32 | 4 bands |
| C2 named system | 12/32 | 3 bands |
| C3 what it could do | 8/32 | 2 bands |
| C4 what decided the next step | 8/32 | 2 bands |
| C5 what bounded it | 2/32 | 1 band |

Identical to `Production ownership`'s, which is what "transfers directly" means when it
is checked rather than asserted. The gate asks whether a system that acts exists at all,
and the bounding criterion — the one that needs the most reading, and the one fluidstack
cares most about — costs one band.

## `rule_share` 0, and why the deterministic judge still runs here

04 gave this category 0.4; 07 corrected it to **0**, because the category has no
deducting rule and no `jd_dimensions.py` dimension, so a non-zero share blends the band
against a constant 100 rather than against a channel. That is a fact about `score.py`,
not about whether the questions are answerable by pattern.

The distinction matters for reading the measurement below. The deterministic judge
answers all five criteria here and got 54/55 right, so a rule channel is *available*
even though none is *wired*. That is the opposite of `AI-assisted coding fluency`,
where C5 is unanswerable by any regex and the judge abstains. 09 giving this category a
dimension would make the channel real; nothing has to be reworded for that to happen.

## Open

- **C3's alias family reads the agent's own name.** Probe `5-control-no-tools` describes
  a *ticket-triage agent* whose planner retries and escalates, and nothing else: no tool,
  no API, no action. The deterministic judge matched `ticket` — in the agent's name —
  and answered C3 `yes`, landing band B against the model judge's C. The criterion's
  prose now rules the case out explicitly; the alias family cannot, because it has no way
  to know which words are inside a name. Same shape as 05's C2 finding, one category over.
- **The three-way split is enforced by C1 and C2 of two different categories.** 02's
  *advising others on agents* reading (anthropic) is scored by neither: a bullet about
  guiding customers through agent development answers C1 `no` here and C2 `no` in
  category 4. That is deliberate — a resume claim about advice is not evidence of
  building — but it is the reading most likely to be argued with, and 02 raised it first.
