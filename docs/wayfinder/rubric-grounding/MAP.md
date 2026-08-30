# Map: Grounding the rubric in the JD corpus

`wayfinder:map` — local-markdown tracker. Tickets are files in `tickets/`.
A ticket is **claimed** by setting `claimed: <name>` in its header, before any work.
The **frontier** is every ticket that is `open`, unclaimed, and whose `blocked-by` are all `closed`.

**05 is closed ahead of its `blocked-by`.** It needed 04 only to confirm Coverage is a
category, which this map already asserts, and the bands it produced do not depend on
02's inventory. 04 and 07 should read its verdict before they are worked; the ticket
says what it did not do.

## Destination

A rubric specification for the content pass: a category set grounded in what the
target job descriptions actually require, where each category defines its score
bands in concrete evidence terms — such that two different LLM judges scoring the
same resume land within a stated tolerance of each other.

This map produces the **spec and the decisions behind it**. Implementing it in
`ats/prompts.py`, `ats/score.py` and the digest pipeline is a separate effort.

## Spec so far

- [coverage-bands.md](coverage-bands.md) — the first category's bands (05).
- [coverage-bands-agreement.md](coverage-bands-agreement.md) — what they measured,
  and the verdict on the format (05).
- [coverage/](coverage/) — the provisional requirement set and recorded judge verdicts
  the measurement ran on. Replaced by 02.

## Notes

- **Domain**: resume scoring against AI-engineering job postings. Glossary in `/CONTEXT.md`.
- **Skills every session should consult**: `grilling` and `domain-modeling` by default;
  `research` for AFK reading tickets; `prototype` for tickets that need something concrete
  to react to.
- **Acceptance test**: two providers within **5 points** on every category, on all seven
  fixtures in `tests/fixtures/` plus the user's real resume. Above **8 points** is a
  failure; 5–8 is a pass that wants another look. Sample twice per resume per provider so
  sampling noise is separable from genuine provider disagreement.
  **Not yet run against anything** — it needs 06 and provider credentials. 05 measured
  a two-judge proxy only, and says so.
  Two things 05 found out about the test itself: the fixture set cannot exercise a
  content rubric (four of the seven carry the same bullets, three carry almost nothing,
  none has agent, prompt or customer-facing content), and a tolerance stated in points
  on a 0–100 scale is far stricter than it reads — see the decisions below.
- **Evidence rule**: every category must be scoreable from observable evidence in the
  resume. A category no judge can point at evidence for is what produces a 22-point spread.
- Corpus is personal data (`corpus/jds/user/`), six verbatim postings.

## Decisions so far

- **Destination named**: the deliverable is a rubric spec, not an implementation.
- **Agreement is the bar**: ≤5 points between judges per category is the target, >8 fails.
  A rubric that cannot hit this is not a good rubric, whatever it reads like.
- **Categories are replaced, not evolved**: the current five (`Impact & quantification`,
  `AI/ML relevance & depth`, `Credibility & verifiability`, `Recruiter scan`,
  `Writing quality`) are not a starting point. The new set is derived from what the
  postings actually ask for.
- **Model-authored scores are questionable**: whether the model emits a 0–100 score at
  all is open, not assumed. See ticket 03.
- **Stable bands, living inputs** (provisional): band definitions are prose that changes
  only on deliberate revision; the corpus supplies which skills get checked. Revisited
  only if future postings consistently clash with the bands.
  **Held up under 05**: the Coverage bands never name a skill, so the requirement set
  can be replaced wholesale without touching them.
- **A band boundary must be countable, not weighed** (05). A boundary converges when
  both judges can point at the fact that settles it — a span is present or absent, it
  sits inside a role or outside one. A boundary that asks a judge to weigh something
  (is this impressive, does this read as senior) does not converge, and the band format
  does not rescue it. This is the test a category must pass before bands are written
  for it.
- **A category is withheld, never guessed, when the parse cannot carry it** (05).
  Bands that talk about resume structure have nothing to bind to on a document whose
  structure did not survive extraction. Scoring those anyway was the largest measured
  source of judge disagreement — 19.7 points against a 5-point tolerance — and it
  charges one document twice for a defect the parser gate already found.
- **Coarser bands cost agreement, they do not buy it** (05, measured). On a fixed
  0–100 scale, collapsing four levels to three raised the worst single-step cost from
  5.7 to 9.3 points. Agreement comes from decidable boundaries, not forgiving levels.
- **Headroom comes from a wide, flat requirement set** (05). Nine requirements
  weighted 6…2 give the heaviest 14.3 of 100 points, so the 5-point tolerance affords
  zero judgment calls. Fifteen weighted evenly would give each 6.7 and absorb two.

## Not yet specified

- **When the rubric gets revised.** Deferred: the trigger is "future inputs consistently
  clash with the rubric", which isn't yet a testable condition.
- **Nice-to-have bonus mechanics.** Nice-to-haves should add "a slight bonus" to coverage;
  how much, and whether it can compensate for a missing requirement, is unspecified.
- **What happens to `config.RULE_DIMENSION` and `dimension_multiplier()`** — the existing
  JD-derived 1.5× rule scaling — once categories are redesigned. It may be subsumed,
  kept alongside, or dropped.
- **Whether the slop pass folds into a quality category** or stays a separate pass with
  its own findings.
- **How the spec migrates into code** without a flag day: the composite, the ledger and
  the report all read today's five categories.

## Out of scope

- Implementing the rubric in code. The destination is the spec; implementation follows.
- Pass 3 (rewrite generation) and its judge/polish machinery.
- The report UI and score-derivation rendering.
- The deterministic rule set (`ats/human.py`, `ats/keywords.py`) except where a new
  category demonstrably overlaps it — see ticket 07.
