# Map: Rewrites that know what they are fixing

`wayfinder:map` — local-markdown tracker. Tickets are files in `tickets/`.
A ticket is **claimed** by setting `claimed: <name>` in its header, before any work.
The **frontier** is every ticket that is `open`, unclaimed, and whose `blocked-by` are all `closed`.

## Destination

Pass 3 rebuilt for the criterion rubric. The writer is handed what the judge knew, every
unmet criterion gets a fill-in-the-blanks draft, and a measurement says whether the
named problem goes away.

Done when a rewrite's prompt carries the criterion, its quote, the target postings and
the rest of the role, unmet criteria come back as drafts in the report, and 06 has
measured the fix rate before and after on the acceptance set.

**Status, 3 October: 02 is closed; 01 is built and waits on a key.** 01's harness runs offline
but its baseline needs `OPENAI_API_KEY`, and it must run on commit `14c6a89`, before 02
(see 01's Found). 03 and 04 are the frontier.

**Status, 3 October: a first five-document run (post-02) says the gate is the problem.**
Content rewrites fixed 1 of 9 findings, the same as the no-edit control; 64 of 106 targets
never shipped, 54 of them for missing `rewrite_margin` on the regex ranking score. Scoring
takes about 2.5 minutes a resume in the app; across the whole run, 69% of output tokens
are reasoning. See 01's Found. The
baseline on `14c6a89` is still not run.

## Why this map exists

`rubric-migration` moved scoring onto criteria and left one question unanswered in its
*Not yet specified*: *"What happens to the rewrite pass. Findings keyed on criterion ids
change what it is handed. Not looked at yet."* This map is that question.

A read of the code on 3 October found the pass still works the way it did before the
migration.

- **The writer sees a short complaint, never the target.** `rewrite_pass` hands each
  bullet its findings as `"<message> -> <fix>"`. For a placed finding the message is the
  judge's `why`, cut to 200 characters. The criterion's `question`, `yes_requires` and
  `no_looks_like` (in `ats/criteria/*.json`) and the finding's `evidence` quote never
  reach the writer.
- **The writer never sees the postings.** The digest goes to the content judge and to
  the rewrite *ranking* judge (`prompts.judge_user`), not to `prompts.rewrite_user`.
- **The writer sees one bullet alone.** No role, no neighbouring bullets.
- **Prompt and fact-check disagree.** `NO_INVENTION` allows "information present in the
  resume". `ensemble.audit_score` calls any quantity absent from *that bullet* an
  invented figure. A real number stated two bullets down is rejected.
- **The ranking judge and the final gate ignore the defect.** `JUDGE_SYSTEM` ranks on
  general writing quality. `ensemble.rank_score` scores four regex invariants, slop
  pattern hits and length. Neither asks whether the named problem is gone.
- **Unmet criteria never reach the writer, or the report.** `place` files a `no` with
  nothing to quote as an `UnmetCriterion`. `pipeline.analyze` keeps them out of the run
  metadata and the `Report` has no field for them. `/CONTEXT.md` calls them "the most
  important thing the candidate could be told".
- **Nothing measures rewrites.** The tests check the gates. No run has counted how often
  a rewrite fixes what it was asked to fix.

## Decided

- **3 October (the owner): context first, grading kept.** The writer is given
  everything the judge knew before it writes. The final gate stays: the writer is a
  model and can ignore its context, and the gate is how 06 tells whether the context
  helped.
- **3 October (the owner): unmet criteria get fill-in-the-blanks drafts.** A "new
  write" uses the rewrite machinery and `NO_INVENTION` unchanged: every fact the resume
  lacks is a typed `[add: …]` placeholder. Asking the candidate questions first was the
  other option. It gives truer bullets but needs a back-and-forth step the app lacks, so
  it is out of scope here.

## Tickets

| # | Title | Blocked by |
|---|---|---|
| 01 | Measure what rewrites fix | — |
| 02 | Hand the writer what the judge knew | — |
| 03 | One rule for where a fact may come from | — |
| 04 | Unmet criteria come back as drafts | — |
| 05 | The final gate asks whether the defect is gone | 01, 02 |
| 06 | Measure again | 01, 02, 03, 04, 05 |

01 should record its baseline before 02 lands. If no key is available then, 06 checks
out the commit before 02 for the baseline instead.

## Not yet specified

- **Where drafts sit in the report.** Beside the unmet criterion they answer, or in the
  rewrites section. 04 decides, and it touches the template.
- **Whether the rewrite passes move to `high` effort.** `weights.toml` keeps them at
  `medium` "until something measures them". 01 is that something; the switch is a
  separate call once there is a number.
- **The summary.** Only bullets are rewritten. A summary finding is dropped by
  `rewrite_pass` because `summary` is not a bullet locator.

## Out of scope

- Any rubric decision. Criteria, bands and weights are `rubric-grounding`'s.
- Asking the candidate questions before writing.
- Applying rewrites automatically. They stay proposals in a diff.
