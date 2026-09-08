# Resume corpus — the acceptance set

The documents the rubric is measured on. Ticket 08 exists because until now there were
almost none: seven PDF fixtures (four carrying identical bullets, three carrying almost
nothing), twenty-nine band probes written by the sessions that then judged them, and one
real resume that cannot be committed. A rubric tuned until it agrees with its author on
examples its author wrote has one reader.

The specification, the reasoning and the measurements are in
[docs/wayfinder/rubric-migration/acceptance-set.md](../../docs/wayfinder/rubric-migration/acceptance-set.md).
This file is the operating manual.

## What is here

| path | what it is | committed |
|---|---|---|
| `briefs.json` | the drawn briefs each document was written from | yes |
| `synthetic/` | 30 documents, tier 1 | yes |
| `manifest.json` | a hash per document, so a change after a measurement is visible | yes |
| `rendered/` | the PDFs, generated from `synthetic/` | **no** — gitignored |
| `real/` | tier 2: real resumes, consented or the owner's | **no** — gitignored |

## Provenance

**Tier 1, `synthetic/`, is invented.** No real person, employer, address, phone number
or email; nothing lifted from a real resume. Names, companies and contact details are
fabrications, and the phone numbers use the 555-01xx range reserved for fiction.

What is *not* invented is the material each document is written from. A brief is drawn
by `scripts/draw_briefs.py` from the job-posting corpus in `corpus/jds/` — the same
postings that derive the taxonomy and four of the eight category weights. The sampler
draws what the candidate has done, who they are and how their resume is written, and
draws it **before anybody writes a word**. Nothing in the sampler names a category, a
criterion or a band.

**Tier 2, `real/`, is personal data and is never committed.** Real resumes belong to
people who did not volunteer them for this. Anything here is either the owner's own or
submitted with consent recorded alongside it, and only redacted derivatives — criterion
answers, bands, locators, hashes — leave the directory. The precedent is
`docs/wayfinder/rubric-grounding/baseline/run-summary.json`: the arithmetic is
checkable, the resume text is not there.

## The rules

1. **Bands are observed, never targeted.** No document is written to land anywhere. If
   the set does not reach a band, the fix is more seeds and more documents, never an
   edit to a document that already exists.
2. **A document does not change after a judge has read it.** `manifest.json` records a
   hash of each one. A change is a new document: re-freeze and say so in
   acceptance-set.md, and any measurement taken on the old text is measurement of
   something that no longer exists.
3. **Real resumes never reach git.** Not the text, not a quote from the text, not a
   locator that reproduces it. `.gitignore` covers `real/` and `rendered/`; that is a
   backstop, not the control.

## Running it

    .venv/bin/python scripts/draw_briefs.py             # rewrite the briefs (see rule 1)
    .venv/bin/python scripts/make_acceptance_set.py     # render the PDFs
    .venv/bin/python scripts/make_acceptance_set.py --verify   # check the freeze
    .venv/bin/python scripts/acceptance_coverage.py     # what the set reaches

## Adding real resumes

Drop them in `real/` as PDFs with a sibling `<name>.consent.json`:

    {
      "source": "consented submission" | "owner",
      "consented": "YYYY-MM-DD",
      "scope": "scoring and agreement measurement; no text committed or republished",
      "withdrawal": "how the person asks for it to be deleted"
    }

Then run the harness with `--resume`. Tier 2 upgrades what 09 can claim; it does not
replace tier 1, because tier 1 is what a future session can re-run without holding
anybody's personal data.
