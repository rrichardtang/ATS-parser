type: prototype (HITL)
status: closed
claimed: claude
blocked-by: 03

# The content prompt asks the criteria

## Question

`prompts.CONTENT_SYSTEM` asks the model two things: score five categories 0–100, and
find what is missing. 03 removed the first and 10 removed the second. Neither removal
has reached the file.

The model now answers **criteria** — for each category, five binary questions, each
with the quote that settles it. It names no band and no number; the band is a lookup
and the value is a lookup from the band.

## What 10 specified, restated so it needs no second decision

- `CONTENT_SYSTEM` stops asking *"what critical information is MISSING?"* — the
  open-ended search — and asks the criteria, one question at a time.
- **`"pattern"` leaves the schema.** Nothing in the reply names a kind of defect; the
  criterion being answered is the kind. `passes.py:104`'s
  `_rule_id("llm", item.get("pattern"), "content")` becomes a lookup of the criterion
  id and can no longer mint a new id from model text. That single line produced 108
  distinct names for 198 findings in the baseline.
- Each answer returns `yes`/`no` plus, where there is one, the quote and the locator.
- **A reply naming a criterion that does not exist is dropped**, exactly as an
  unevidenced finding is dropped today.
- **Locators are resolved, not trusted.** 10% of the baseline's locators named nothing
  in the parsed resume — `interests.bullet[0]`, `exp[0]`, `skills`, and one compound
  `exp[0].bullet[0] / exp[1].bullet[0]` that breaks "one defect in one place" outright.
  `passes.py` already resolves locators against real bullet text for the rewrite pass;
  that resolution moves earlier and applies to all of them. A finding whose locator does
  not resolve is **demoted to an unmet criterion, not discarded** — the reading survives,
  the fictional address does not.

## The two objects a `no` produces

10 §3, and the schema has to carry both:

- **Unmet criterion** — the absence case. No locator, no quote, because there is nothing
  to point at. *"Nothing in the resume says any work reached production."* This is what
  the band lookup reads and what the report leads with.
- **Placed finding** — present-but-weak, where the resume does say something and what it
  says is the problem. Quote and locator required.

A criterion answered `yes` may also carry placed findings; they are evidence, not
advice, and the report must not render them as fixes.

## Withholding

05's rule, and it is not optional: every criterion asks about a bullet inside a role, so
a document whose roles did not survive extraction has its judged categories **withheld**,
not guessed and not zeroed. The parser gate has already found and charged for that
defect; scoring it as well charges one fault twice. `two_column`, `hidden_text` and
`scanned` are the fixtures that exercise it.

Done when: the content pass sends criteria and parses criterion answers; ids come from
the specs rather than from model text; locators resolve or the finding demotes; unmet
criteria and placed findings are separate objects; and a document whose roles did not
parse is withheld.

## What was done

`prompts.CONTENT_SYSTEM` is gone. `prompts.content_system()` builds the prompt from
the five specs in `ats/criteria/`: every category, what it measures, and its five
criteria with the `yes_requires` and `no_looks_like` that anchor them. The questions
the model answers are therefore the same objects `rubric.band_of` reads — not a copy
of them — so the prompt cannot drift from the lookup. It is a function rather than a
constant so importing the package does not read five JSON files before anything asks
for a prompt.

Both removals landed. The open-ended *"what critical information is MISSING?"* is
gone, and so is *"Score each category 0-100"* — the prompt now says in as many words
that naming a band and giving a category a score are not the model's to choose.
`"pattern"` has left the schema: the model gets no findings vocabulary of its own,
because the criterion it is answering **is** the kind of defect.

### One array, not two

The reply carries criterion answers and nothing else. A separate `findings` array
would have re-opened the vocabulary question through the back door — the model would
have had to name each defect again to file it. So each answer carries `yes`/`no`,
the quote and the locator where there is one, a one-line `why`, and a `fix` for the
`no` cases; both objects §3 defines are derived from that in `passes.place`.

### The two objects, and which quotes survive

- A `no` with a quote whose locator resolves is a **placed finding**, `rule_id` =
  `<slug>/<criterion id>`.
- Every other `no` — no quote, no locator, or a locator naming nothing in the parsed
  resume — is an **unmet criterion**, carrying the model's `why` or, where it gave
  none, the criterion's own `no_looks_like`.
- A `yes` produces neither. Its quote is the evidence that settles the criterion and
  it stays on the answer. Rendering it as a finding would be the report handing
  somebody a fix for the thing they did right, and the fix list is not the place to
  discover that distinction.

Locators are resolved against `resume.bullets` plus `summary` — the same resolution
the rewrite pass already did before spending a call, moved earlier and applied to
every answer. I did **not** try to recover a real locator from the quote the way the
slop pass does; 10 says demote, and this is not the place to re-decide it. The other
half of that defence is in the prompt: `content_user` now lists the PLACES a locator
may name, with the text at each, so a judge has no reason to invent `exp[0]` or
`skills` in the first place.

`_rule_id`, which minted an id from model text and produced 108 names for 198
findings, is now reachable only from the slop pass, whose ids were never the problem.

### Withholding

`passes.withholding_reason` returns why a document cannot be judged, or `""`.
`content_pass` checks it **before** the calls — a withheld document costs nothing —
and returns `meta["withheld"]` naming the five judged categories plus the reason.
`agreement.judge_resume` checks the same function and skips, beside its existing
no-text-layer skip, so the harness cannot report agreement numbers on the one kind
of document the pipeline refuses to judge. `two_column`, `hidden_text` and `scanned`
all parse to **zero roles**, which is the shape the rule was written for.

### The union, and the fold that is deliberately missing

`content_pass` unions the **report** channel across judgements: placed findings on
`(rule_id, locator)` — 10's key of record, now that both halves are closed — and
unmet criteria on the criterion id, one per criterion per resume.

It does **not** fold the **scoring** channel. Two judges answering the same five
questions differently is a criterion split, not a spread of numbers, and 06 owns what
that buys. The unfolded answers stay on each `ContentJudgment`, reachable as
`passes.criterion_answers(j.categories)`, which needs nothing but the specs.
`ContentJudgment` stores `unmet` rather than deriving it because that split needs the
parsed resume, which a saved harness run does not carry.

## What this costs until 06 lands

Stated plainly, because a reader of a report in the meantime deserves to know:

- **No judged category has a model channel.** The model authors no number, and
  turning answers into a value is 06. `pipeline.analyze` therefore blends nothing,
  and says so in a note on every run that reached the judge. `Production ownership`,
  `Evaluation rigour` and `Resume craft` show their deterministic channel alone and
  read high; `Agentic systems` and `AI-assisted coding fluency`, which have no rule
  channel at all, come out `n/a` — `CategoryScore.assessed` doing exactly the job 03
  built it for.
- **A withheld category is still not a number.** `content_pass` withholds and says
  so, but `score.build` has not been told: with no judge answer and a positive
  `rule_share`, the three categories that have rules ride at 100 on a document whose
  roles never parsed. That is 06's third item — *"a withheld category neither
  inflates nor deflates the composite"* — verbatim, and it is recorded on 06 rather
  than half-decided here.
- **`ensemble.combine_scores` is unreached** by the pipeline now. It is left in place
  because 06 is the ticket that decides what replaces it; nothing else calls it.

## Changed

- `ats/prompts.py` — `criteria_block()`, `content_system()`, and `places()`;
  `content_user` lists the locators an answer may name and asks for every criterion.
- `ats/models.py` — `CriterionAnswer` and `UnmetCriterion`.
- `ats/passes.py` — `criteria_index`, `criterion_answers`, `resolvable_locators`,
  `place`, `withholding_reason`; `content_judgments` builds both objects from the
  answers; `content_pass` withholds, unions on the key of record, and folds no
  answers.
- `ats/pipeline.py` — the withheld note, the interim note, and no blend to do.
- `ats/agreement.py` — `unmet` round-trips, withheld documents are skipped, and the
  docstrings say what the reply actually carries.
- `tests/test_llm_passes.py` — ids come from the specs; an invented criterion and a
  retired category are dropped; a `no` with nothing to point at is an unmet criterion;
  an unresolvable locator demotes rather than discards; a `yes` produces neither
  object; an unreadable answer is an abstention, not a `no`; two judges collide on
  kind and place; the prompt asks every criterion and no longer asks for a score; a
  document whose roles did not parse is withheld without costing a call.
- `tests/test_agreement.py` — the stub judge answers criteria; a withheld document is
  skipped by the harness; the capped-composite row is built rather than collected,
  because `hidden_text` is now withheld before a judge is asked.
- `CONTEXT.md` — *placed finding* and *unmet criterion* defined. `README.md` — what
  pass 1 asks.
