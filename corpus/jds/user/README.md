# Personal JD corpus

Real postings for roles you're actually targeting, added one at a time with
`python scripts/add_jd.py`. This is what grounds your own runs -- unlike
`corpus/jds/*.txt` (the generic, synthesized composite corpus the tool ships with),
every file here is a verbatim posting you chose.

## Schema

One JSON file per posting, named by slug:

```json
{
  "title": "AI Engineer",
  "company": "Example Corp",
  "source_url": "https://example.com/careers/123",
  "date_added": "2026-08-29",
  "raw_text": "<the full pasted posting, verbatim>"
}
```

`raw_text` is never edited or split at rest -- it's the ground truth. Section
classification (requirements vs. nice-to-have vs. responsibilities) and dimension
detection (ownership, production evidence, evaluation rigor, seniority,
leadership) are computed fresh from it every time `scripts/build_user_corpus.py`
runs, never stored here. If that logic improves later, re-running the script
picks it up for every posting already in this directory -- nothing needs to be
re-pasted.

## Workflow

```
python scripts/add_jd.py           # paste one posting, prompted for metadata
python scripts/build_user_corpus.py  # regenerate ats/taxonomy.json + ats/jd_digest.json
```

Run the build script again after every posting you add, or after adding several
at once -- it's idempotent and free (no API key, no LLM call, just regex over
text you already pasted).

With zero files here, `build_user_corpus.py` is a no-op: it leaves
`ats/taxonomy.json` exactly as the generic corpus produced it, and `ats/jd_digest.json`
is simply absent, so nothing downstream (scoring, target-title, prompts) behaves
any differently than before this corpus existed.

## A note on what you're committing

Unlike `corpus/jds/*.txt` (a generic corpus shipped with this tool to anyone who
clones it), this directory holds full verbatim postings for roles *you* chose --
treat it as personal data, not distributable content. That's fine for a private
fork or local use; think twice before pushing it to a public repository.
