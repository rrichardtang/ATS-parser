type: task (AFK)
status: open
claimed:
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
