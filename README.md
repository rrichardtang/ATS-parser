# resume.diagnostics

**A resume checker for AI Engineer roles that explains every point it takes off.**
Upload a PDF and get a list of named defects. Each one comes with the line it is on, the
quote that proves it, a fix, and exactly what it cost the score.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)

![A report: the score ledger on the left, the top five fixes on the right](docs/images/report.png)

<sub>A sample report with no API key: deterministic checks only. Every row of the ledger on
the left is a real movement of the score, and they sum to the total.</sub>

**Contents:** [Quickstart](#quickstart) · [Why it exists](#why-it-exists) · [Engineering highlights](#engineering-highlights) · [How it works](#how-it-works) · [Evaluation](#evaluation) · [Models and cost](#models-and-cost) · [Project layout](#project-layout) · [Development](#development) · [Limitations](#limitations) · [Privacy](#privacy)

## Quickstart

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --reload
# INFO:     Uvicorn running on http://127.0.0.1:8000
```

Open http://127.0.0.1:8000 and upload a PDF.

It works with no API key. An OpenAI key adds the LLM judgement passes; Claude is opt-in
(see [Models and cost](#models-and-cost)).

## Why it exists

Free "ATS score" checkers give the same resume wildly different numbers, because there is
no ground truth: no checker is calibrated against interview outcomes, so each one invents a
rubric and scales it to 0 to 100. This project does not pretend otherwise. Its score is a
**diagnostic index over named defects**, never a prediction. If you ignored the number and
read only the findings, the tool would still work.

## Engineering highlights

What the project demonstrates, in the order a reviewer would want to check it:

| | |
|---|---|
| **LLM evaluation against a labelled answer key** | The content judge is accepted only if it matches a hand-labelled answer key on at least 32 of 36 entries, on each of two independent voted samples. The current configuration passed at **35/36 and 32/36**. ([results](#evaluation)) |
| **Rubric built for reproducibility** | Judges answer binary evidence questions, each with the quote that settles it. Scores are computed from those answers by a lookup, never chosen by the model, so two judges can be compared question by question. |
| **Reward-hacking defence for generation** | Rewrites are best-of-N with a **split verifier**: one signal set ranks candidates, a separate audit set (invented figures, vacuous numbers, padding) is never optimised against and only detects gaming. A rising rank score with a falling audit score is logged and asserted in tests. |
| **No fabrication by construction** | Every rewrite candidate is fact-checked before any judge sees it. A missing metric becomes `[add: eval metric]`, never a plausible number. |
| **Deterministic first, LLM only where rules can't reach** | PDF geometry checks (hidden text, columns, tables, header bands), structure and slop patterns all run in plain Python, free and reproducible. Two of three LLM passes only judge. |
| **Cost-aware ensembling** | One model is voted three ways; a second provider is switched on deliberately, and the combination rule flips with it (k-of-N for samples of one model, union for two providers, since a model is weakest at spotting its own idiom). The three content votes cost about **$0.03** per resume. |
| **Weights grounded in data** | Behaviour categories are weighted by how many target job postings state that behaviour, so adding a posting moves the weights with nobody editing a number. |

## How it works

```mermaid
flowchart LR
    PDF["PDF resume<br/>(+ optional job posting)"] --> EX["Extract<br/>text, layout, hidden text"]
    EX --> SEC["Parse sections<br/>roles, bullets, dates"]
    SEC --> DET["Deterministic checks<br/>parseability, structure,<br/>slop patterns, keywords"]
    DET --> P1["Pass 1: content judge<br/>criteria + quotes, voted"]
    DET --> P2["Pass 2: slop judge<br/>named patterns"]
    P1 --> SCORE["Score + ledger"]
    P2 --> SCORE
    DET --> SCORE
    SCORE --> REP["Report<br/>web · Markdown · PDF"]
    P1 -.-> P3["Pass 3: rewrites<br/>only on request"]
    P2 -.-> P3
    P3 -.-> REP
```

A resume has to clear two gates that fail for unrelated reasons, and findings are labelled
by which one they belong to:

- **Parser gate.** Can an applicant tracking system extract your fields? Fails on two
  columns, tables, hidden text, content in the header band.
- **Human gate.** Does a recruiter learn what you are in seconds, and does a hiring manager
  believe the work happened? Fails on buried evidence, no eval method, no scale, no named
  model.

Pass 3 never runs on upload. It is a separate button, so you always know when extra calls
are being spent. It generates candidates under three framings, drops any that fail the
fact-check, ranks the survivors, lightly polishes the winner, and ships it only if it beats
your original bullet by a margin. Otherwise your bullet stands.

The full reasoning for every stage is in [docs/design.md](docs/design.md).

## Evaluation

The content judge is tested by `scripts/agreement_harness.py` on 24 keyed documents from a
30-resume synthetic acceptance set (`corpus/resumes/`), against the owner's hand-labelled
answer key (`corpus/resumes/answer_key.json`).

| Run (30 Sep 2026) | Bar | Sample 0 | Sample 1 | Result |
|---|---|---|---|---|
| gpt-6-luna, high effort, 3-try vote | ≥ 32/36 on each sample | **35/36** | **32/36** | Pass |

How the bar was reached, including the runs that failed (30/36 on both samples at medium
effort, then 31 and 32 at high), is recorded in
[rubric-grounding ticket 15](docs/wayfinder/rubric-grounding/tickets/15-judges-that-repeat-themselves.md).

**What this does and does not show.** The second sample sits exactly on the bar, and the
two samples differ by three, so voting is still noisy. The ruling examples in the prompt
were written from the keyed lines, so this measures instruction-following, not
generalisation to unseen resumes. That check on unseen, real resumes is the next step.

The harness also reports Krippendorff's alpha and how far each judge lands from itself on a
rerun, because two judges agreeing on the score nearly every resume gets is coincidence,
not a rubric. `--dry-run` prints the call budget without spending it.

## Models and cost

| Setting | Model | Typical cost per resume |
|---|---|---|
| Default | OpenAI `gpt-6-luna`, content judge voted 3 ways | about $0.03 for the content votes |
| `use_claude = true` in `ats/weights.toml` | adds Claude `claude-sonnet-5` on every pass | about $0.11 more (measured 27 Sep) |
| No key | deterministic checks only | free |

A Claude key alone does not switch Claude on; the setting in `ats/weights.toml` does.

## Project layout

| Path | What it holds |
|---|---|
| `app.py`, `templates/`, `static/` | FastAPI web app and report UI |
| `ats/` | The pipeline: extraction, section parsing, rules, LLM passes, scoring, report |
| `ats/criteria/`, `ats/weights.toml` | The rubric's evidence questions and the authored weights |
| `corpus/jds/` | Job postings that weights and keyword coverage are derived from |
| `corpus/resumes/` | Synthetic acceptance set and the hand-labelled answer key |
| `scripts/` | Evaluation harness, reward-hacking sweep, corpus builders |
| `tests/` | 518 tests; fixture PDFs are generated, not checked in |
| `docs/` | Design notes and the decision log for the rubric work |

## Development

```bash
.venv/bin/python -m pytest                              # 518 tests, no network
.venv/bin/python tests/make_fixtures.py                 # regenerate fixture PDFs
.venv/bin/python scripts/hacking_sweep.py               # raising N must not degrade the audit
.venv/bin/python scripts/agreement_harness.py --dry-run # judge agreement, call budget only
```

To ground the weights in the roles you are targeting, paste real postings in and rebuild.
This step is free and makes no LLM calls:

```bash
python scripts/add_jd.py             # paste one posting
python scripts/build_user_corpus.py  # regenerate ats/taxonomy.json and ats/jd_digest.json
```

## Limitations

- **The shipped job-posting corpus is synthesized**, not verbatim postings: the
  environment that built it could not reach careers sites. Add real postings with the
  commands above. See `corpus/README.md`.
- **The acceptance set is synthetic.** Real resumes are gitignored and never committed, so
  the published evaluation is on invented documents.
- **No score here predicts interviews.** Nothing public does; see [Why it exists](#why-it-exists).

## Privacy

Your resume is written to a temp file, analysed, and deleted in a `finally` block. API keys
live in the request only; they are never written to disk or logged. Reports are cached in
memory for an hour so re-rendering does not re-bill you. PDF exports are generated locally
with ReportLab, with no watermark and blank producer metadata.

## Credits

Slop patterns adapted from [`no-ai-slop`](https://github.com/petergyang/no-ai-slop) by
Peter Yang (MIT), see `vendor/no-ai-slop/`. UI built following Anthropic's
[`frontend-design`](https://github.com/anthropics/skills/tree/main/skills/frontend-design)
skill.
