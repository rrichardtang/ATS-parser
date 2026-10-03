type: task (AFK)
status: open
claimed: claude
blocked-by: —

# Hand the writer what the judge knew

## Question

What does the writer need in its prompt to aim at the criterion instead of guessing?

## What to build

Extend each target `rewrite_pass` builds, and `prompts.rewrite_user`, so the writer gets:

- **For a placed finding:** the criterion's `name`, `question`, `yes_requires` and
  `no_looks_like` from `ats/criteria/<slug>.json`, the finding's `evidence` quote, and
  the judge's `why` and `fix` uncut. Deterministic and slop findings keep their message
  and fix.
- **The role:** its title and the other bullets in it, marked as context, not to be
  rewritten.
- **The postings:** `prompts.digest_text(digest)`, the same summary the ranking judge
  already gets.

Give the ranking judge (`JUDGE_SYSTEM`, `judge_user`) each bullet's defect list as well,
so it ranks on whether the defect is fixed before how the bullet reads.

Watch the prompt size. Six targets with full criterion text each must stay inside the
rewrite pass's token cap.

## Done when

The prompts carry the above, tests cover the payload shape, and Felix has approved it.

## Found
