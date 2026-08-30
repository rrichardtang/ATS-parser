# Map: Grounding the rubric in the JD corpus

`wayfinder:map` — local-markdown tracker. Tickets are files in `tickets/`.
A ticket is **claimed** by setting `claimed: <name>` in its header, before any work.
The **frontier** is every ticket that is `open`, unclaimed, and whose `blocked-by` are all `closed`.

## Destination

A rubric specification for the content pass: a category set grounded in what the
target job descriptions actually require, where each category defines its score
bands in concrete evidence terms — such that two different LLM judges scoring the
same resume land within a stated tolerance of each other.

This map produces the **spec and the decisions behind it**. Implementing it in
`ats/prompts.py`, `ats/score.py` and the digest pipeline is a separate effort.

## Notes

- **Domain**: resume scoring against AI-engineering job postings. Glossary in `/CONTEXT.md`.
- **Skills every session should consult**: `grilling` and `domain-modeling` by default;
  `research` for AFK reading tickets; `prototype` for tickets that need something concrete
  to react to.
- **Acceptance test** (restated by 03, now that the model emits a band rather than a
  number): per category, two providers must name the **same band**; one adjacent-band
  disagreement per resume is a pass that wants another look, and any non-adjacent
  disagreement — or more than one adjacent — is a failure. The **5 points / above 8 fails**
  bar survives as the composite-level statement. Measured on all seven fixtures in
  `tests/fixtures/` plus the user's real resume, sampling twice per resume per provider so
  sampling noise is separable from genuine provider disagreement.
- **Evidence rule**: every category must be scoreable from observable evidence in the
  resume. A category no judge can point at evidence for is what produces a 22-point spread.
- Corpus is personal data (`corpus/jds/user/`), six verbatim postings.

## Decisions so far

- **Destination named**: the deliverable is a rubric spec, not an implementation.
- **Agreement is the bar**: two judges must land in the same place on every category, and
  within 5 composite points, >8 fails. A rubric that cannot hit this is not a good rubric,
  whatever it reads like. (The per-category half of this was a point tolerance until 03
  replaced the model's number with a band; see the acceptance test above.)
- **Categories are replaced, not evolved**: the current five (`Impact & quantification`,
  `AI/ML relevance & depth`, `Credibility & verifiability`, `Recruiter scan`,
  `Writing quality`) are not a starting point. The new set is derived from what the
  postings actually ask for.
- **The model authors no number** (03): it names one **band** per category and cites the
  evidence placing it there; the band's value is a rubric lookup. Findings-only was
  rejected on arithmetic — a finding count is unbounded and unanchored, so two judges
  splitting the same defects 3 ways vs 7 move the composite 34 points, against 2.9 for the
  worst score spread observed. Continuous movement comes from the deterministic rules
  (zero inter-judge variance); the band supplies placement.
- **One opinion, one channel** (03): findings from the model are evidence for the band and
  the fix list, and no longer deduct. Band definitions must therefore be phrased as
  evidence *present*, not defects *found*, or the double count returns.
- **Stable bands, living inputs** (provisional): band definitions are prose that changes
  only on deliberate revision; the corpus supplies which skills get checked. Revisited
  only if future postings consistently clash with the bands.

## Not yet specified

- **A new word for the report's "banded"**. 03 leaves **band** meaning only what
  `/CONTEXT.md` defines it as, so the display of two judges disagreeing needs its own
  term — *contested* is the placeholder.

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
