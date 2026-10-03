type: task (AFK)
status: closed
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

Built 3 October. Offline tests only; no key here, so no live call has read the new prompt.

- **Defects.** `passes.target_payload` builds each target. A placed finding (its `rule_id`
  is a key of `passes.criteria_by_rule_id`) becomes `{criterion, evidence, why, fix}`;
  deterministic and slop findings keep the `"<message> -> <fix>"` string. The criterion's
  `name`, `question`, `yes_requires` and `no_looks_like` go once into a CRITERIA section
  (`passes.referenced_criteria`), keyed by id, rendered by `prompts.rewrite_user`.
- **Not uncut.** The judge's `why` reaches the writer as `Finding.message`, already cut to
  200 characters by `place`. The Finding model is not widened; `fix` was never cut.
- **Role.** Each target carries `role` (title, or heading, plus company) and
  `other_bullets_in_role_context_only`. The system prompt says to rewrite only `bullet`.
  It does not tell the writer it may borrow figures from the other bullets; the fact-check
  still reads the bullet alone (03's contradiction, untouched).
- **Postings.** `rewrite_user` takes the digest. `pipeline.generate_rewrites` already
  passed `config.jd_digest()`; a test now pins it.
- **Judge.** `judge_user` payloads carry `defects` (criterion `name: question`, or the
  message line). `JUDGE_SYSTEM` ranks on fixed defects first, then quality, and still
  does not judge truthfulness.
- **Budget.** `rewrite_eval.writer_prompt` replaces the inline fake prompt: the six
  largest real payloads (role context included), five 260-character defects each, the
  thirty largest criteria in CRITERIA, and the digest. A test compares it with the
  real prompt for the `strong` fixture.
- **Size, `strong` fixture** (6 bullets, 3 placed findings each, system plus user):
  7079 chars before (1367 + 5712), 17122 after (1834 + 15288), about 4300 tokens.
  Most of the growth is the other bullets repeated per target and the posting digest;
  CRITERIA is one copy of each of 3 criteria. Input only, far inside the reply caps.
