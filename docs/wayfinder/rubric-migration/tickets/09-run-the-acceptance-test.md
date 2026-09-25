type: task (AFK)
status: closed
claimed: claude
blocked-by: 07, 08

# Run the acceptance test on the new rubric

## Question

The other map's Destination asks for a category set defined *"such that two different
LLM judges scoring the same resume land within a stated tolerance of each other."* That
sentence has never been tested against two providers on the rubric being designed.

Five categories have verdicts and all five come from the same proxy: a deterministic
judge against one recorded model judge, on documents written to exercise the rubric.
`Production ownership` LOOK, `AI-assisted coding fluency` unmeasured, `Evaluation
rigour` PASS, `Agentic systems` LOOK, `Resume craft` LOOK. Every one of those documents
says so in its own method section, and every one is a proxy.

Run the real thing. `scripts/agreement_harness.py` exists (06) and the baseline ran it
against the old rubric; 05 and 11 both flagged that it reads `score` and `band` from a
reply rather than criterion answers, so it needs teaching before it can measure this.
**Criterion agreement is the primary measurement, with band agreement derived from it** —
04's ask, and the reason is measured: 05's two splits were indistinguishable at band
level and needed opposite fixes.

## Two things to check that the proxy could not

- **`AI-assisted coding fluency` has never been measured at all.** Its C5 has no rule
  channel at any wording, so the deterministic judge abstains and the proxy has one
  judge. This is the first number that category will ever have.
- **`Resume craft` is where this should fail first, and the reason is pre-registered.**
  Its band is a defect count with no gate, so leverage is uniform and every criterion
  split costs one adjacent band — two splits anywhere is a failure where a gated
  category survives them. 12's open item names the likely cause: C4 and C5 are not
  independent, and the repair was deliberately left unapplied so that this run could
  find it honestly.

## The bar may not survive the run

*Two providers within 5 points per category* was set against a rubric that emitted
numbers. Under a band lookup the smallest possible disagreement is one band, which on
`Production ownership` is 17 to 23 points. Restating the bar in bands rather than points
is a rubric question, so it goes back to the other map — but this is the ticket that
produces the evidence for it.

Needs provider credentials, and needs 08's test set to be worth running on.

Done when: the acceptance test has been run against two providers on documents nobody
wrote in order to pass it, criterion agreement is reported per category with band
agreement derived from it, and the result is written up wherever it contradicts or
confirms the five proxy verdicts.

## Built, 25 September: the harness reads criterion answers

The harness could not measure this rubric. It read `score` and `band` from each reply,
and since 05 a reply carries neither, only criterion answers. So on a live run both its
per-category tables would have come out empty, and only the composite rows would have
had numbers.

- **Per-criterion agreement** (`agreement.CriterionAgreement`), the primary
  measurement. For each criterion and resume: the providers agree, disagree, or one of
  them is **unstable** (answered both yes and no across its own reruns). Unstable
  resumes are counted apart rather than folded into either side, because 07's second
  run showed one judge moving two bands on the same document. Krippendorff's alpha,
  nominal, between providers.
- **Band agreement derived from the answers.** `agreement.band_of` looks the band up
  with `rubric.band_of`, the same lookup the report uses, when a reply names none. Band
  order defaults to the specs' shared ladder, E to A.
- Repeated runs were already there: `--samples`, default 2 per provider.

The run itself is left: it needs both keys, which this session does not have.

    .venv/bin/python scripts/agreement_harness.py --acceptance-set --resume <resume.pdf>

That is 38 documents (7 fixtures, 30 drawn, the owner's resume) × 2 providers × 2
samples, up to 152 calls. Three fixtures are skipped before any call (`two_column`
and `hidden_text` are withheld because their roles do not parse, and `scanned` has no
text layer), so 140 in practice. The raw replies go to `runs/`, which is
gitignored; the printed tables quote nothing and are what belongs here.

## The first attempt ran silent, and could have lost everything

The owner started the run and saw nothing for over five minutes. That was expected:
resumes are judged one after another and each waits on its four calls. But reading the
code turned up two faults behind the silence, both fixed:

- `ensemble.gather` let a call past its 180 s timeout raise out of the pool. The pool
  then waited for the slow call anyway, and the exception ended the sweep. A slow call
  is now a failed call, recorded like any other. This path is shared with the app's own
  passes, which had the same fault.
- The harness saved only at the end, so a crash or Ctrl-C discarded every call already
  paid for. It now saves and prints a progress line after each resume.

## The run, 25 September

Run by the owner with both keys: `anthropic:claude-sonnet-5` and `openai:gpt-5.6-luna`,
2 samples each, on 38 documents (7 fixtures, 08's 30 drawn documents, the owner's
resume). Three fixtures were skipped before any call (`two_column`, `hidden_text`
withheld; `scanned` has no text layer), so 35 documents were judged, 140 replies, 47.4
minutes, no failed calls. The raw run is `runs/agreement-20260925T034102Z.json` on the
owner's machine, gitignored. The temperature did not reach either provider (both
current models dropped the parameter), so reruns measure each provider's own default
sampling.

### Criterion agreement, the primary measurement

875 criterion readings (25 criteria × 35 documents). **Unstable 107, disagree 59,
agree 709.** A provider changing its own answer between two samples of the same document
happened almost twice as often as the two providers disagreeing.

| category | agree | disagree | unstable | alpha, lowest to highest |
|---|---|---|---|---|
| `Production ownership` | 129 | 18 | 28 | 0.27 (C4) to 0.67 |
| `Resume craft` | 133 | 14 | 28 | 0.27 (C3) to 1.00 |
| `Agentic systems` | 133 | 14 | 28 | 0.67 to 0.81 |
| `Evaluation rigour` | 145 | 10 | 20 | 0.71 (C3) to 1.00 |
| `AI-assisted coding fluency` | 169 | 3 | 3 | 0.66 to 1.00 |

The weakest criteria: `production-ownership/C2` (11 unstable, alpha 0.48), `/C3`
(0.47), `/C4` (0.27), `resume-craft/C2` (10 unstable, 0.42) and `/C3` (0.27).

### Bands, derived from the answers

| category | exact | adjacent | far | unstable | alpha | verdict |
|---|---|---|---|---|---|---|
| `AI-assisted coding fluency` | 34 | 0 | 0 | 1 | 1.00 | look |
| `Evaluation rigour` | 24 | 3 | 0 | 8 | 0.93 | FAIL |
| `Agentic systems` | 19 | 3 | 1 | 12 | 0.74 | FAIL |
| `Resume craft` | 7 | 8 | 0 | 20 | 0.56 | FAIL |
| `Production ownership` | 9 | 0 | 7 | 19 | 0.33 | FAIL |

### Composite

Between the two providers' mean composites (no-deduct): 26 pass, 6 look, **3 FAIL**
(`05-career-changer-eval` 9.8, `29-returning-agentic-corporate` 9.8,
`30-junior-genai-product` 11.8). The owner's resume: 1.0. The composite passes on 26 of
35 while four categories fail at band level, because a category disagreement is diluted
by its weight and by averaging two samples per provider.

### Findings

Placed-finding agreement is at or below chance on every document under every key: the
highest kappa is +0.00. Two providers naming a defect do not name it in the same place
more often than random flagging would.

## Against the five proxy verdicts

| category | proxy | this run |
|---|---|---|
| `Production ownership` | LOOK | **FAIL**, the worst: 7 far splits, alpha 0.33 |
| `AI-assisted coding fluency` | unmeasured | look, near-perfect. Probably a floor: on these documents almost every answer is likely `no`, which agrees by construction. Check prevalence in the raw run before crediting the category. |
| `Evaluation rigour` | PASS | **FAIL** by the verdict rule, but alpha 0.93. It fails on 3 adjacent splits and 8 unstable documents |
| `Agentic systems` | LOOK | **FAIL**, 12 unstable |
| `Resume craft` | LOOK | **FAIL**, 20 unstable |

**The pre-registered `Resume craft` prediction was wrong about where.** It said the
category would fail first, through C4 and C5 not being independent. It fails, but C4
and C5 are its two best criteria (agree 34 and 33, alpha 1.00). Its failure is C1 to C3
and instability. C4 and C5 agreeing is most likely the same floor migration 08 found (C5
`yes` on 0 of 30 full-length documents): both judges say `no` because both criteria get
harder with length. It is not evidence the criteria work.

## What it means

1. **Repeatability is the first problem, not agreement between providers.** 107 unstable
   readings against 59 disagreements. No wording fix aimed at making two providers agree
   can pass while one provider disagrees with itself this often.
2. **The band verdict rule cannot be passed at this sample size.** More than one adjacent
   split in 35 documents is a FAIL, so `Evaluation rigour` fails at alpha 0.93.
   Krippendorff's usual reading is 0.800 or above reliable, 0.667 to 0.800 tentative.
   On that reading: `AI-assisted coding fluency` and `Evaluation rigour` pass, `Agentic
   systems` is tentative, and `Resume craft` and `Production ownership` fail. Restating
   the bar is the other map's decision; this is the evidence.
3. **`Production ownership` C2 to C4 and `Resume craft` C2 and C3 are where to work.**
   They carry most of both the instability and the disagreement.
4. Placed findings do not agree beyond chance, so a finding's location is not yet a
   stable thing to show a user as fact.

## Closed

Done when the test has run against two providers on documents nobody wrote to pass
it, with criterion agreement reported and bands derived from it, and the result set
against the five proxy verdicts. All three are above. The results go back to the other
map as rubric questions.
