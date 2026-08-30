type: research (AFK)
status: closed
claimed: claude
blocked-by: 01

# Inventory what the six postings actually require

## Question

With extraction repaired, what do these postings actually ask for — in their own
language, not the taxonomy's? Produce the evidence base the category set will be
built from: recurring requirements with document frequency, the dimensions they
emphasise, and the phrasing they use.

`ats/jd_digest.json` is not that evidence base and cannot become it: its document
frequencies are counted only over the 57 terms hand-authored in
`ats/skill_groups.py`, and its dimensions only over the five regex sets in
`ats/jd_dimensions.py`. Anything these postings require that nobody has already
named is invisible to it — which is exactly the material a category set derived
from the corpus needs. Ticket 01 closed having shown this is now the binding
constraint: `rag` reads 0/6 required over a corpus in which fluidstack asks for
"retrieval systems" and edra for "context engineering". Read the six postings in
`corpus/jds/user/` directly; the digest cross-checks what the taxonomy already
covers, it is not the source.

Start from the three findings ticket 01 hands over: the 3/6 ceiling on any named
term, the alias gap above, and nice-to-haves that appear as inline `Bonus:` bullets
rather than as sections. The first is the one to weigh hardest — if these postings
genuinely do not converge on named tools, a category set built on "what most
postings require" has less to stand on than it sounds like, and this inventory is
where that is established or refuted.

This is deliberately descriptive, not prescriptive. It answers "what is in the
corpus", so that ticket 04 can decide "what should the categories be" against
evidence rather than intuition.

Done when: `docs/wayfinder/rubric-grounding/inventory.md` exists, recording each
recurring requirement with the number of postings it appears in and at least one
verbatim quote, and naming what the taxonomy misses — enough that a reader could
use it to argue for or against any proposed category.

## Answer

[`../inventory.md`](../inventory.md). All six postings read end to end; counts split
into literal string matches and interpretive readings, with the divergence between
them treated as itself a finding.

### The corpus converges — on verbs, not nouns

Every named tool sits at or below 4/6. Every behaviour sits at 5/6 or 6/6:

| | df |
|---|---|
| Shipped to production and owned it after launch | 6/6 |
| Built agentic systems | 6/6 |
| Responsible for reliability | 6/6 |
| End-to-end ownership | 6/6 |
| Evaluation of model quality | 5/6 |
| Python / TypeScript / prompting / RAG / fine-tuning / MCP | 2–4/6 |

This qualifies ticket 01's finding #1. "No convergence on named tools" holds. "A
category set built on what most postings require has less to stand on than the label
implies" does not — it has a great deal to stand on, once you stop counting nouns.
The taxonomy is 57 nouns, so the consensus is invisible to it by construction.

### The dimension scan understates the corpus badly

`jd_dimensions` reads ownership **1/6**; the corpus is **6/6**. It reads evaluation
**3/6**; the corpus is **5/6**. The regexes require particular phrasings ("own"
adjacent to production/lifecycle) that most postings simply do not use.

### Three structural findings beyond 01's handoff

1. **Most requirements are disjunctions, and df cannot represent that.** `python`
   reads 3/6, but exactly **one** posting requires Python specifically; two accept it
   as one of several ("Python, Go, or TypeScript"). Document frequency overstates
   requirement strength wherever a posting offers a choice, and in this corpus most
   do. **This is a live defect in `ats/keywords.py`, not only a rubric concern**:
   `jd/missing-core` on "python" against an "or" list is a false finding.
2. **Two postings disclaim their own requirements list** — amex "We don't hire to a
   narrow checklist"; fluidstack "The below is a starting point." Evidence against
   any category treating requirements as a hard gate.
3. **Ramp shares nothing with the other five at the tool level** — TypeScript, React,
   state management, no Python, no evals, no ML. It overlaps only on the 6/6
   behaviours. The strongest argument in the corpus for behaviour-based categories.

### What the taxonomy has no term for at all

- "Shipped and owned it after launch" — the 6/6 requirement.
- "Can explain the engineering decisions" — 3/6.
- **AI-assisted coding fluency — 3/6, and the newest requirement in the corpus.**
  ramp makes it hard: "This is how the team works, and we expect you to be excellent
  at it." No term for the tools or the practice.

01's finding #2 quantified: `rag` reads 0/6 required; the corpus is 2/6 explicit
(amex, fluidstack) and 2 more adjacent (edra "context engineering", openai "context
construction").

01's finding #3 confirmed: inline `Bonus:` bullets are 2/6 (fluidstack, ramp); two
postings mark nice-to-haves with headers; anthropic and edra make no distinction at
all, so every bullet reads as required.

## What this hands to ticket 04

1. **Categories should be behaviours, not tool coverage.** 6/6 agreement on four
   behaviours, never above 4/6 on any tool, and Ramp makes tool-coverage actively
   harmful.
2. **`Coverage` needs redefining or dropping.** As "does the resume evidence the
   required skills" its ceiling is 4/6 and it inherits the disjunction bug. As "has
   this person shipped, owned, evaluated and operated a production LLM system" it is
   5–6/6 and directly scoreable. This bears on ticket 07 as well.
3. **The most scoreable single axis** is "shipped to production and owned it after
   launch": 6/6, phrased as a claim about history in four of the six, evidenced or
   not evidenced with no judgement call.
4. **Two items belong to the deterministic layer, not the rubric** — the disjunction
   bug and the inline `Bonus:` weighting.

## Changed

- `docs/wayfinder/rubric-grounding/inventory.md` — new, the inventory and its evidence.
