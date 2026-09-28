type: decision + build
status: open
claimed: claude
blocked-by: —

# Judges that give the same answer twice

## Question

Raised by rubric-migration 09. Over 875 criterion readings, a provider changed its own
answer between two identical calls 107 times; the two providers disagreed 59 times.
Five criteria carry most of it: `production-ownership/C2`, `/C3`, `/C4` and
`resume-craft/C2`, `/C3`. What change makes a judge answer them the same way twice?

## What the flips show

The owner printed every flip on those five criteria from the 25 September run: 43 in
all (12, 5, 7, 11 and 8). Read one by one, they fall into three patterns.

1. **The `no` run did not search (33 of 43).** Each criterion asks whether *any* bullet,
   or *every* role, shows something. A `yes` needs one example; a `no` needs every bullet
   checked, and the models do not check them. On `12-returning-rag` both providers said
   `no` on one sample and found "our claims assistant" on the other. On
   `20-genai-product-senior` one sample found "the customer-facing routing assistant" and
   the other judged a different bullet. Many `no` answers quote nothing.
2. **Same quote, opposite answer (10 of 43).** The criterion does not say where the line
   is. `strong`'s "Cut GPU spend 34% ... by profiling the serving path" was `no` then
   `yes` for post-launch work. "It was picked up again a year later and is still in use"
   went both ways from both providers. "We stayed on afterwards" split twice. "The
   pipeline" split as a named system; "enterprise partners" split as a purpose.
3. **The criterion's own rule misread.** Three `production-ownership/C2` flips turned on
   whether a name two bullets from the destination counts (C2 says same bullet). One
   `resume-craft/C2` run said `yes` for "satisfying the requirement for at least one role"
   on a criterion that says *every* role. One called "Helped the team to streamline
   various processes" a change.

## Decided, 25 September (the owner)

The boundaries for pattern 2, to be written into each criterion's `yes_requires` and
`no_looks_like` as worked examples:

1. **"Stayed on afterwards" with no work described is `no`** for
   `production-ownership/C4` (post-launch work). Staying is not work.
2. **"Still in use" is `yes` for `production-ownership/C3` (operational fact) and `no`
   for C4.** It says the system survived, not what the candidate did, so it earns credit
   once, where it belongs.
3. **A descriptive name is a named system; a bare category noun is not**
   (`production-ownership/C2`). The test: could an interviewer say "tell me about X" and
   both know which system? "The forecasting service", "the claims assistant", "the
   retrieval pipeline": `yes`. "The pipeline", "the service", "the system", "the model":
   `no`.
4. **Who paid is not what it was for** (`resume-craft/C3`). "Clients", "enterprise
   partners", and "customers" or "users" on their own: `no`. A user doing a task or a
   problem solved ("for dispatchers", "so support agents could answer without
   escalating", "for ticket triage"): `yes`. The deterministic judge's alias list, which
   counts "customers" and "users", changes to match.
5. **A system named elsewhere in the same role counts** for `production-ownership/C2`.
   A name in the skills section or in a different role does not. This loosens C2's
   "same bullet" rule on purpose: the rule was there to stop a listed tool counting as
   shipped, and a name two bullets up in the same role is the same system to any reader.

## Decided, 26 September (the owner): five readings

From a 5-resume run on the owner's machine, after the OpenAI locator fix
(`runs/agreement-20260926T224846Z.json`): 6 whole-answer flips on the five weak
criteria (`production-ownership/C2` ×3 -- both judges on `02`, OpenAI on `18`;
`resume-craft/C2` ×2 -- Claude on `02` and `24`; `production-ownership/C4` ×1 -- OpenAI
on `24`). Every flip was wholesale: all bullets of the resume moved at once, not one
bullet's reading changing against the rest, which points at the question admitting two
readings rather than at per-bullet noise. Of 35 per-bullet flip groups in the run, 29
did not change the whole answer.

The five readings, written into `yes_requires` / `no_looks_like`:

1. **`production-ownership/C2`: a word for what the system is FOR, no proper name,
   counts on its own.** "Built forecasting for build timelines" is `yes`, and so is
   plain "built forecasting" -- an interviewer can say "tell me about the
   build-timeline forecasting".
2. **`production-ownership/C2`: a generic stage or kind word needs one more
   detail.** "Ingestion", "processing", "ETL", "pipeline", "service" count only with
   one detail that picks the system out -- purpose, users, data, or stack. "Built
   ingestion on Airflow and Postgres" is `yes`. "The ingestion service" and "the
   pipeline" alone stay `no`.
3. **`resume-craft/C2`: building something new is a change.** "Designed and
   implemented an LLM-powered marking workflow" is `yes` -- a new thing that now
   exists is a difference.
4. **`resume-craft/C2`: a change the bullet doesn't attribute to the candidate's
   work is not a change.** "is now owned by the ops team", "retrieval quality dropped
   and nobody noticed" -- `no`.
5. **`production-ownership/C4`: still-used is not post-launch work,** consistent with
   the existing "still in use" ruling for C4. "The eval suite has been run on every
   release since, 40 releases" is `no` -- it says the suite is still used, not what the
   candidate did to it.

Round 1's text for readings 1 and 2 (commit a7b5821) stacked two overlapping sentences
that contradicted each other on "the ingestion" -- one said what-it-does alone was
enough, the other said a bare category noun wasn't. The owner's follow-up (round 2)
replaced them with one rule: a purpose word stands alone, a stage/kind word needs a
detail. Round 2 also sharpened reading 4 to name causation rather than leave the judge
to guess it, and added a sixth reading to `resume-craft/C2`:

6. **`resume-craft/C2`: designing or working on something without building it is not
   a change.** "Designed model architectures" is `no`.

**Not comparable to the 25 September baseline without qualification:** from 26
September, Claude runs at effort medium with a cached system prompt, which the 25
September numbers above predate. A rerun against this ticket's "Left" section is still
needed before closing it.

## Decided, 26 September (the owner): ask per bullet

- **Pattern 1: ask per bullet, let the program count.** Approved by the owner. Instead of "does any bullet...",
  the content pass answers the criterion for each bullet (or each role, for
  `resume-craft/C2`), and the code derives *any* or *every*. The model stops doing the
  search; the program does the counting, the same way each time. This is a change to
  `ats/prompts.py`, the reply parser and the answer shape, so it is a build, and it
  changes what `rubric.band_of` is handed. It also fixes pattern 3's quantifier misreads
  as a side effect.

### How it is built

Scoped to the five criteria this ticket is about; the other twenty keep one answer.

- Each of the five specs gains a `scope`: `any_bullet` for `production-ownership/C2`,
  `/C3`, `/C4` and `resume-craft/C3`, `every_role` for `resume-craft/C2`.
- For a scoped criterion the model returns an answer **for every bullet in PLACES**
  rather than one answer. The code derives the criterion: `any_bullet` is `yes` when
  any bullet is `yes`; `every_role` is `yes` when each role has at least one `yes`.
- A reply that leaves bullets out has not answered: the criterion is dropped as an
  abstention, as an unreadable answer is today, rather than read as `no`. Reading a
  missing bullet as `no` would rebuild the search failure this change removes.
- A derived `yes` carries the first `yes` bullet's quote and locator. A derived `no`
  is an unmet criterion, not a placed finding: there is no single bullet that is the
  defect.

## Done when

The five boundaries are in the specs and the deterministic judge; pattern 1 is decided
and, if adopted, built; and the acceptance run (migration 09's command) is repeated with
unstable readings on the five criteria measurably down.

## Built, 26 September

Both parts, each built by bob-the-builder and approved by felix-the-fixer.

- **Round A** (1de8759, b29be5e): the five boundaries are in the specs' `yes_requires`
  and `no_looks_like`. `resume-craft/C3` lost its bare "customer(s)" and "user(s)"
  aliases; `production-ownership/C3` gained "still in use" and "still running". The
  probe's `named_in` now searches the anchor's role, tracked with the anchor rather than
  looked up by bullet text, which felix caught mis-resolving a bullet repeated across
  roles.
- **Round B** (2d4a83c, 047ec1d): `production-ownership/C2`, `/C3`, `/C4` are `any_bullet`
  (role bullets only), `resume-craft/C3` is `any_place` (summary and bullets, because its
  question is about the resume) and `resume-craft/C2` is `every_role`. The model answers
  each place; `passes.derive_scoped`, called from `content_judgments`, derives one answer,
  so everything downstream is unchanged and saved runs still load.
  - A scoped criterion answered the old way (one answer) is an abstention on the live
    path, so the model cannot fall back to the unsearched answer.
  - A missing place abstains only when it could change the result: one `yes` settles
    `any_*`; one role answered all `no`, or with no bullets, settles `every_role`.
  - A place answered both `yes` and `no` counts as unanswered.
  - A derived `no` is an unmet criterion, never a placed finding, and shows the
    criterion's own `no_looks_like` (for `every_role`, the role that fell short).
  - The model quotes only on `yes` places, to keep the reply inside the token limit.

## Known gaps

- **The deterministic judge cannot see decision 3.** `SPECIFIC_TOKEN_RE` in
  `scripts/criteria_probe.py` matches tokens like `vLLM`, not descriptive names like
  "the forecasting service". The model is now told those count; the probe still says
  `no`. Expect the probe and the model to disagree on `production-ownership/C2`.
- **The probe also misses the 26 September readings.** `SPECIFIC_TOKEN_RE` says `no`
  to "Built forecasting for build timelines" and "Built ingestion on Airflow and
  Postgres" -- neither is a name-shaped token. `OUTCOME_VERBS` has no designed or
  implemented, so the `resume-craft/C2` probe says `no` to reading 3's example,
  "Designed and implemented an LLM-powered marking workflow", where the model says
  `yes`. Recorded, not fixed: the probe is not changed here.
- **Reply size is unmeasured.** Felix estimated 6–7k output tokens for a 15-bullet
  resume and 10–11k for 30, against a 16,000 cap that OpenAI's reasoning tokens also
  count against. A truncated reply fails loudly, not silently. Only a live run can
  confirm it.

## Left

Rerun migration 09's acceptance test (owner's machine, both keys) and compare unstable
readings on the five criteria against 25 September: `production-ownership/C2` 11,
`/C3` 5, `/C4` 6, `resume-craft/C2` 10, `/C3` 7. These are the `unstable` column of the
harness's per-criterion table for that run, which counts documents where either
provider flipped. They are one lower than the flip counts above wherever both providers
flipped on the same document (`12-returning-rag` on C2, `08-junior-mixed-quality` on C4,
`24-forward-deployed-senior` on `resume-craft/C2`, `18-terse-data-senior` on
`resume-craft/C3`). Then this ticket closes.

## Decided, 27 September (the owner): the finish line

**Why.** Three 5-resume runs (26 September) each ended in "maybe". Every ruling moved the
line and new borderline resumes landed on it. The flips that remained after the 26
September rulings are mostly the same quote read two ways, or a `no` given without a
quote where the other sample found one. Zero flips can't be reached with a judge whose
sampling can't be fixed (temperature doesn't reach current models).

**Finish line, decided before the run.** On all 30 documents of the acceptance set
(`corpus/resumes`, rubric-migration 08), with both providers and 2 samples:

- The composite spread between judges ("as built") is ≤ 5 on at least 27 of the 30
  documents.
- No category has a "far" band split, i.e. two judges two or more bands apart.
- Band instability within a judge is reported, not failed. This replaces the stricter
  band pass rule for this acceptance decision.

**What follows.** A pass closes ticket 15 and both maps' destinations. A fail means
building one majority-of-3 vote per judge and rerunning the same 30 documents once.
There will be no further wording rounds.

**Run settings.** Claude effort medium, cached system prompt, `--batch --max-tokens
25000 --openai-price 0.20,1.20 --budget 16` (worst case $15.59, a one-off raise of the
$3 test budget approved by the owner).

## Decided, 27 September (the owner): cut the cost, vote the app judge

**The run failed the finish line.** The 30-document acceptance run (both providers, 2
samples, batch) measured 28 documents. 25 of the 28 had a composite spread of 5 or less;
the three over were `12-returning-rag` 8.0, `13-eval-quality-promoted` 6.7 and
`29-returning-agentic-corporate` 5.2. `02-analyst-toward-ml` and `14-applied-ml-mid` had
no Claude composite, and the printed report did not say why. There were "far" band splits
in Evaluation rigour and Production ownership. Claude cost about $3.90. Claude Sonnet 5
costs about $0.11 per live check; the OpenAI judge costs about $0.01.

**Decisions.**

1. **The app judge is OpenAI `gpt-6-luna`, three tries, majority vote.** Claude is off in
   the app by default. It stays in the code and is switched on only by `weights.toml`'s
   `[ensemble] use_claude = true`. A Claude key alone, from the form or
   `ANTHROPIC_API_KEY`, does not turn it on.
2. **Test runs use the voted luna judge, with Claude as an audit judge.** Claude answers each
   resume once (1 sample, 1 try), through `--batch`.
3. **Finish line for the next acceptance run**, set before the run: on all 30
   acceptance-set documents, the luna-voted composite is within 5 points of Claude's on at
   least 27 of 30, and no category has a "far" band split (two or more bands) between
   them. The run has not happened.

**Built.**

- `ats/llm.py`: `OPENAI_MODEL = "gpt-6-luna"`, still Chat Completions with a JSON-object
  `response_format`. Current models get `reasoning_effort="medium"` and no temperature.
- The vote is `ensemble.vote`. Within one provider, each criterion gets one answer from
  that provider's tries, by majority among the tries that answered it. An abstention is
  not a `no`, so it does not count against `yes`: 1 yes and 2 abstentions is `yes`. A tie
  is `no` (1 yes, 1 no, 1 abstain): criteria are monotone, so `no` can only hold a band
  down. If no try answered, the criterion stays unanswered. Scoped criteria vote on their
  derived answers. A voted item copies the evidence, locator and why of a try that voted
  with the majority: the first one with a quote and a place, else the first. It records
  every try's answer under `votes`. `passes.vote_samples` groups try `i` into sample
  `i // votes`, so a failed try shrinks only its own vote. The lower-band rule
  (`combine_bands`) now applies across providers only.
- The app (`weights.toml`): `content_votes = 3` (economy 1, thorough 3) and
  `use_claude = false`. `pipeline.app_providers` is the one provider list every pass
  reads, so slop, rewrite, judge and polish cannot reach Claude either. A single provider
  no longer marks the report partial.
- Calls per resume check, keys for both providers present, default mode:

  | pass | before | after |
  |---|---|---|
  | content | Claude 1, OpenAI 1 | OpenAI 3 (voted) |
  | slop | Claude 3, OpenAI 3 | OpenAI 3 |
  | score total | 8 (4 Claude) | 6 (0 Claude) |
  | rewrites, only on request | 3 objectives × 2 providers + judge 1 + polish 1 = 8 | 3 + 1 + 1 = 5, all OpenAI |

  Each live call may add one JSON-repair call.
- The harness: OpenAI gives `--samples` (default 2) answers, each voted from `--votes`
  tries (default `content_votes`, 3), so 6 luna calls per resume. Claude gives
  `--claude-samples` (default 1) single-try answers, 1 call per resume. `--claude-only`
  and the new `--no-claude` leave one judge out. Claude's self-consistency is not
  claimed at 1 sample; the run notes say so. `ats/budget.py` counts every try, times
  the JSON-repair multiplier. The harness builds OpenAI clients with no SDK retries
  (`Provider.openai_max_retries = 0`), so a timed-out try is lost rather than resent and
  billed again, and it shrinks only its own vote. The app keeps the SDK's default
  retries. `--openai-price` is still required; gpt-6-luna's is `0.10,0.50`.
- Between judges, the harness measures what the app could report. The composite spread
  is the worst gap between any luna voted sample and Claude, not the gap between means.
  A judge whose samples name two bands is counted `unstable` and is still compared, so a
  far split behind a wobble is counted as far.
- The report names each resume's failed calls (`<resume>: call failed: ...`). It also
  names each resume where a judge gave no composite (`<resume>: no composite from
  <provider>: ...`), and the composite tally counts rows with one judge.

**Next run.** All 30 documents, `--docs` listing them, `--batch --max-tokens 25000
--openai-price 0.10,0.50`. The dry-run worst case is $7.22 (Claude $4.05, luna $3.17).
The default `--budget 3` refuses it, so it needs the owner's `--budget 8`.

## Decided, 28 September (the owner): the answer key

**Why.** The 27 September audit ran all 30 acceptance documents: luna voted from 3 tries,
against one Claude try (`runs/agreement-20260927T043041Z.json`, on the owner's machine).
It failed the finish line. The composite was within 5 points on 14 of 28 documents, and
there were 17 far band splits. Luna now agrees with itself: flips fell from 73 to 28. But
it scored lower than Claude on 26 of 28 resumes, by about 5 points on average. When two
judges are each consistent and still disagree, agreement can't say which one is right.
So the owner labelled the disagreements, and from now on the judge is scored against
those labels, not against Claude.

**The new `resume-craft/C1` bar.** The owner found every line that passed the old bar
("names the discipline") to be poor. A line above the first role must now state three
things: (a) the target role title, (b) the experience level, in years or seniority, and
(c) what the candidate builds or specialises in. All three are needed for `yes`. A
named project or product is a bonus and not required. The owner's `yes`: "Applied AI
Engineer with 3+ years shipping production LLM and agent systems. Builds independently
outside of work, including YunHai.io, a live AI travel planner, in beta." The `no`
examples: "Engineer. Data platforms, some product work." (no level, vague); "GenAI
product engineer, two years." (doesn't say what they build); "Seeking a senior
full-stack role with room to work closer to the model layer." (a wish, not what they
are); "Agentic AI engineer." (title only).

**The rulings**, now worked examples in the specs and the criteria docs:

- `agentic-systems/C1`: defining how an agent is evaluated is `no`. Designing agent
  behaviour without saying it was built is `no`, as in `resume-craft/C2`'s "design
  alone doesn't count". An agentic system that was built or shipped is `yes`, even in
  the passive voice; voice is C5's concern.
- `evaluation-rigour/C4`: a relative change states its own baseline, "before", so "22%
  fewer escalations", "halved recall", "4 points of F1" and "19% fewer failed reviews"
  are `yes`. A method rather than a result ("an LLM judge calibrated against 500 human
  labels") is `no`.
- `production-ownership/C4`: fixing a live system, monitoring it, and rework that the
  neighbouring bullets place after launch are `yes`, and so is operating it when that
  produced a named artefact ("It was kept running afterwards and the runbook came out of
  that"). An incident that was merely caught is `no` (it is C3's operational fact), and
  so are "A small serving benchmark I run each release" and "We kept the loops running
  after the grant ended" (staying, with no work named). This is consistent with the 25 and 26 September rulings: staying on or
  still-in-use with no work named stays `no`.

**The key.** `corpus/resumes/answer_key.json`, committed, holds 36 entries. Each entry
has the doc, the category slug, the criterion id, the owner's answer, the exact quote
and the date. Single-answer criteria are keyed per document. `production-ownership/C4`
(`any_bullet`) is keyed per place: its locators were resolved with `ats.sections.parse`,
and `tests/test_answer_key.py` fails if a parser change moves one. The entries are
`agentic-systems/C1` ×10, `evaluation-rigour/C4` ×5, `production-ownership/C4` ×11
places, and `resume-craft/C1` ×10 (all `no`, each checked against the new bar).

**Built.**

- `scripts/agreement_harness.py --key PATH`, which defaults to the committed key. After
  the agreement tables, every report (live, `--collect` or `--from`, with or without
  Claude) prints each provider sample's items matched out of every key entry (`N/36`),
  including a planned sample that answered nothing. It then lists every mismatch as
  doc / criterion / locator / key answer vs judge answer. A missing answer is a mismatch
  marked `missing`: a document the run skipped or never judged, or a criterion the
  sample left unanswered. A scoped item is compared at its keyed place, not on the
  derived answer. A voted sample keeps every try's per-place answers under
  `try_places`, and the keyed place is voted across them with `ensemble.vote`. A run
  saved before that has only the copied try's `places`, which is read instead.
- The headline under the contact details is now citable. On five resumes luna refused
  to cite lines such as "Agentic AI engineer." because "that line has no locator in
  PLACES". When there is no summary section, `ats.sections.parse` reads one header line
  as the summary: the second line with no contact details on it, since the first is the
  name. Emails, phones, URLs and places ("Boston, MA", "London, United Kingdom",
  "Remote") count as contact details. A header with a date range in it, or more than
  four lines, has no headline; that is a career block under a heading the parser does
  not know. So `prompts.places`, `passes.resolvable_locators` and the scoped
  `any_place` count all see it as `summary`.
- The probe's `identity` check (`scripts/criteria_probe.py`) now needs a level
  (`LEVEL_RE`) as well as a title.
- Wrapped bullets stay whole. The parser used to open a fake role when a bullet's next
  line started with a digit or a capital letter, because PDF text keeps no indent. This
  hit 06, 16, 18, 28 ("Grafana, 14 dashboards.") and 29 ("19% fewer failed reviews."),
  so both judges saw "…were monitored in" cut off. After a bullet, a line that starts
  lowercase continues it. A heading-shaped line opens a role: every word capitalised
  and no digit ("Open Source Contributions", "VOLUNTEERING"). If a date range follows
  it, it becomes the first half of that role's heading instead ("Corvus Labs" over "ML
  Engineer  Jan 2022 - Jun 2023"). Anything else continues the bullet. Projects are
  parsed on their own: an undated name opens a project, and project bullets with no
  name go under a "Projects" role, not under the last job (02, 09, 15, 16, 17, 22 and
  26). "VOLUNTEERING" is a known section. Bullet texts, bullet counts and years of
  experience did not change; the fake roles had no dates. The key's locators were
  regenerated through the parser. Only 09's benchmark bullet moved, from
  `exp[2].bullet[3]` to `exp[3].bullet[0]`, and 28's quote is now the whole bullet.
  Runs from before this fix, including 27 September, saw the split bullets.
  (ponytail: the heading test is a word-shape heuristic. A wrapped line made only of
  capitalised names, such as "Kubernetes Engine", reads as a heading. Under PROJECTS, a
  wrapped line that starts with a capital and is followed by a bullet reads as a
  project name.)

**Known gaps.**

- The probe cannot see part (c) of the C1 bar, what the candidate builds. It says `yes`
  to "AI engineer, eight years.". `scan/no-identity-above-fold` still checks
  the title only.
- The probe's `evaluation-rigour/C4` aliases (`from N`, `N to M`) don't match a relative
  change such as "22% fewer". They were not changed here.
- A voted luna sample whose tries all abstain on the derived answer drops the item,
  and the keyed place with it, so it scores `missing` even if some tries answered that
  place.

**Next finish line.** Luna against the key, not against Claude. Finish line, set by the
owner before the run: gpt-6-luna (medium effort, 3-try vote) matches the answer key on
at least 32 of 36 entries, on each of its two voted samples, over the 24 keyed
documents. A missing answer counts as a miss. Claude is not part of this test.
