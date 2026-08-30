# What the six postings actually require

The evidence base for ticket 04. Built by reading all six postings in
`corpus/jds/user/` end to end, in their own language, and counting how many state
each requirement. Descriptive only — no category is proposed here.

Counts marked **(literal)** are string matches, reproducible with grep. Counts marked
**(reading)** are my judgement about what a bullet means, and are the ones to argue
with. Where the two diverge, both are given, because the divergence is the finding.

The six: **amex** (AI Engineer III – Agentic AI), **anthropic** (Applied AI Engineer),
**edra** (Forward Deployed AI Engineer), **fluidstack** (Machine Learning Engineer),
**openai** (Applied AI Engineer, Codex Core Agent), **ramp** (Applied AI Engineer,
Fullstack).

## The headline: they converge on verbs, not nouns

Ticket 01 found no named term exceeding 3/6 and asked whether these postings converge
at all. They do — strongly. Just not on tools.

| Requirement | df | kind |
|---|---|---|
| Shipped an LLM/ML system **to production** and owned it after | **6/6** | behaviour |
| Built **agentic** systems | **6/6** | behaviour |
| Responsible for **reliability** of what they built | **6/6** | behaviour |
| **End-to-end ownership** across the lifecycle | **6/6** | behaviour |
| **Evaluation** of model quality | **5/6** | behaviour |
| Works with **customers or cross-functional partners** | **6/6** | behaviour |
| Python | 3/6 | tool |
| TypeScript | 3/6 | tool |
| Prompt engineering / context construction | 4/6 | tool |
| RAG / retrieval | 2/6 | tool |
| Fine-tuning | 2/6 | tool |
| MCP | 2/6 | tool |

Every tool sits at or below 4/6. Every behaviour sits at 5/6 or 6/6. **The corpus has
a strong consensus; the taxonomy just cannot see it**, because the taxonomy is 57
nouns and the consensus is verbs.

This directly qualifies ticket 01's finding #1. "These postings genuinely do not
converge on named tools" is true. "A category set built on what most postings require
has less to stand on than the label implies" is false — it has a great deal to stand
on, as soon as you stop counting tools.

## The 6/6 requirements, with evidence

### 1. Shipped to production, and owned it after launch — 6/6 (reading; "production" 6/6 literal)

The only requirement all six state as a requirement of the candidate.

- **amex**: "Some hands-on experience building or contributing to AI-powered features,
  LLM-based applications, or applied ML systems (professional or project-based)."
  Also: "This is not a research-only role."
- **anthropic**: "Production experience with LLMs including advanced prompt
  engineering, agent development and frameworks, evaluation frameworks, transcript
  analysis, MCP, and deployment at scale"
- **edra**: "You've shipped something meaningful to production and can explain how it
  evolved"
- **fluidstack**: "You've shipped ML or LLM features to production and owned them
  after launch."
- **openai**: "Have experience building or shipping machine learning or LLM-powered
  products."
- **ramp**: "A track record of shipping polished, production-grade product experiences
  and owning them through ambiguity"

Note the shape: four of the six are phrased as *"you have shipped X"* — a claim about
the candidate's history that a resume either evidences or does not. This is the most
directly scoreable requirement in the corpus.

### 2. Agentic systems — 6/6 (literal)

Universal, but it splits three ways, and the split matters:

- **Building agents as the product**: amex ("Build and extend agentic AI workflows
  that reason over context, call tools, and perform actions"), edra ("Build agentic
  features for knowledge management"), openai ("Design and iterate on agent
  behaviors"), fluidstack ("Ship agentic systems with real guardrails, authorization,
  audit, and evals").
- **Advising others on agents**: anthropic ("agent development and frameworks").
- **Using agentic tools to do your own job**: ramp ("Fluency with the latest AI coding
  models and agentic development workflows. This is how the team works, and we expect
  you to be excellent at it").

A rubric that scores "agentic experience" as one thing will conflate building an agent
with using Claude Code. Three postings mean the first, one means the second, and ramp
means the second as a hard requirement.

### 3. Reliability of what you built — 6/6 (literal, reliability family)

- **amex**: "high standards for reliability, security, and auditability"
- **anthropic**: "maintaining our high standards for safety and reliability"
- **edra**: "Build reliability and confidence systems—evaluation frameworks,
  confidence scoring, and logic for when to automate vs. when to escalate to a human"
- **fluidstack**: "Ship agentic systems with real guardrails, authorization, audit,
  and evals, so agents act on company systems instead of just advising."
- **openai**: "Analyze failures in production and systematically improve robustness
  and reliability."
- **ramp**: "fast, dense, interactive, and trustworthy"

### 4. End-to-end ownership — 6/6 (reading; "own*" 4/6 literal)

The clearest case where literal counting misleads. `own` appears in four postings;
all six describe the same span of responsibility.

- **amex**: "help operate what you build after launch"
- **anthropic**: "guide a focused portfolio of customers from technical discovery
  through successful deployment" (ownership of the engagement, not the system)
- **edra**: "Own customer engagements from discovery and solution design through
  production, adoption, and expansion."
- **fluidstack**: "Own models end to end, from problem framing and data through
  deployment, evaluation, and iteration in production."
- **openai**: "Help define what 'good' looks like for agents completing complex tasks
  end-to-end."
- **ramp**: "Design and ship customer-facing AI experiences end to end, from React UI
  through to the APIs and data contracts behind them"

`ats/jd_dimensions.py` scores this dimension **1/6**. The corpus is 6/6. The regex
requires `own` adjacent to production/lifecycle/end-to-end; the corpus says it many
other ways.

### 5. Evaluation — 5/6 (literal)

Present in every posting except ramp.

- **amex**: "evaluation or monitoring tooling"
- **anthropic**: "developing customized pilots, prototypes, and evaluation suites"
- **edra**: "evaluation frameworks, confidence scoring"
- **fluidstack**: "You've built evaluation harnesses that told you the truth about
  model quality before users did."
- **openai**: "develop and run evals to measure agent performance, regressions,
  failure modes, and edge cases"

`jd_dimensions` scores this **3/6**. Actual 5/6. Fluidstack's phrasing is the most
scoreable in the whole corpus — it names a deliverable *and* the standard it must meet.

## What the taxonomy cannot see

`ats/skill_groups.py` is 57 terms in 7 groups, all nouns. Three things the corpus
requires have no term at all:

1. **"Shipped and owned it after launch"** — the 6/6 requirement. No term.
2. **"Can explain the engineering decisions"** — 3/6. edra: "something with multiple
   layers of engineering decisions you can walk through in detail"; fluidstack: "can
   defend the choice"; anthropic: "Exceptional communication skills to convey
   technical concepts to diverse stakeholders". A resume claim with no reasoning
   behind it fails this; nothing in the pipeline measures it.
3. **AI-assisted coding fluency** — **3/6** (amex, fluidstack, ramp), and it is the
   newest requirement in the corpus. ramp makes it a hard requirement: "This is how
   the team works, and we expect you to be excellent at it." fluidstack: "work
   fluently with AI coding tools." amex: "Use of AI-assisted and agentic development
   tools for design, implementation, testing, debugging, and refactoring." There is no
   taxonomy term for Cursor, Claude Code, Copilot, or the practice itself.

Plus the alias gap ticket 01 flagged, now quantified: `rag` matches only
`rag`/`retrieval-augmented` and reads **0/6 required**. In the corpus, retrieval is
explicit in 2/6 (amex "retrieval-augmented generation (RAG) pipelines", fluidstack
"retrieval systems") and adjacent in 2 more (edra "context engineering", openai
"context construction"). True coverage 2–4/6.

## Three structural findings that constrain any category set

### A. Most requirements are disjunctions, and df cannot represent that

- **amex**: "at least one backend language (Python, Go, or TypeScript)"
- **anthropic**: "proficiency in Python or TypeScript"
- **fluidstack**: "hands-on with LLM APIs, fine-tuning, or retrieval systems"
- **openai**: "Have worked on model evaluation, fine-tuning, or prompt design."
- **amex**: "(professional or project-based)"

`python` reads 3/6. But **exactly one posting requires Python specifically** (openai:
"Are strong in Python"). Two accept it as one of several. Document frequency over
terms systematically overstates requirement strength wherever the posting offers a
choice — and in this corpus, most do.

Consequence for `ats/keywords.py`: `jd/missing-core` firing on "python" against a
posting that said "Python, Go, or TypeScript" is a false finding. This is a live
defect in today's deterministic rules, not only a rubric-design concern.

### B. Two postings disclaim their own requirements list

- **amex**: "We don't hire to a narrow checklist, but candidates should be excited to
  grow in a modern, enterprise-scale engineering environment"
- **fluidstack**: "The below is a starting point. We always make space for exceptional
  people, so if you don't fit this role exactly, tell us where you would."

Evidence against any category that treats a requirements list as a hard gate.

### C. Ramp shares nothing with the others at the tool level

Ramp requires TypeScript, React, state management, API design, and AI-coding fluency.
No Python, no evals, no ML, no retrieval. It is a frontend role inside an Applied AI
org.

Ramp overlaps the other five **only on the 6/6 behaviours**. Any category set scored
on tool coverage will score a strong Ramp candidate as weak against this corpus, and
vice versa. This is the single strongest argument the corpus makes for behaviour-based
categories over coverage-of-named-tools.

## Nice-to-have marking (ticket 01's finding #3, quantified)

Four of six distinguish nice-to-have from required; two do not.

- **Section headers**: amex "Preferred Qualifications", openai "Bonus Points"
- **Inline bullets**: fluidstack "Bonus: Forecasting or scheduling problems. Document
  extraction at scale. Agentic frameworks and MCP. Temporal or workflow engines.";
  ramp "Bonus: experience with BI tools, data visualization, or financial/analytics
  products"
- **No distinction at all**: anthropic, edra — every bullet reads as required

Confirmed: the inline form is 2/6 and counts at full required weight today.

## Seniority

Three postings state years, three state none: amex "4+ years", anthropic "4+ years",
edra "3+ years". No posting asks for senior/staff/principal. `jd_dimensions` scores
the seniority dimension 0/6, which is right about titles and wrong about the corpus —
half of it does gate on experience, just numerically.

## What this hands to ticket 04

1. **Categories should be behaviours, not tool coverage.** The corpus agrees at 6/6 on
   four behaviours and never above 4/6 on any tool. Ramp makes tool-coverage actively
   harmful.
2. **`Coverage` needs redefining or dropping.** As "does the resume evidence the
   skills these postings require", its best case is 4/6 agreement and it inherits the
   disjunction bug in A. As "has this person shipped, owned, evaluated and operated a
   production LLM system", it is 5–6/6 and directly scoreable.
3. **The most scoreable single axis in the corpus** is "shipped to production and
   owned it after launch" — 6/6, phrased as a claim about history in four postings,
   and evidenced or not evidenced in a resume with no judgement call.
4. **AI-assisted coding fluency is a real 3/6 requirement with zero pipeline support.**
   Either a category covers it or the tool is knowingly blind to it.
5. **Two things belong to the deterministic layer, not the rubric**: the disjunction
   bug in `jd/missing-core` (A), and inline `Bonus:` bullets counting as required.
