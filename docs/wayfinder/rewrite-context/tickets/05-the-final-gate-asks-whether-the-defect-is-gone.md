type: task (AFK)
status: closed
claimed: claude
blocked-by: 01, 02

# The final gate asks whether the defect is gone

## Question

Should a rewrite that reads better but leaves the named defect in place ship?

## Why it matters

`ensemble.rank_score` rewards four regex invariants, no slop hits and staying under 32
words. A candidate can beat the original by `rewrite_margin` on those and still leave
the criterion unanswered. 02 tells the writer and the ranking judge the defect; this
ticket makes the gate check it.

## What to build

Before a candidate ships, rerun the deterministic rules that fired on the original
against it. A rule that still fires blocks it, the same way an audit problem does. Use
01's numbers to decide whether a model re-check of the criterion is worth its calls as
well, or whether 02 already fixes enough without it.

## Done when

The gate blocks a candidate that keeps its rule defect, tests cover it, the decision on
the model re-check is recorded here with 01's number behind it, and Felix has approved it.

## Found

**The approach changed, 3 October.** The ticket asked for a rule that blocks a candidate
which keeps its rule defect, on top of the existing gate. 01's first live run (five drawn
documents, post-02 code) showed the existing gate was the problem: 64 of 106 targets never
shipped, 54 of them because no candidate beat the original by `rewrite_margin` on
`ensemble.rank_score` (four regex invariants, slop hits, a length penalty over 32 words),
10 for the fact-check. `rank_score` never looks at the named defect, so the margin threw
away most rewrites for reasons unrelated to the defect and let through ones that fixed
nothing: content rewrites fixed 1 of 9, the same as the no-edit control. So the margin rule
was replaced, not added to.

**The gate now (`ensemble.select_rewrite`).** A candidate ships only if:

1. the fact-check is clean (`audit_score`: no problems, no regression), as before;
2. no deterministic rule fires at that bullet that did not fire on the original;
3. when any fired on the original, at least one of them no longer fires.

Content-only (criterion) and slop-pass targets have no cheap check, so 1 and 2 suffice and
the ranking judge's order decides (02 made it rank on the defects first). Among passing
candidates the judge's order wins when it ran (polished first, then every candidate in the
judge's order, not just its #1). Otherwise (Economy, or the judge skipped or failed the
bullet) the candidate fixing most deterministic defects wins, `rank_score` breaking ties;
a bullet the judge failed is no longer polished. `rewrite_margin` is gone from
`weights.toml`, the pipeline and the harness.

- `ensemble.bullet_defects(resume, locator)` reruns `rules.content_mechanics` and
  `slop.analyze` (bullet-scope patterns and `slop/portable`) on a copy of the resume with
  that one bullet replaced (`Resume.with_bullet`, now also used by `rewrite_eval.swap`) and
  keeps the rule ids at that locator. Pure and offline. `human` and `keywords` have no
  bullet-scoped rules, so they are not run.
- Not covered: document-scope slop, the experience-level rhythm and synonym-cycling checks,
  and a duplicate that the candidate creates with a *later* bullet (the duplicate rule fires
  on the later one, not at the candidate's locator).
- `hack_detected` now means a candidate that fixed a deterministic defect but failed the
  fact-check: winning on what the gate selects for while losing on what it never trades
  against. `scripts/hacking_sweep.py` runs the new gate through a tested `shipped()`; no
  hack ships at any N.
- Harness reason buckets: `no candidates`, `audit rejected`, `new defect`, `fixed nothing`
  (the furthest any candidate got). `no margin` is gone.

**Model re-check of the criterion: not now.** 01's numbers: the content fix rate was 1 of 9,
equal to the control's 1 of 9, on n=9. That is too few to say whether a re-check would
catch anything, and each re-check is another call at the judge's effort while the owner
has rejected added latency (scoring already takes about 2.5 minutes). Revisit in 06 with a
larger sample.
