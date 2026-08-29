# resume.diagnostics

A local resume checker for mid-level AI Engineer roles. Upload a PDF, get a list
of specific defects — each with the line it is on, the fix, and what it cost the
score.

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --reload
# http://127.0.0.1:8000
```

Works with no API key at all. Keys unlock judgement, not the tool.

## What this is not

It does not tell you how to beat a bot, because that is not what happens. Most
ATSs do not auto-reject on resume content — in a poll of 630 recruiters, 83% said
theirs does not. Greenhouse and Lever are built around human scorecards.

It also does not give you a portable "ATS score". The same resume scores
differently in Workday, Lever and Greenhouse, and no public checker is calibrated
against interview outcomes — there is no ground truth, so every vendor invents a
rubric and normalises it to 0–100. That is why three free checkers give you three
wildly different numbers.

So the composite here is a **diagnostic index over named defects**, never a
prediction. Every point traces to a finding with its evidence and its cost, the
ledger sums to the total, and you can disagree with any weight and see exactly
what changes. If you only ever read the findings and ignored the number, the tool
would still work.

## Two gates

A resume clears two, and they fail for unrelated reasons:

| Gate | Question | Typical failure |
|---|---|---|
| **Parser** | Can an ATS extract your fields? | Two columns, tables, hidden text, content in the header band |
| **Recruiter** | Does a human learn what you are in seconds? | Best evidence below the fold; Interests above Experience |
| **Hiring manager** | Did the work actually happen? | No eval methodology, no scale, no named model |

Findings and subscores are labelled by gate, because a resume can pass one and
fail the other and the fixes are unrelated.

## How it works

```
PDF → extract → sections → deterministic checks → LLM passes → score → report
```

Everything mechanically checkable runs in Python, free and reproducible. The LLM
only judges what rules cannot.

### Deterministic (no key needed)

- **Parseability**, from PDF geometry rather than text: hidden/invisible text,
  empty text layer, column gutters, tables, header-band content, page count.
- **Structure**: sections, dates, reverse-chronological order, gaps, bullet counts.
- **Bullet invariants**: every bullet checked for Outcome, Measurability,
  Mechanism, Ownership — independently, so strong bullets pass in any construction.
- **Slop patterns** ported from [`no-ai-slop`](https://github.com/petergyang/no-ai-slop),
  scoped to resume form, including the portability test.
- **Recruiter scan** using page-1 word boxes: what is actually above the fold.
- **Keywords**: coverage, stuffing penalties, unsupported claims, JD gap diff.

### Three LLM passes

| # | Pass | Job |
|---|---|---|
| 1 | Content | Substance, ownership, seniority fit, missing information |
| 2 | Slop | Named patterns beyond regex reach — never an AI-likelihood score |
| 3 | Rewrite | Fixes content and slop in one edit, after seeing both |

1 and 2 run concurrently; 3 depends on both, so a rewrite cannot reintroduce the
phrasing pass 2 flags.

## Two API keys

Supply both an Anthropic and an OpenAI key and the tool ensembles across them.
This is worth more than sampling one model repeatedly, because **a model is
weakest at flagging its own idiom** — if your resume was drafted with one, the
other is the informative detector.

That inverts the combination rule, which is the subtle part:

- **One model, N samples** — a lone finding is probably sampling noise → keep
  findings seen in *k of N*.
- **Two providers** — a lone finding is plausibly a blindspot catch → keep the
  *union*, labelled `1 of 2 models`.

Getting that backwards would either flood you with false positives or discard
exactly the catches that make two keys worth having.

Either key alone works. Neither still runs every deterministic check.

## Rewrites invent nothing

Rewrites are proposals in a diff. Nothing is applied automatically.

Where a bullet needs a number you never supplied, you get `[add: eval metric]`,
not a plausible figure. A fabricated stat is not a style error — it is something
you have to defend in an interview.

This is enforced, not just prompted. Pass 3 generates candidates from both
providers (best-of-N), then adds one more: a **mixture-of-agents synthesis** step
that gives every candidate to a single model and asks it to combine their distinct
strengths into one bullet, rather than only ever picking a single winner and
discarding the rest. The synthesizing provider is whichever one contributed
*fewest* of the candidates — the same cross-provider-adjudication logic used
elsewhere, so a model never grades mostly its own drafts.

Synthesis is not a side channel around the verifier — the synthesized bullet is
just one more candidate, gated by the exact same rules as any other. Best-of-N
against a verifier is a textbook Goodhart setup, so the verifier is **split**:

- **Ranking set** — selects the winner (invariants, slop patterns, length).
- **Audit set** — never used for selection, only to detect gaming: invented
  figures, vacuous numbers (`collaborated with 3 engineers`), truncation, and
  proper-noun padding.

A candidate cannot optimise against signals it is not selected on, so a rising
ranking score with a falling audit score is the hacking signature — logged per run
and asserted in tests. A rewrite must also beat the **original** by a margin, not
merely beat its siblings; if nothing does, you keep your bullet. The rule holds
whether the winning candidate came from best-of-N or from synthesis.

Run `python scripts/hacking_sweep.py` to see the ceiling check: raising N must not
degrade the audit. Synthesis costs one extra call per rewritten bullet, so it's on
by default and in Thorough mode, and off in Economy — turn it off in
`ats/weights.toml` (`[ensemble].synthesize`) if you want best-of-N alone.

## Where the rubric comes from

There is **no published "gold standard" resume** from Anthropic, OpenAI, or any
FAANG. What circulates under that name is vendor SEO content, much of it itself
LLM-generated — calibrating on it would tune the slop detector toward the exact
phrasing it exists to catch.

So weights are derived from the **demand side**: `corpus/jds/` holds AI Engineer
postings, and `scripts/build_taxonomy.py` measures term frequency across them to
generate `ats/taxonomy.json`. A weight the corpus does not support is visibly
wrong and correctable.

> **Corpus caveat, read this.** The shipped corpus files are *synthesized
> composites*, not verbatim postings — the environment that built this could not
> reach careers sites. They are grounded in published 2026 hiring analyses, but
> they are a defensible starting point, not a substitute for real data. Drop real
> postings into `corpus/jds/` and re-run the script. See `corpus/README.md`.

### Rule provenance

Every rule declares where its authority comes from:

| Provenance | Meaning |
|---|---|
| `parser-mechanics` | Mechanically verifiable — the text genuinely fails to extract |
| `jd-derived` | Measured in the JD corpus |
| `recruiter-evidence` | Cited external evidence about recruiter behaviour |
| `heuristic` | Author judgment |

**Heuristic rules are capped at minor severity and can never sink a score**, and
are tagged in the UI. Weights live in `ats/weights.toml` — edit them.

### Why not the XYZ formula

"Accomplished X as measured by Y by doing Z" traces to one exec's 2014 advice, not
a Google rubric. Enforcing it as a template would contradict this tool's own
robotic-rhythm detector — one formula across every bullet is an LLM tell — and it
checks shape rather than substance. A bullet can satisfy XYZ perfectly and still
name no model, dataset or eval. The four invariants above are what XYZ is a
delivery vehicle for, checked independently.

## No hard gates

One public checker returns 22/100 for a missing phone number. That measures one
field and reports it as a verdict on the whole document.

Here, no single non-fraud finding may cost more than its category's weight, and it
is asserted in the test suite: two fixtures differing only in a phone number must
score within a few points. The one deliberate exception is hidden-text injection,
which caps the composite — that is a fraud-flag risk to your candidate record, not
a style preference, and the cap is disclosed in the report.

## Exports

Markdown or PDF. The PDF is generated locally with ReportLab — no headless
browser, no hosted service — so it contains only your report. No watermark, no
branding, producer metadata blanked.

## Development

```bash
.venv/bin/python -m pytest              # 92 tests, no network
.venv/bin/python tests/make_fixtures.py # regenerate fixture PDFs
.venv/bin/python scripts/build_taxonomy.py
.venv/bin/python scripts/hacking_sweep.py
```

Fixture PDFs are generated from `tests/make_fixtures.py` rather than checked in,
so the inputs stay readable in review.

## Privacy

Your resume is written to a temp file, analysed, and deleted in a `finally` block.
API keys live in the request only — never written to disk, never logged. Reports
are cached in memory for an hour so re-rendering does not re-bill you.

## Credits

Slop patterns adapted from [`no-ai-slop`](https://github.com/petergyang/no-ai-slop)
by Peter Yang (MIT) — see `vendor/no-ai-slop/`. UI built following Anthropic's
[`frontend-design`](https://github.com/anthropics/skills/tree/main/skills/frontend-design)
skill.
