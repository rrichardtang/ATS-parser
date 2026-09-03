type: prototype (HITL)
status: closed
claimed: claude
blocked-by: —

# Criteria for the three remaining behaviour categories

## Question

04 named five judged categories. 05 wrote the criteria for one of them, deliberately —
prove the format before mass-producing it — and returned LOOK, one wobble from failing.
`Agentic systems`, `Evaluation rigour` and `AI-assisted coding fluency` still have a
name, a document frequency and a `rule_share`, and nothing a judge can answer.

Four fifths of the spec the map is for does not exist, and nothing tracked that until
now. `Resume craft` is [12](12-criteria-for-resume-craft.md), split off because 05
predicts it will not converge and the other three should not wait on it.

**10 raised the stakes on this.** Before it, a category with no criteria still had the
open-ended defect search as a fallback — the model would surface *something* about
agentic work whether or not a criterion asked. 10 removed that: the criteria are now
the only vocabulary the content model has, so a category with no criteria is not a
vague score, it is **silence**. The candidate reads nothing about it.

## What 05 already settled, and this ticket must not relitigate

- **The format**: binary evidence questions, each answered with the quote that settles
  it, and a band lookup from the answers. Five bands, E to A. The judge names no band
  and no number.
- **The two properties under test**: the lookup must be *total* (every answer set lands
  in a declared band) and monotone. `tests/test_criteria_probe.py` and
  `scripts/criteria_probe.py` are the existing harness; `criteria/production-ownership.json`
  is the schema to follow.
- **When to withhold**: every criterion asks about a bullet inside a role, so a document
  the parser cannot carry (`two_column`, `hidden_text`) is withheld rather than guessed.
  Answering anyway makes judges disagree about what the document *is*.
- **The fixture set cannot do this alone.** Four of the seven fixtures carry the same
  bullets and every answerable one lands in band A or E, leaving three of five bands
  unreachable. 05 wrote seven short band probes for the boundaries
  (`criteria/probes/`); each category here needs its own.

## Order, and why it is not "easiest first"

05 is explicit and this ticket follows it:

1. **AI-assisted coding fluency** — first, not last. `rule_share` **0** by 04's
   decision, the first model-owned category, so criterion agreement is the *only*
   agreement it has. Nothing masks a bad criterion here, which makes it the honest test
   of the format and the one whose failure is most expensive to discover late.
2. **Evaluation rigour** — 5/6 in the corpus, and the baseline handed over its
   vocabulary for free: both judges, unprompted, converged on *evaluation methodology /
   protocol*, *benchmark provenance*, *baselines*, *eval set*, *measurement method*.
   That is evidence for wording, and better than intuition.
3. **Agentic systems** — 6/6, and 05 expects it to transfer nearly directly from
   `Production ownership`. Last of the three because it is the most likely to be
   uneventful, not because it matters least.

## The leverage table is not optional

05's second finding: a criterion's cost is set by its position in the band lookup, not
by how hard it is to answer. `Production ownership`'s C1 moves the band from all 32
answer sets; C5 moves it from 2. Spend the wording budget on the gate criterion.

So each category needs its own leverage table, and 05 states the failure condition it
detects: **a category whose gate is its hardest question will not converge however well
it is worded.** That is a reason to restructure the lookup, not to keep rewording. It is
the cheapest check available here and it comes before any measurement.

## The demand 10 added

10 made the criteria the only vocabulary, which asks something of them that 04 never
did. 04 chose categories on separability and document frequency; nothing asked the
criteria to be *exhaustive over defects*. They now carry the report's usefulness as
well as the score.

Concretely, while writing each set: the baseline records what both judges actually said
about real resumes. A reading that recurs there and that no criterion in this set can
hold is the signal 10 named — and the answer is a criterion, or an explicit note that
the reading is given up. Not a shrug. If that happens often enough across all three,
10's decision is the thing to reopen (option B: a separate closed findings list), and
this ticket is where the evidence for that would first appear.

## Note on measurement

05 could not run the acceptance test — no provider credentials in that environment — so
its LOOK came from a deterministic answerer against one model judge. That measures where
the wording leaves room to differ, not whether two providers diverge. 06 built the real
harness and the baseline ran it, so a two-provider run is now possible in principle;
whether credentials are available here decides whether these three get the real number
or 05's proxy. Say which was used, either way.

Done when: `AI-assisted coding fluency`, `Evaluation rigour` and `Agentic systems` each
have criteria, a total and monotone band lookup, a leverage table, band probes for the
boundaries the fixtures cannot reach, and a measured agreement verdict — with the judge
setup named. Machine-readable alongside `criteria/production-ownership.json`, prose
alongside `production-ownership-criteria.md`.

## Answer

**Written, measured, and one of the three could not be measured — which is the finding.**

- [ai-assisted-coding-fluency-criteria.md](../ai-assisted-coding-fluency-criteria.md)
- [evaluation-rigour-criteria.md](../evaluation-rigour-criteria.md)
- [agentic-systems-criteria.md](../agentic-systems-criteria.md)
- [three-categories-agreement.md](../three-categories-agreement.md) — the measurement,
  the four leverage tables, and the check 10 demanded.

Machine-readable beside `criteria/production-ownership.json`; 22 band probes in
`criteria/probes/<category>/`; recorded judge answers in
`criteria/judgments/<category>/`.

### The results

| category | criteria agreement | bands | verdict |
|---|---|---|---|
| Evaluation rigour | 54/55 | 11 exact, 0 adjacent, 0 far | **PASS** |
| Agentic systems | 54/55 | 10 exact, 1 adjacent, 0 far | **LOOK** |
| AI-assisted coding fluency | 44/48, C5 not comparable | — | **unmeasured** |

**Judge setup, as asked: 05's proxy, not the acceptance test.** No provider credentials
in this environment either, so `deterministic` versus one recorded model judge over
eleven documents per category — four PDF fixtures and seven or eight band probes, with
the three unparseable fixtures withheld.

### What the leverage check found before any measurement

05's failure condition — *a category whose gate is its hardest question will not
converge however well it is worded* — does not fire for any of the three. Every gate
asks whether a thing exists at all, and every C5 (the reading, the judgment call) moves
the band by at most one. Both judges answered all four gates identically on all 45
answerable documents; every split is below the gate. The two properties are now under
test rather than argued: C1 moves the band from all 32 answer sets, C5 by at most one
band, for every category in `SLUGS`.

### The one that could not be measured, and why it was ordered first

05 said to write `AI-assisted coding fluency` first because `rule_share` 0 means nothing
masks a bad criterion. What it actually exposed is one step further out: **05's proxy
does not exist for a model-owned category.** C5 — *did the practice reach past the
candidate's own keyboard* — has no rule channel at any wording. Written as an alias
family it answered `yes` on `strong` off "eval **harness**" and on `slop` off "Helped
the **team**", because the vocabulary of a practice spreading is the vocabulary of
ordinary engineering and only the subject makes it this category's evidence. So the
deterministic judge abstains, names no band, and there is one judge.

That is a cleaner statement of 04's decision than 04 could make: `rule_share` 0 is not
"a weak channel", it is an absent one, and it costs the *measurement* as well as the
score. Band probe `8-tool-not-on-the-list` is the standing demonstration — `7-fluent`
with `Claude Code` swapped for `Goose`, four criterion splits from one substitution.

### The demand 10 added

Checked against the baseline's 198 findings, grouped by the reading behind each of the
108 invented names. Nothing recurring is unreportable, and **no criterion was added to
make that true** — the readings land on the criteria, on a deterministic rule, or on
`Resume craft`. So 10 does not get reopened and option B stays unnecessary. Two things
carried forward: the "activity, not outcome" reading (18 findings) is reportable only if
12 authors a criterion `content/bullet-invariants` answers, and the check itself rests on
a baseline that ran the *old* open-ended prompt, so it should be repeated on the first
run of the new one.

### Two things changed that 05 wrote

Neither relitigates a decision; both are what a second, third and fourth category
forced.

- **The band lookup became data.** Rules are `when` clauses in the JSON, evaluated in
  order. Four hand-written lookups would have been four totality arguments nobody could
  check by reading. `Production ownership`'s bands, leverage table and measurement are
  bit-identical after the change.
- **A judge may abstain.** A criterion with no rule channel is declared unanswerable
  rather than answered `no`, and a judge that cannot answer every criterion names no
  band. A judge that abstains and a judge that read the resume and found nothing look
  the same in a band, and they are not the same thing.

### Changed

- `docs/wayfinder/rubric-grounding/ai-assisted-coding-fluency-criteria.md`,
  `evaluation-rigour-criteria.md`, `agentic-systems-criteria.md` — new.
- `docs/wayfinder/rubric-grounding/three-categories-agreement.md` — new.
- `docs/wayfinder/rubric-grounding/criteria/` — three specs, 22 probes, three judgment
  files; probes and judgments moved into per-category directories.
- `scripts/criteria_probe.py` — generalised over categories; declarative band lookup;
  abstention; `--category`.
- `tests/test_criteria_probe.py` — every property parametrised over the four categories.
- `docs/wayfinder/rubric-grounding/MAP.md`, `production-ownership-criteria.md`,
  `production-ownership-agreement.md` — findings recorded, open questions narrowed or
  closed, moved paths repaired.
