# Three categories of criteria: what was measured, and what the criteria cannot hold

Ticket: [11](tickets/11-criteria-for-the-three-remaining-behaviour-categories.md).
Criteria under test:
[ai-assisted-coding-fluency-criteria.md](ai-assisted-coding-fluency-criteria.md),
[evaluation-rigour-criteria.md](evaluation-rigour-criteria.md),
[agentic-systems-criteria.md](agentic-systems-criteria.md). Format and method from
[05](tickets/05-draft-bands-for-one-category.md).

```
python scripts/criteria_probe.py                          # all four categories
python scripts/criteria_probe.py -c evaluation-rigour     # one of them
python scripts/criteria_probe.py --grid                   # every answer with its span
python scripts/criteria_probe.py --leverage               # the four leverage tables
```

## The judge setup, named

**The map's acceptance test was not run.** `scripts/agreement_harness.py` (06) exists
and the baseline ran it, but this environment has no provider credentials, so no
two-provider sweep has happened for any of these three. The ticket asked which was
used: **05's proxy**, unchanged.

- **`deterministic`** — each criterion answered from parser-checkable facts, reusing
  the repo's regexes where one exists. It is the floor under any judge and the most a
  `rule_share` channel could ever contribute.
- **`model-claude`** — one model judge (this session) reading each document and
  answering the same criteria without sight of the deterministic answers. Recorded with
  evidence in [criteria/judgments/](criteria/judgments/), one directory per category.

What that measures is where the *wording* leaves room to differ. It cannot measure
whether two providers diverge somewhere neither of these judges does. Two-provider
numbers remain 06's to supply, and the recorded-verdict files are the shape it has to
emit.

Eleven answerable documents per category — four PDF fixtures and seven band probes
(eight for `AI-assisted coding fluency`) — with `two_column`, `hidden_text` and
`scanned` withheld under 05's rule: every criterion asks about a bullet inside a role,
so a document whose roles did not survive extraction is one the judges do not agree
about the *identity* of, and the parser gate has already charged for that.

## The three measurements

### AI-assisted coding fluency — no second judge exists here

```
criteria: 44/48 answered the same; split on 8-tool-not-on-the-list/C1, /C2, /C3, /C4
          C5 not compared -- one judge declares it unanswerable, over 12 documents
bands: not comparable -- no document has two complete answer sets
```

**This is the result, not a failure to obtain one.** 04 set this category's
`rule_share` to 0; the probe now shows what that costs the measurement. C5 — *did the
practice reach past the candidate's own keyboard* — has no rule channel at any wording:
written as an alias family it answered `yes` on `strong` off **"eval harness"** and on
`slop` off **"Helped the team"**, because the vocabulary of a practice spreading is the
vocabulary of ordinary engineering and only the subject makes it this category's
evidence. So the deterministic judge abstains, names no band, and 05's proxy degenerates
to one judge.

The four splits are all one probe: `8-tool-not-on-the-list` is `7-fluent` with `Claude
Code` replaced by `Goose`. The model judge reads band A; the alias list has never heard
of the tool, C1 falls, and the three criteria anchored to C1 fall with it. That is 04's
"stale the day it ships" argument, now a file that fails on demand.

**Verdict: unmeasured, and it is the only one of the three that is.** Its number needs
06 with credentials, and until then this category is the strongest argument for getting
them.

### Evaluation rigour — PASS

```
criteria: 54/55 answered the same; split on 3-eval-claimed-no-number/C5
bands: 11 exact, 0 adjacent, 0 far, over 11 documents -> PASS
```

| document | deterministic | model-claude | agree |
|---|---|---|---|
| strong | A Evaluation that could say no (95) | A (95) | yes |
| slop | E Nothing measured (10) | E (10) | yes |
| no_phone | A (95) | A (95) | yes |
| buried_evidence | B A readable result (78) | B (78) | yes |
| 1-nothing-measured | E (10) | E (10) | yes |
| 2-numbers-but-no-measurement | E (10) | E (10) | yes |
| 3-eval-claimed-no-number | D Measured, not reported (35) | D (35) | yes |
| 4-a-number-alone | D (35) | D (35) | yes |
| 5-number-with-provenance | C A number (58) | C (58) | yes |
| 6-readable-result | B (78) | B (78) | yes |
| 7-eval-that-said-no | A (95) | A (95) | yes |

The one split is C5 on a probe whose harness "ran it before each release": the model
judge reads a suite standing between the work and a release, the alias family has
`on every change` and `pre-release` and not that phrasing. It cost no band, because C2
was already unmet and band D is reached either way — 05's `2-shipped-unnamed` case
exactly, and the same diagnosis: a vocabulary gap in the criterion, fixable, invisible
at band level.

This is the strongest of the four results, and the reason is worth naming: it is the
one category whose wording came from the baseline rather than from intuition.

### Agentic systems — LOOK

```
criteria: 54/55 answered the same; split on 5-control-no-tools/C3
bands: 10 exact, 1 adjacent, 0 far, over 11 documents -> LOOK
```

| document | deterministic | model-claude | agree |
|---|---|---|---|
| strong | E No agentic system (10) | E (10) | yes |
| slop | E (10) | E (10) | yes |
| no_phone | E (10) | E (10) | yes |
| buried_evidence | E (10) | E (10) | yes |
| 1-no-agent | E (10) | E (10) | yes |
| 2-coding-agent-user | E (10) | E (10) | yes |
| 3-agent-unnamed | D Claimed, not described (35) | D (35) | yes |
| 4-tools-no-control | C Half a mechanism (58) | C (58) | yes |
| 5-control-no-tools | B Mechanism, unbounded (78) | **C Half a mechanism (58)** | **NO** |
| 6-mechanism-unbounded | B (78) | B (78) | yes |
| 7-bounded-agent | A Bounded agent in the world (95) | A (95) | yes |

The split: a *ticket-triage agent* whose planner retries and escalates, and no tool, API
or action anywhere. The deterministic judge matched `ticket` — inside the agent's own
name — and answered C3 `yes`. This is 05's C2 finding one category over: a name-shaped
match a regex cannot distinguish from evidence. Unlike 05's C2, the criterion's prose
*can* rule it out, and now does; the alias family still cannot.

`2-coding-agent-user` is the probe that earns its place quietly. A resume full of Cursor
usage scores **E** here and band A in `AI-assisted coding fluency`, which is 02's
three-way split — building agents, advising on them, using them — enforced by C1 of one
category and C2 of the other. Both judges agreed, on both categories.

## Every category's leverage table, and the check 05 said comes first

| | gate (C1) | C2 | C3 | C4 | C5 |
|---|---|---|---|---|---|
| Production ownership | 32/32 | 12/32 | 8/32 | 8/32 | 2/32 |
| AI-assisted coding fluency | 32/32 | 8/32 | 8/32 | 4/32 | 4/32 |
| Evaluation rigour | 32/32 | 12/32 | 8/32 | 8/32 | 2/32 |
| Agentic systems | 32/32 | 12/32 | 8/32 | 8/32 | 2/32 |

05's failure condition: *a category whose gate is its hardest question will not converge
however well it is worded*. Checked before any measurement, and it does not fire for any
of the three. Every gate asks whether a thing exists at all — is a tool named, did anyone
measure anything, did the candidate build something that acts — and the criterion that
asks for a reading sits at the cheap end in all four. Both judges answered all four gates
identically on all 45 answerable documents; the four splits are all below the gate.

Two properties are now under test for every category rather than argued per category:
that C1 is the criterion moving the band from all 32 answer sets, and that C5 moves it
by at most one band. `tests/test_criteria_probe.py` parametrises everything over the
four specs, so the fifth category inherits the whole suite by existing.

## The demand 10 added: can the criteria carry the report?

10 made the criteria the only vocabulary the content model has, so a defect no criterion
asks about is not a vague score — it is silence. 04 chose the categories on separability
and document frequency, and nothing ever asked them to be exhaustive over defects. The
baseline is the evidence available: 198 findings under 108 invented names, on real
resumes, by two providers. Grouped by the reading behind the name:

| reading | findings | held by |
|---|---|---|
| evaluation, benchmarks, baselines, datasets, methodology | 58 | `Evaluation rigour` C1–C5 |
| scale, production reach, deployment, monitoring, operational fact | 72 | `Production ownership` C1, C3, C4 |
| team attribution, vague or unclear ownership | 12 | `Production ownership` C5 |
| unnamed model, dataset or tool | 9 | `Production ownership` C2, `Agentic systems` C2 |
| seniority overreach and mismatch | 9 | `Title & seniority alignment` (deterministic, unchanged) |
| fragments, run-ons, duplication, padding, generic summary | 15 | `Resume craft` — [12](tickets/12-criteria-for-resume-craft.md) |
| unverified or unsupported claims | 5 | the criterion the claim is about; a claim with no quote is a `no` |

Two readings recur and land outside all three:

- **"Activity, not outcome"** — 13 findings under that name, plus 5 more asking for a
  user or business outcome. `ats/invariants.py` already checks Outcome per bullet and
  07 files `content/bullet-invariants` into `Resume craft`, *conditional on 12
  authoring criteria whose evidence it answers*. So this reading is not given up; it is
  a named requirement on 12, and it is now the largest thing riding on that ticket.
- **"Missing role or product context"** — about 8 findings across five names, all
  asking what the work was *for*. 04 ruled the nearest category out on the map's
  evidence rule and pointed at `invariants.py`'s Mechanism check, which is
  deterministic and survives. Held, but by the layer beneath the criteria.

**Nothing recurring is unreportable, and no criterion was added to make that true.** 10
does not get reopened on this evidence, and option B — a separate closed findings list —
stays unnecessary. The honest caveat: the baseline ran the *old* rubric's prompt, which
asked an open-ended "what is MISSING" question, so it is evidence about what judges
reach for and not about what these criteria would surface. The first run of the new
prompt is where this check should be repeated.

## Verdict

The format holds for two of the three, and the third is the one 05 sent first precisely
because it would be the hardest to measure:

- **Evaluation rigour** — PASS. Transfers directly from `Production ownership`'s shape,
  with wording taken from what two providers already said.
- **Agentic systems** — LOOK. Transfers directly, with one adjacent disagreement caused
  by an alias family reading a proper noun, which is the failure 05 already recorded in
  a different category.
- **AI-assisted coding fluency** — unmeasured. One judge, because the other cannot
  answer C5 at all. `rule_share` 0 was 04's decision about scoring; this is the first
  measurement of what it costs the *measurement*, and the answer is that 05's proxy does
  not exist for a model-owned category.

Four of five judged categories now have criteria, a total and monotone lookup, a
leverage table, band probes and a verdict. `Resume craft` is [12](tickets/12-criteria-for-resume-craft.md).

## What this hands the next tickets

- **06** — three categories' worth of recorded verdicts now exist in the shape the
  harness would have to emit, and one of them (`AI-assisted coding fluency`) cannot be
  measured at all without it. That is a stronger case than 05 could make alone.
- **09** — a dimension for `Agentic systems` is worth `rule_share` as well as weight
  (07), and the deterministic judge here shows the channel is *available* even though
  none is wired: 54/55 with one name-shaped error. The C1/C3/C4 alias families are a
  starting vocabulary that has been run against text.
- **12** — inherits the outcome reading, above, with a count attached: 18 baseline
  findings depend on `Resume craft` authoring a criterion that `content/bullet-invariants`
  answers, or they become unreportable under 10.
- **04** — no separability judgement moved. The one most at risk here was the
  agentic three-way split, and `2-coding-agent-user` shows both judges putting the same
  resume in opposite categories, correctly.
