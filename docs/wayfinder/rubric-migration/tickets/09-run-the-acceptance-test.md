type: task (AFK)
status: open
claimed:
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
