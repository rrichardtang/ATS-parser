type: task (AFK)
status: closed
claimed: claude
blocked-by: —

# Repair JD requirement-section extraction

## Question

Three of the six postings (anthropic, openai, ramp) classify **zero words** as
`required`; `jd_sections._header_bucket` only matches conventional headers, so
"You May Be a Good Fit If You Have" lands in `responsibilities`. `required_df` is
counted over the `required` span alone, so no term can exceed 2/6 — which is why the
digest tells the model "Required in most: python (1/6)".

Nothing about grounding a rubric in this corpus can be decided while two-thirds of it
extracts nothing. Make every posting yield a requirements span, and report what the
corpus actually contains once it does.

Done when: all six postings classify a non-empty `required` span, the header patterns
cover the variants present in this corpus, and the change is covered by a test using
the real posting headers.

## Answer

All six postings now yield a non-empty `required` span. The vocabulary was one of
**two** independent causes; the missing headers were the visible one.

### Cause 1: the vocabulary never saw half the headers it already knew

Careers sites emit a typographic apostrophe (U+2019), not ASCII `'`. The corpus holds
the same header spelled both ways — `What We're Looking For` (edra, fluidstack) and
`What We’re Looking For` (amex) — and `_HEADERS` is written with ASCII, so the
typographic half never matched. `What You’ll Do` (amex, openai, ramp) was missed the
same way. Matching now runs on a punctuation-normalized copy of the line; bucket
contents stay verbatim.

This one is worth naming separately because it was invisible in the symptom: amex and
edra looked like they worked. Amex only extracted requirements because the *preceding*
header (`Qualifications`) happened to be in the vocabulary, so its unmatched
`What We’re Looking For` inherited the right bucket by luck.

### Cause 2: three header families genuinely absent

- **The conditional fit-statement**, how both frontier-lab postings introduce their
  requirements list instead of a noun heading: `You May Be a Good Fit If You Have`
  (anthropic), `You Might Be a Good Fit If You` (openai). Its tail runs free, so it is
  a regex family rather than a phrase; `_MAX_HEADER_LEN` is what stops body prose from
  reading as a heading.
- **`What You Need`** (ramp) → required. **`Role Scope`** (fluidstack) → responsibilities.
- **`Technical Environment`** (amex) → **nice-to-have**, a judgement call worth
  contesting. It is a stack listing (Python, Go, TypeScript, Kubernetes, Kafka, gRPC)
  the posting itself prefaces with "we don't hire to a narrow checklist". Required
  would take that disclaimer at less than its word; responsibilities counts toward no
  skill at all. Nice-to-have (0.4 weight) is the honest reading of a posting that
  names its stack and declines to require it.

### Also added: a rescue pass, because the vocabulary will miss the next one too

A posting whose requirements header is not in the vocabulary drops that entire list
into `responsibilities` and **reports nothing** — four spans still come back, one
silently empty. That is precisely how this defect survived to be a ticket. So when
headers were found but none of them was a requirements header, requirement-shaped
lines are now moved out of `responsibilities` into `required`. It changes nothing for
these six postings; it is the guard for the seventh.

## What the corpus actually contains

Six postings. `required` doc-frequency, over repaired spans:

| term | before | after |
|---|---|---|
| python | 1/6 | **3/6** |
| typescript | 1/6 | **3/6** |
| prompt-engineering | 1/6 | **3/6** |
| eval-harness | 1/6 | **3/6** |
| agents | 1/6 | **2/6** |
| fine-tuning | 1/6 | **2/6** |
| cloud | 1/6 | 1/6 |

Emphasized qualities are unchanged (they already read responsibilities text):
production 6/6, evaluation 3/6, ownership 1/6, seniority 0/6, leadership 0/6.

Per posting, terms now found in the requirements span:

- **amex** — python, cloud, typescript
- **anthropic** — python, typescript, prompt-engineering, agents, eval-harness
- **edra** — prompt-engineering, agents
- **fluidstack** — fine-tuning, eval-harness
- **openai** — python, fine-tuning, prompt-engineering, eval-harness
- **ramp** — typescript

## Three findings this hands to ticket 02

1. **The ceiling is 3/6, not the majority the prompt claims.** `prompts.digest_text`
   labels the list "Required in most"; the most any term reaches across six postings
   is exactly half. Extraction is no longer what is suppressing the number — these
   postings genuinely do not converge on named tools. A category set built on "what
   most postings require" has less to stand on than the label implies.
2. **The taxonomy's aliases are now the binding constraint, not the spans.**
   Fluidstack asks for "retrieval systems" and edra for "context engineering"; `rag`
   matches only `rag`/`retrieval-augmented`, so it reads 0/6 required over a corpus
   that plainly discusses retrieval. Term counts still understate the corpus, one
   layer further down.
3. **Nice-to-haves also appear as bullets, not only as sections.** Fluidstack and ramp
   each end their requirements list with an inline `Bonus:` bullet, which header
   detection cannot reach and which therefore counts at full required weight.
   Bullet-level classification is out of scope here; naming it so it is not
   rediscovered as a surprise.

## Changed

- `ats/jd_sections.py` — punctuation normalization, the header families above, the
  rescue pass.
- `tests/test_jd_sections.py` — every header parametrized verbatim from a real
  posting, both apostrophe spellings asserted equivalent, rescue asserted to fire only
  when no requirements header matched.
- `ats/jd_digest.json`, `ats/taxonomy.json` — regenerated by
  `scripts/build_user_corpus.py` (deterministic, no API key).

Full suite: 144 passed.
