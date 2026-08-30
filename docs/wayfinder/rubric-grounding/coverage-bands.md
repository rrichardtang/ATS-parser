# Coverage: score bands

Ticket: [05](tickets/05-draft-bands-for-one-category.md). Measured in
[coverage-bands-agreement.md](coverage-bands-agreement.md). Requirement set and
recorded judge verdicts in [coverage/](coverage/).

**Coverage** — does the resume evidence the skills the target postings require.
Distinct from whether it evidences them *well*.

Chosen as the one category to draft first because the map names it the axis nothing
today measures and the most direct reading of "grounded in what the job descriptions
want". If bands cannot be written for Coverage they cannot be written for anything,
because Coverage is the category whose evidence is most nearly countable.

## The shape of the answer

Coverage is **not a number a judge picks**. A judge picks a level for each
requirement; the score is arithmetic over those levels:

```
Coverage = 100 × Σ (df_r × level_value_r) / Σ df_r
```

where `df_r` is the requirement's document frequency in the personal corpus — how
many of the six postings ask for it — and `level_value_r` comes from the band table
below.

This shape is the whole design, and it is what the measurement vindicated. A judge
asked for one number about nine different skills has nothing to be held to. A judge
asked "is retrieval evidenced, and where" is answering a question with a checkable
answer, nine times. The score inherits whatever agreement those nine answers have,
and nothing else can leak in.

It also means **the bands are stable while the inputs live**. The prose below never
mentions retrieval, or agents, or Python. It defines what *evidence for a
requirement* looks like. Which requirements get checked comes from the digest, and
changes every time a posting is added. This is the map's "stable bands, living
inputs" decision, and Coverage is where it is cheapest to honour.

## The bands

For each requirement, exactly one level. Read the resume for the requirement's
subject matter, not for its keyword: a bullet about a "planning loop that calls
tools" evidences agents whether or not it uses the word.

### L3 — Demonstrated (1.00)

The requirement appears inside a role or project, in a bullet that also says what
came of it: a number, a named artifact, or a stated before-and-after.

You can say what the candidate did *and* what changed.

> "Owned the eval harness for our RAG pipeline: 900 labelled QA pairs, and raised
> answer-groundedness from 71% to 88%" — L3 for evaluation and for retrieval.

### L2 — Placed (0.60)

The requirement appears inside a role or project, attached to a specific action the
candidate took, but the bullet states no outcome, artifact, or scale.

You can say where they did it. You cannot say what came of it.

> "Maintained the retrieval service for the support assistant." — L2 for retrieval.

**Naming is not placing.** A bullet that contains the requirement's vocabulary but
describes no specific action does not reach L2, however confidently it is written.
"Empowered cross-functional stakeholders" names collaboration; it places nothing.
Such a bullet is L1 if the requirement appears nowhere better, and L0 if it appears
nowhere at all.

### L1 — Asserted (0.25)

The requirement appears only outside any role or project: a skills list, a summary
adjective, a headline, an interests block. Nothing ties it to a period of work.

> `Skills: Python, PyTorch, RAG, Docker` — L1 for retrieval, and nothing more.

### L0 — Absent (0.00)

No form of the requirement appears in the text a human being can see.

## Four rules the bands do not work without

**1. Visible text only.** White-on-white and sub-2pt injection is in the extracted
text (`ats.extract` records the spans but does not remove them). Counting it would
make Coverage *reward* the one thing the parser gate calls fraud. Hidden spans come
out before any requirement is matched.

**2. Coverage is scored on the parsed resume, never on raw text.** Two of the three
bands are statements about structure — "inside a role", "only in a skills list". A
judge who reads the raw text and a judge who reads the parse are answering different
questions on any document where the two differ.

**3. Where the structure did not survive extraction, Coverage is withheld.** Not
zero, not a guess: withheld, the way a missing text layer is withheld today. A
two-column resume whose columns interleave, or an experience section with no dated
role under it, gives the bands nothing to bind to. Scoring it anyway was the single
largest source of judge disagreement measured — 19.7 points on one fixture, against
a 5-point tolerance. The parser gate already has findings for these documents; the
content pass adding an invented number on top is double jeopardy for one defect.

**4. The level is the deliverable; the score is derived.** A judge that emits
`{"retrieval-rag": "L3", "evidence": "..."}` can be checked. A judge that emits
`{"Coverage": 63}` cannot. Every level must carry the span it was read from, and a
level with no span is treated as L0 — the same rule findings already live under.

## What this costs per requirement

The acceptance test is stated in points, so the arithmetic above fixes how much
disagreement the rubric can absorb. With nine requirements weighted 6…2, the
heaviest carries **14.3 of the 100 points**, and one level-step on it costs:

| step | cost |
|---|---|
| L0 → L1 | 3.6 |
| L1 → L2 | 5.0 |
| L2 → L3 | 5.7 |

`python scripts/coverage_band_probe.py --budget` prints the full table.

**One L2/L3 disagreement on one heavy requirement fails the 5-point test on its
own.** That is not a flaw in the prose; it is what a weighted mean of nine things on
a 0–100 scale mathematically is. Two consequences follow, and they are the design
constraints on everything else in the rubric:

- **Agreement has to come from the boundaries being decidable, not from the level
  scheme being forgiving.** Compressing the levels makes each remaining step *more*
  expensive, not less: a three-level variant was measured and its worst step costs
  9.3 points, past the failure line. There is no scheme that buys slack.
- **Headroom comes from more requirements and flatter weights.** Nine requirements
  weighted 6…2 give the heaviest 14.3 points. Fifteen requirements weighted evenly
  would give each 6.7, and two full disagreements would still land inside the
  8-point line. If the acceptance test is to survive contact with real judges, the
  requirement set wants to be wider and flatter than the one drafted here.

## Where a judge still has to judge

Three of the four boundaries are decidable from the parse: whether the subject
matter appears at all, and whether it appears inside a role or outside one. The
deterministic judge in `scripts/coverage_band_probe.py` applies them with no model
involved, and it is the floor under any judge's reading.

Two things it cannot do, and a model judge must:

- **Recognise the requirement when it is not named.** "A planning loop that calls
  tools" is agents. "Caught a 9-point AUC regression before it reached production"
  is monitoring. Alias lists miss both.
- **Tell naming from placing.** "Empowered cross-functional stakeholders" and
  "Partnered with the payments PM to scope the rollout" match the same aliases in
  the same position. Only one of them places the requirement in real work.

Both land on the L1/L2 boundary — 5.0 points on a heavy requirement, which is the
entire tolerance. This is the whole judgment surface Coverage has, and it is already
as large as the acceptance test can afford.

## Open, and deliberately not settled here

- **The requirement set itself.** [coverage/requirements.json](coverage/requirements.json)
  was hand-derived from the six postings for this prototype and is provisional;
  ticket 02 replaces it. Three of its five heaviest requirements
  (`production-llm-systems`, `cross-functional-work`, `reliability-guardrails`) have
  no term in `ats/skill_groups.py` at all, which is a finding for 02 and 04 rather
  than something to patch here.
- **Nice-to-haves.** The map leaves their bonus mechanics unspecified. Nothing above
  depends on them; a nice-to-have is a requirement with a low `df` unless and until
  a different rule is decided.
- **Whether the model scores Coverage at all**, given `ats/keywords.py` already
  emits `jd/missing-core` from the same source — ticket 07. The bands above are
  agnostic: the levels are the deliverable either way, and whether they feed a
  0–100 category or a set of findings is 03's and 07's to settle.
