type: grilling (HITL)
status: open
claimed: claude
blocked-by: —

# What makes two findings the same finding?

## Question

The baseline run measured findings agreement between two judges at **0.03**. Re-keyed
on the locator alone it is **0.51**, and on the quoted evidence span **0.36** — the same
findings, the same run, a 17× swing decided entirely by what "the same finding" means.
See [../baseline-agreement.md](../baseline-agreement.md).

The cause is that both halves of today's key are text the model invents. Across 198
findings the two providers produced **108 distinct `rule_id`s**, sharing **5**.
`missing-evaluation-methodology`, `-detail`, `-context`, `-method` and
`missing-eval-methodology` are five spellings of one defect, 33 findings between them.
`prompts.CONTENT_SYSTEM` already asks for a name "reused verbatim across every finding
of that kind"; asking harder is not a fix, because the model has no list to reuse *from*.

This is not only a measurement problem. `/CONTEXT.md` defines a rule id as naming the
*kind* of defect, and `Report.grouped` and the ledger both total by it. At 108 names for
198 findings, one defect renders as five cards in the report a candidate reads.

Three things to settle, and the third is the one with teeth:

1. **The key.** What identifies a finding for agreement measurement — locator, evidence
   span, or a pair. The harness reports one number today and it is the least informative
   of the three.
2. **The vocabulary.** A closed list the model chooses from, rather than a name it
   invents. What is on the list, and what happens to a defect that does not fit one.
3. **Whether the model needs a findings vocabulary at all.** 04 already gives it a
   closed vocabulary — the criteria. A finding could be *the evidence for a criterion
   answered `no`*, in which case the criterion id is the rule id, the list is fixed by
   construction, and this ticket collapses into 04. The cost is that a defect no
   criterion asks about becomes unreportable, and the slop pass and the deterministic
   rules both emit findings that no criterion covers. Settle whether the model's
   findings are criterion evidence, a separate channel with its own list, or both.

Note the constraint 03 leaves standing: model findings are evidence for the band and
the fix list, and no longer deduct. So this decides what the candidate reads, not what
the score is — which lowers the stakes on getting the list exhaustive and raises them on
getting it legible.

Also recorded, because it bears on 1 and is easy to miss: within-judge locator overlap
(0.57) barely beats between-judge (0.51). Finding localisation is unstable inside a
single judge, so ensembling two providers does not fix it and a stable key will not
either.

Done when: the key is chosen and `ats/agreement.py` reports it, the vocabulary question
is answered one of the three ways above, and whichever answer is taken is stated
precisely enough that `prompts.py` could be changed without a second decision.
