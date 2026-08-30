type: grilling (HITL)
status: open
claimed:
blocked-by: 11

# Criteria for Resume craft, or an admission that it cannot have them

## Question

`Resume craft` is the fifth judged category and the one 05 singles out as the one to be
careful with:

> subtract what `ats/human.py` already checks deterministically and what remains is
> weighed, not countable, and criteria will not make it converge.

That is a prediction of failure from the ticket that invented the format, and it is why
this is split from [11](11-criteria-for-the-three-remaining-behaviour-categories.md)
rather than being its fourth item. The three behaviour categories should not wait on it,
and it should not be attempted with three sets' worth of momentum behind it.

It is a **grilling** ticket, not a prototype, because the first question is whether to
write criteria at all — not how to word them.

## Why it is different from the other four

- **It is not a behaviour.** The other four are things the corpus asks candidates to
  have done, counted by document frequency. `Resume craft` has no df to derive from; 04
  gave it an authored weight for that reason.
- **`rule_share` 0.7, the highest.** Most of its score already comes from the
  deterministic channel. So the criteria are being asked to carry the *smallest* share
  of score of any category — while being the hardest to write.
- **The baseline says it is the worst.** `Writing quality`, its predecessor, had the
  largest residual in the run: 10.1 mean, 20.3 max, and only 2 of 7 resumes inside the
  bar. On `two_column` all four samples agreed the bullets were telegraphic and landed
  on 50, 55, 57, 48. That is the shared-reading-different-number failure in its purest
  form, and it is the failure 04's output form was supposed to remove.
- **The overlap problem is real, not theoretical.** `ats/human.py` and the `scan/*` and
  `content/*` rules already check passive voice, first person, bullet length, duplicate
  bullets, weak openers and quantification rate. 07 is deciding where those file. What
  is left after subtracting them is the question this ticket has to answer, and 07
  should land first if it is going to.

## The three outcomes, and none of them is a bad result

1. **Criteria that converge.** 05's prediction was wrong, and the format is more general
   than its author thought. Requires the same artifacts 11 produces.
2. **Criteria that do not converge, measured.** The category keeps its deterministic
   channel and the model's 0.3 share is dropped or held at a fixed value. `rule_share`
   0.7 makes this survivable in a way it would not be for a behaviour category — the
   score mostly does not depend on the model here.
3. **No model channel at all.** `Resume craft` becomes deterministic, `rule_share` 1.0.
   Clean, and it costs the candidate the qualitative reading a resume's craft arguably
   needs most.

Outcome 3 is the one to hold in view, because 10 makes it sharper than it looks: with
the open-ended search gone, a `Resume craft` with no criteria is a category that says
nothing qualitative at all. If that is the answer, say so deliberately rather than
arriving at it by failing to word criteria well enough.

## Also here, because it cannot be settled without this

**Which gate `Resume craft` belongs to.** It merges `Recruiter scan` (`Gate.RECRUITER`)
with `Writing quality` (`Gate.MANAGER`) and must pick one. `report.py` groups findings
by gate and `score.py` derives the parser and human sub-scores from it, so this moves
visible output. 04 left it as a reporting question; it is tracked in the map's *Not yet
specified* and this is the ticket that has the context to close it.

Done when: either criteria with a measured verdict as 11 produces, or a recorded
decision that `Resume craft` has no model channel — with the measurement that supports
it, not the difficulty of writing them. The gate question answered either way.
