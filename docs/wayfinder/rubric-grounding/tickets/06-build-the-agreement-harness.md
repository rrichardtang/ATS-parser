type: task (AFK)
status: closed
claimed: claude
blocked-by: 03

# Build the inter-judge agreement harness

## Question

The acceptance test — two providers within 5 points per category, >8 fails — cannot
be applied without something that measures it. Build the harness: run each resume
through both providers twice, report per-category spread between providers and
between samples of the same provider, so sampling noise is visible separately from
genuine disagreement.

Inputs: the seven fixtures in `tests/fixtures/` plus the user's real resume.
Blocked by 03 because what it measures depends on whether the model emits scores.

Done when: the harness runs from the command line, prints a per-category table, and
its output is the evidence any rubric change is judged on.

## Done

```bash
.venv/bin/python scripts/agreement_harness.py --dry-run          # the plan and its cost
.venv/bin/python scripts/agreement_harness.py --resume ~/cv.pdf  # the acceptance test
.venv/bin/python scripts/agreement_harness.py --from runs/....json   # re-render, no calls
```

Three modules, split by what each is: `ats/reliability.py` (Krippendorff's alpha,
domain-free), `ats/agreement.py` (collect the judgements, compute the comparison),
`ats/agreement_table.py` (print it). The script is argparse and nothing else.

It prints four tables. Per category: between-judge spread, within-judge spread,
alpha, and how many resumes cleared the 5-point bar. Then composite spread per
resume against the 5 / >8 bar, the composites themselves by judge, and findings
agreement keyed on (defect kind, locator).

## What the harness had to be built around

**The pipeline destroys its own evidence.** `content_pass` averages a provider's
samples, then `combine_scores` averages across providers, then the report shows the
mean. By the time a number exists, every disagreement that produced it is gone. So
the harness could not be a wrapper over `analyze()`; it needed the judgements
unfolded. `passes.content_judgments()` is that seam — the per-(provider, sample)
replies, parsed but not combined — and `content_pass` is now a fold over it, so the
harness measures the same parse the report does rather than a second copy of it.

**The measurement runs through the real scoring code.** Each judgement goes through
`score.build` to get its composite and its blended category scores, rather than a
reimplementation of the blend. That matters because the 5-point bar was always
stated against the *blended* category score, and `rule_share` scales the model's
disagreement by `(1 - rule_share)` — 0.6 everywhere, 0.3 in Recruiter scan. A
harness that compared raw model numbers would be applying the bar to the wrong
quantity, at a factor that varies 2× by category (`scoring-mechanics.md`).

**Bands do not exist yet, and the harness cannot wait for them.** 03 settled that
the model names a band; `prompts.CONTENT_SYSTEM` still asks for 0–100. So the
channel is read from the reply rather than assumed: a number, a band label, or
both. Both is not hypothetical — it is exactly 05's second experiment (band versus
band-plus-a-point-inside-it), which this measures in one run. Numbers get spreads
and interval alpha; bands get exact/adjacent/far and ordinal alpha against the
order passed as `--bands`.

## Three numbers, not one — and what each refuses to say

08 asked for between-judge spread, within-judge spread, and a chance-corrected
statistic. The third one is the one that does work the other two cannot, and
getting it right meant making it decline to answer in three places:

- **Alpha is `n/a`, never 1.00, when there is no variance.** If every judge lands on
  the same value for every resume there is nothing for the rubric to have explained,
  and reporting perfect agreement would be precisely the false pass 08 warned about
  (`±5 is passable by luck when every real resume lands between 60 and 80`).
- **An unmeasured spread prints `-`, never 0.0.** Three separate places produce a
  zero that reads as perfect agreement: one provider configured, a category only one
  judge answered on, and a single sample per provider. The last two are per-row, not
  per-run — with both providers present, a run-level guard passes and the row prints
  `0.0` beside its own alpha of `n/a`.
- **A resume only one judge scored gets no composite verdict.** A provider erroring on
  one resume drops it to a single judge, whose spread against itself is 0.0. That row
  prints `-` and stays out of the pass/look/FAIL tally, and the failed calls are
  reported as notes beside the tables rather than left in the scrollback.
- **A composite pinned by a cap is marked, not counted.** `hidden_text` sits at the
  fraud cap and `scanned` at the unreadable cap, so both judges report the same
  number whatever they thought. Two of the seven fixtures pass the composite bar for
  a reason that has nothing to do with agreement, and the table says so.
- **A band a lone judge named is not exact agreement.** One judge's band matches
  itself by construction; and a judge that names two bands for the same resume on a
  rerun costs the category its verdict, having failed the same test from the other
  direction.

Findings agreement is keyed on `(rule_id, locator)` per 03 — same defect, same
place, however differently worded — and reported as Jaccard overlap between judges
and within each judge across its reruns.

## Two facts, one already known and one a correction

**1. The noise floor is not adjustable — and this was already written down.**
`weights.toml`'s comment on `temperature` already says it: the parameter only
reaches models of the gpt-4 era and earlier, since `ats/llm.py` never sends it to
Anthropic and gates it behind `LEGACY_OPENAI`. Not a discovery by this ticket, and
recorded here because the *consequence for measurement* is new. `content_pass`
passes `temperature` whenever `samples > 1`, so the within-judge column measures
each provider's **own default** sampling. That is still a real noise floor — it is
the noise a user's run actually carries — but it cannot be turned down to make
between-judge spread look better by comparison. The honest move, and what the
harness does, is to report the floor, say in its own output that the temperature
was not chosen, and require between-judge spread to clear it.

**2. `content_samples` stays at 1 in `weights.toml`.** `scoring-mechanics.md` reads
the acceptance test as needing the config flipped to 2. It does not, and flipping it
would be wrong: sampling twice is a *measurement* requirement, and putting it in the
shipped config doubles the cost of every user's run to buy them nothing — the report
averages the samples away again. The harness takes `--samples` (default 2) itself
and leaves production alone. `scoring-mechanics.md` §2 is corrected in place, since
04 and 05 read it: its claim that "the config is the small part" was true about the
requirement and wrong about where the requirement lands.

## Cost, and why the run is saved

2 providers × 2 samples × 8 resumes is 32 calls at the ceiling, 28 in practice —
`scanned` has no text layer, so it never reaches a judge. That is why `--dry-run`
prints the plan and its upper bound before anything is spent, and why `--only`
narrows the corpus.

Every run is written whole — raw replies, not the computed tables — so the next
rubric change is judged on a diff rather than a remembered number, and so a change
to *how* agreement is measured can be re-run against calls already paid for
(`--from`). `runs/` is gitignored: the saved judgements quote resume text, while the
printed table quotes nothing, which is what makes the table the part that belongs in
a ticket.

## What this hands downstream

- **04, 05** — the bar is now a thing that can be run rather than argued. A category
  set or a band draft is judged by a sweep before and after. Note what the harness
  can already say without any rubric change: if between-judge spread does not clear
  the within-judge column, the disagreement being designed against is sampling noise
  and no category redesign will move it.
- **05 specifically** — its second experiment needs no new tooling. Emit `band` and
  `score` in the same reply and one sweep reports both channels side by side.
- **Everyone** — alpha reading `n/a` on a category is a result, not a bug: it means
  every judge put every resume in the same place, which is a rubric that does not
  discriminate.

## Not done here, deliberately

The harness reads whatever the content prompt emits; it does not change the prompt,
the categories, or the bands. Those are 04's and 05's, and a measuring instrument
that also moves what it measures is not one.

## Changed

- `ats/reliability.py` — new. Krippendorff's alpha, nominal/ordinal/interval, with
  missing judgements tolerated and the degenerate cases returning no value rather
  than a flattering one.
- `ats/agreement.py` — new. Collecting unfolded judgements, and the four comparisons.
- `ats/agreement_table.py` — new. The printed tables.
- `scripts/agreement_harness.py` — new. The CLI.
- `ats/passes.py` — `content_judgments()` extracted; `content_pass` is now a fold
  over it, unchanged in behaviour.
- `ats/pipeline.py` — `_resolve_target_title` made public; the harness has to resolve
  the target title exactly as `analyze()` does or it measures a different prompt.
- `tests/test_reliability.py`, `tests/test_agreement.py` — new, 24 tests, no network.
- `README.md`, `.gitignore` (`runs/`).
