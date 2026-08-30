# Production ownership: the criteria, and the band they look up

Ticket: [05](tickets/05-draft-bands-for-one-category.md). Category defined by
[04](tickets/04-design-the-category-set.md). Measured in
[production-ownership-agreement.md](production-ownership-agreement.md). Machine-readable
in [criteria/production-ownership.json](criteria/production-ownership.json).

> **Production ownership** — whether the resume evidences taking a system to production
> and staying responsible for it after launch. 6/6 in the corpus, `rule_share` 0.4.

Written first because 04 named it: the most scoreable axis in the corpus, and phrased
as a claim about the candidate's history in four of the six postings — the shape a
resume either evidences or does not.

## What the judge answers

Five binary questions. Each is answered with the quote that settles it; an answer with
no quote is a `no`, the same rule findings already live under. The judge names no band
and no number — the band is a lookup from the answers, and the value is a lookup from
the band.

### C1 — Destination
**Does any bullet say the work reached somewhere real — production, a release, live
traffic, users, customers?**

*Yes* needs a quote naming where the work ended up. Building it, designing it, or
researching it is not a destination.
*No* looks like: every bullet stops at the artifact — "Built a classifier", "Designed a
pipeline", "Explored transformer architectures".

### C2 — Named system
**Is at least one shipped thing named specifically enough to ask about in an
interview?**

*Yes* needs a named service, product, model, or pipeline in the same bullet as the
destination.
*No* looks like: "Shipped AI-powered solutions", "delivered scalable systems" —
portable to any candidate.

### C3 — Operational fact
**Does any bullet state a fact that could only be true after the system ran for real?**

*Yes* needs load carried, users served, an incident, an outage, on-call, uptime, an SLA
or SLO, or a regression caught in production.
*No* looks like: only pre-launch numbers — offline accuracy, a benchmark score, a model
size.

### C4 — Post-launch work
**Does any bullet describe work done to a system that was already live?**

*Yes* needs operating, monitoring, debugging, tuning, migrating, porting, replacing,
profiling or iterating on something already running.
*No* looks like: every bullet ends at the launch.

### C5 — First-person ownership
**Is the shipped work attributed to this candidate rather than to a team, and without
hedging their part?**

*Yes* needs the destination bullet's subject to be the candidate — an act, not a
contribution to one.
*No* looks like: "We shipped", "the team launched", "helped deliver", "contributed to",
"assisted with", "participated in".

## The band lookup

First rule that matches. Shared by every judge, so two judges who split on a criterion
only disagree about the *band* when the split crosses a rule boundary.

| band | name | rule | value | reads as |
|---|---|---|---|---|
| **E** | No destination | C1 unmet | 10 | Nothing says any work reached anywhere. |
| **D** | Built, not operated | C1 met, and either C2 unmet or neither C3 nor C4 | 35 | Something shipped, but it is unnameable, or nothing says it ran or that the candidate stayed with it. |
| **C** | Shipped | C1, C2, and exactly one of C3/C4 | 58 | A named thing reached production, and there is one half of the after-launch story. |
| **B** | Shipped and operated | C1, C2, C3, C4; C5 unmet | 78 | The full arc is evidenced, but the resume gives it to a team or hedges the candidate's part. |
| **A** | Owned in production | all five | 95 | A named system, in production, that ran, that they stayed with, and the resume says it was them. |

Two properties the lookup has to have, both under test in
`tests/test_criteria_probe.py`:

- **Total** — every one of the 32 answer sets lands in a declared band, so no judge can
  answer its way off the rubric.
- **Monotone** — meeting one more criterion never lowers the band. The lookup is
  hand-written conditionals, which is exactly where a rubric that punishes extra
  evidence gets in.

## Not every criterion costs the same

Flipping one answer moves the band over some answer sets and not others. This is the
concrete form of 04's claim that criteria are more diagnosable than a band label:

| criterion | flips the band | widest move |
|---|---|---|
| C1 destination | 32/32 | 4 bands |
| C2 named system | 12/32 | 3 bands |
| C3 operational fact | 8/32 | 2 bands |
| C4 post-launch work | 8/32 | 2 bands |
| C5 first-person ownership | 2/32 | 1 band |

`python scripts/criteria_probe.py --leverage` prints it.

C1 is a gate: it moves the band from wherever the resume was, so **agreement on C1 is
the whole category's agreement**. C5 separates the top two bands and nothing else, so
two judges may split on ownership all day and cost the rubric at most one adjacent
band. Design consequence: **spend the wording budget on the gate criterion**, and
accept looser wording lower down. That inverts the intuition that the subtle criterion
(ownership) needs the most careful prose.

## Rules answer these too, and that is what `rule_share` is

04 set `rule_share` 0.4 here on the grounds that a robust rule channel exists —
absence-over-the-whole-document across many synonyms, not a closed list of proper
nouns. That is true of C1, C3 and C4, whose vocabularies are wide and stable, and
`ats/human.py`'s `PRODUCTION_RE` is already most of C1.

It is **not** true of C2. The deterministic probe answers C2 with
`invariants.SPECIFIC_TOKEN_RE`, and on the band probe written to have nothing nameable
it answers *yes* — `AI-powered` matches the `Llama-3-8B` shape. That is
`cred/no-named-models`'s failure mode exactly, in the criterion 04 did not flag: a
name-shaped regex cannot tell a name from an adjective with a hyphen. **C2 is
model-owned in practice**, whatever the category's `rule_share` says, and a rule
channel that answers it will answer it wrong on precisely the resumes the criterion
exists to catch.

## Three rules the criteria do not work without

**1. Visible text only.** White-on-white injection is in `doc.text` — `ats.extract`
records the spans but does not remove them. A criterion answered off injected text
would let the rubric reward the one thing the parser gate calls fraud.

**2. Criteria are answered on the parsed resume, never on raw text.** Every one of the
five is a question about a bullet inside a role.

**3. Where the roles did not survive extraction, the category is withheld** — not
zero, not a guess. On a document whose structure did not parse the judges are not
reading the same resume, and the parser gate has already found and charged for that
defect. Scoring it as well charges one fault twice.

## The second experiment, and why it is not run here

03's runner-up was the model naming a band and then a point inside it; 04 took the
decision further, so under the current shape the difference is one optional field
*after* the criteria: the judge answers C1–C5, and additionally names a point inside
the band the lookup returns.

`scripts/agreement_harness.py` already reads a number, a band, or both, so the
comparison is one prompt variant and one run. It is not run here because this
environment has no provider credentials. What it would settle: whether the extra field
adds resolution inside a band or just re-imports the disagreement discretising
removed.

## Open

- **C5's wording is the weakest.** Band probe `7-hedged-but-operated` is written to
  break it: "Helped ship a Mistral-7B summariser to production", then "Carried the
  pager for it alone after launch". The criterion asks about *the shipped work*, so the
  answer is `no`, and both judges gave `no` — but a resume that evidences sole
  operation of a live system is not obviously team-attributed. Either C5 should ask
  about the whole arc rather than the destination bullet, or the case belongs in the
  band rules. Left open rather than patched, because it needs the second judge that
  06 supplies.
- **Where `Resume craft` and the other three categories get their criteria.** This
  ticket wrote one category, deliberately.
