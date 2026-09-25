type: task (AFK)
status: open
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
samples, up to 152 calls. The three fixtures whose roles do not parse are withheld
before any call, so 140 in practice. The raw replies go to `runs/`, which is
gitignored; the printed tables quote nothing and are what belongs here.
