# Production ownership criteria: what was measured, and whether the format generalises

Ticket: [05](tickets/05-draft-bands-for-one-category.md). Criteria under test:
[production-ownership-criteria.md](production-ownership-criteria.md).

```
python scripts/criteria_probe.py                  # the measurement
python scripts/criteria_probe.py --grid           # every answer with its span
python scripts/criteria_probe.py --leverage       # which criteria can move the band
python scripts/criteria_probe.py --score-degraded # answer the unparseable documents too
```

## What was measured, and what was not

**The map's acceptance test was not run.** `scripts/agreement_harness.py` exists (06)
but this environment has no provider credentials, so no run against two providers,
sampled twice, has happened. Nothing below is that number.

What was run is the part that does not need providers. Two judges answered the same
five criteria on the same documents, with no sight of each other:

- **`deterministic`** — each criterion answered from parser-checkable facts alone,
  reusing the repo's own regexes where one exists. It is the floor under any judge, and
  it is also the most a `rule_share` channel could ever contribute to this category.
- **`model-claude`** — one model judge (this session) reading each document and
  answering the same five questions. Verdicts recorded with their evidence in
  [criteria/judgments/model-claude.json](criteria/judgments/model-claude.json).

That measures where the *criteria wording* leaves room to differ. What it cannot
measure is whether two providers, both reading freely, diverge somewhere neither of
these judges does. That is still 06's to supply, and the recorded-verdict file is the
shape it would have to emit for criterion agreement to be measurable at all — the
harness today reads `score` and `band` from a reply, not criterion answers.

## The fixture set could not do this on its own

Four of the seven fixtures in `tests/fixtures/` carry the same bullets, three carry
almost nothing, and every one that can be answered lands in band **A** or band **E**.
Three of the five bands were never reached. A rubric cannot be tested for agreement on
documents that all sit at the ends of it.

So seven short **band probes** were written — plain text, in
[criteria/probes/](criteria/probes/), one per band and one per boundary worth
stressing. They are not PDFs and do not live in `tests/fixtures/`, because they test
the rubric rather than the parser: extraction is deliberately not a variable.

## The measurement

Eleven answerable documents — four fixtures, seven probes.

| document | deterministic | model-claude | agree |
|---|---|---|---|
| strong | A Owned in production (95) | A (95) | yes |
| slop | E No destination (10) | E (10) | yes |
| two_column | withheld | withheld | — |
| hidden_text | withheld | withheld | — |
| scanned | withheld | withheld | — |
| no_phone | A (95) | A (95) | yes |
| buried_evidence | A (95) | A (95) | yes |
| 1-built-not-shipped | E No destination (10) | E (10) | yes |
| 2-shipped-unnamed | D Built, not operated (35) | D (35) | yes |
| 3-shipped-no-after | D (35) | D (35) | yes |
| 4-shipped-operated-once | D (35) | **C Shipped (58)** | **NO** |
| 5-team-attributed | B Shipped and operated (78) | B (78) | yes |
| 6-owned | A (95) | A (95) | yes |
| 7-hedged-but-operated | B (78) | B (78) | yes |

```
criteria: 53/55 answered the same; split on 2-shipped-unnamed/C2, 4-shipped-operated-once/C3
bands: 10 exact, 1 adjacent, 0 far, over 11 documents -> LOOK
```

Against the map's restated test — same band per category, one adjacent disagreement is
a pass that wants another look, more than one or any non-adjacent is a failure — this
is a **LOOK**. It passes, and it is one wobble away from not passing.

## The two splits, and why only one cost anything

**`4-shipped-operated-once` / C3 — the one that moved a band.** The bullet reads
"Shipped a Mistral-7B summariser for support tickets to production, **now serving 40k
requests a day**". The model judge reads that as load only measurable after the thing
ran, answers C3 `yes`, and the lookup returns C. The deterministic judge's C3
vocabulary has `rps`, `qps`, `req/min` and `requests per second` but no per-day or
per-hour form, answers `no`, and the lookup returns D. One criterion, one adjacent
band.

**`2-shipped-unnamed` / C2 — the one that cost nothing.** The probe is written to have
nothing nameable: "Deployed AI-powered solutions to production". The deterministic
judge answers C2 `yes`, because `invariants.SPECIFIC_TOKEN_RE` matches `AI-powered` on
the branch that exists for `Llama-3-8B`. It is wrong. It did not move the band, because
C3 and C4 were both `no` and band D is reached either way.

That pair is the whole argument for criterion-level measurement, and it is worth being
precise about why:

- Both splits are invisible in a band-level comparison. One shows up as a band
  disagreement with no stated cause; the other shows up as nothing at all, while a
  false `yes` sits in the rubric waiting for a resume where C3 and C4 do fire.
- The C3 split is a **vocabulary** defect — one alias family, fixable in the criterion.
  The C2 split is a **channel** defect — no regex can tell a name from a hyphenated
  adjective, so C2 cannot have a rule channel at any wording. Same-looking failure,
  opposite remedies, and only criterion-level output separates them.

04 claimed criteria are "strictly more diagnosable" than a band label. Measured: yes,
and the diagnosis distinguishes two failures that need different fixes.

## Criteria are not equal, and the expensive one is not the subtle one

Flipping one answer moves the band over some answer sets and not others:

| criterion | flips the band | widest move |
|---|---|---|
| C1 destination | 32/32 | 4 bands |
| C2 named system | 12/32 | 3 bands |
| C3 operational fact | 8/32 | 2 bands |
| C4 post-launch work | 8/32 | 2 bands |
| C5 first-person ownership | 2/32 | 1 band |

C1 is a gate — it moves the band from anywhere, so agreement on C1 *is* the category's
agreement. C5, the criterion that reads as most a matter of judgment, separates the top
two bands and nothing else: two judges may split on ownership on every resume and cost
at most one adjacent band each time.

The design consequence is counterintuitive and worth carrying: **spend the wording
budget on the gate criterion, not on the subtle one.** A criterion's cost is set by its
position in the band lookup, not by how hard it is to answer.

## Withholding is load-bearing, and it is measurable

Answering the criteria on documents whose roles did not parse
(`--score-degraded`) puts `two_column` and `hidden_text` back in. Both judges then
answer, and they answer differently — the model judge reads across `two_column`'s
interleaved columns and recovers a shipped, named, operated system; the deterministic
judge, working from a parse with no roles at all, has no bullets to read. The
disagreement is not about the criteria. It is about what the document *is*.

Every one of the five criteria is a question about a bullet inside a role, so on a
document with no roles the judges are not looking at the same resume. Withholding is
the only reading under which they are — and the parser gate has already found and
charged for that defect, so scoring it as well charges one fault twice.

## Verdict: does the format generalise?

**The criteria-to-band format holds for `Production ownership`, and generalises further
than band prose would have** — but on a condition, and with one property that will not
survive being copied blindly.

What makes it work here is that all five questions are answerable by pointing at a
span. That is the same test any category has to pass:

> A criterion generalises when both judges can point at the text that settles it. It
> does not generalise when it asks a judge to weigh something — is this impressive, is
> this deep, does this read as senior.

On that test, applied to 04's remaining four:

- **Agentic systems** and **Evaluation rigour** — the same shape. Both are "is there a
  named thing, and does the resume say what it did". Criteria should transfer nearly
  directly; `Evaluation rigour`'s gate is already written into fluidstack's phrasing
  (*an eval that could have returned a negative answer*).
- **AI-assisted coding fluency** — the questions are answerable ("does a bullet name
  the tooling", "does it say what changed about the work"), but 04 already set its
  `rule_share` to 0 because no rule channel can answer them. It is the category where
  the deterministic floor is absent, so criterion agreement is the *only* agreement
  there is. Worth measuring first, not last.
- **Resume craft** — the one to be careful with. It merges two categories whose
  boundaries are largely weighed, not countable. Some of it is countable (identity
  above the fold, a summary present, bullets within length) and `ats/human.py` already
  checks those deterministically. What is left after subtracting those is taste, and
  criteria will not make it converge. Its 0.7 `rule_share` is doing more work than the
  number suggests.

The property that does not copy: **the band lookup's shape decides what a
disagreement costs**, and here it happens to put the least reliable criterion (C5) in
the cheapest position. That is a fact about this lookup, not about criteria in general.
Every category needs its own leverage table, and a category whose gate criterion is its
hardest question is a category that will not converge however well its criteria are
worded.

## What this hands the next tickets

- **06** — the harness reads `score` and `band` from a judgement, not criterion
  answers. Criterion agreement — 04's "strictly more diagnosable" — is not measurable
  until it reads a criteria object, and the two splits above are the case for adding
  it. Two smaller asks: withhold documents whose roles did not parse rather than
  scoring them, and take the band probes as inputs, since the PDF fixtures reach only
  two of five bands.
- **07** — the deterministic judge in the probe *is* the rule channel for this
  category, measured: 53/55 criterion answers matched a model judge, and its one error
  was C2, where no regex can succeed. That is the concrete form of "which layer owns
  what": C1, C3 and C4 have real rule channels, C2 does not, and C5's is narrow.
  `rule_share` 0.4 is defensible for the category and wrong per criterion.
- **09** — nothing here depends on the digest computing this category's weight, but
  the criteria are the behaviours 09 must teach `jd_dimensions.py` to detect. C1, C3
  and C4's alias families are a starting vocabulary that has now been run against real
  text.
- **04** — its separability judgement holds up where it was most at risk. The
  production/ownership/reliability merge was flagged as the one most likely to be
  revisited if judges split on reliability independently of production. They did not
  split there at all; both splits were on naming and on operational vocabulary. That
  is not proof, on eleven documents with one model judge, but it is the first evidence
  and it points the other way.
