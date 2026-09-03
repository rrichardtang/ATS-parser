type: prototype (HITL)
status: closed
claimed: claude
blocked-by: 04

# Draft score bands for one category, and test they hold

## Question

Can a band definition actually be written in evidence terms tightly enough that two
judges agree within 5 points? Write the bands for the single highest-stakes category
and run them, rather than writing five sets and discovering the format does not work.

Use the agreement harness (06) against the fixtures. If two judges cannot converge on
one category with bands in front of them, the format is wrong and the remaining four
should not be written yet.

Done when: one category has full band definitions, measured agreement across the
fixture set, and a verdict on whether the format generalises.

## Answer

**The format holds for `Production ownership`, at LOOK rather than PASS, and it
generalises to two of the remaining four categories on a stated condition.**

- Criteria and the band lookup: [../production-ownership-criteria.md](../production-ownership-criteria.md)
- Measurement and verdict: [../production-ownership-agreement.md](../production-ownership-agreement.md)
- Probe: `scripts/criteria_probe.py`, tests in `tests/test_criteria_probe.py`
- Machine-readable criteria, band probes, recorded judge answers: [../criteria/](../criteria/)

Per 04 this is criteria, not band prose: five binary evidence questions, each answered
with the quote that settles it, and a band lookup from the answers. Five bands, E to A.

**Measured**: two judges (deterministic band application, one model judge), eleven
answerable documents, **53/55 criterion answers identical, 10 exact bands, 1 adjacent,
0 far → LOOK.** A pass that wants another look, one wobble from failing.

**The fixture set could not do this on its own.** Four of the seven carry the same
bullets, three carry almost nothing, and every one that can be answered lands in band A
or band E — three of five bands unreachable. Seven short band probes were written for
the boundaries, in `../criteria/probes/`.

**Three findings worth more than the verdict:**

1. **Criterion output is measurably more diagnosable than a band label**, which is what
   04 claimed. The two splits look identical at band level but need opposite fixes: C3
   is a vocabulary gap (one alias family, fixable in the criterion), C2 is a channel
   defect (no regex distinguishes a name from a hyphenated adjective, so it cannot have
   a rule channel at any wording). Only criterion-level output separates them.
2. **A criterion's cost is set by its position in the band lookup, not by how hard it
   is to answer.** C1 moves the band from all 32 answer sets; C5 — the one that reads
   as most a matter of judgment — moves it from 2, and never by more than one band.
   Spend the wording budget on the gate criterion, not the subtle one. Every category
   needs its own leverage table, and one whose gate is its hardest question will not
   converge however well it is worded.
3. **A category must be withheld, not guessed, where the parse cannot carry it.** Every
   criterion asks about a bullet inside a role. Answering them anyway on `two_column`
   and `hidden_text` makes the judges disagree about what the document is, not about
   the criteria — and the parser gate has already charged for that defect.

**Generalisation**: a criterion generalises when both judges can point at the span that
settles it. `Agentic systems` and `Evaluation rigour` are the same shape and should
transfer nearly directly. `AI-assisted coding fluency` is answerable but has no rule
channel by 04's own decision, so criterion agreement is the only agreement it has —
measure it first, not last. `Resume craft` is the one to be careful with: subtract what
`ats/human.py` already checks deterministically and what remains is weighed, not
countable, and criteria will not make it converge.

## What this ticket did not do

**The map's acceptance test was not run.** `scripts/agreement_harness.py` exists, but
this environment has no provider credentials, so there is no two-provider,
two-sample run. The two judges compared were the deterministic criterion answerer and
one model judge; that measures where the criteria wording leaves room to differ, not
whether two providers diverge elsewhere. 06 still owes that number, and cannot produce
the criterion half of it until it reads criterion answers from a judgement rather than
`score` and `band`.

03's second experiment — band-only versus band-plus-a-point-inside-it — is specified in
the criteria document but not run, for the same reason. It is one prompt variant and
one harness run once credentials exist.

An earlier pass of this ticket, before 02/03/04 landed, wrote bands for `Coverage` on
the map's then-current framing. 04 dissolved `Coverage` into the behaviour categories
and replaced band prose with criteria, so that work was removed rather than merged.
