type: grilling (HITL)
status: closed
claimed: claude
blocked-by: —

# Where the real resumes come from

## Question

The rubric has been validated almost entirely on documents written by the sessions
validating it.

- **Seven PDF fixtures** in `tests/fixtures/`, four of which carry the same bullets, and
  three of which carry almost nothing. Every one that can be answered at all lands at
  one end of the ladder — 05 found three of five bands unreachable.
- **Twenty-nine band probes**, written by 05, 11 and 12 to land on specific bands, and
  answered by the same sessions that wrote them.
- **One real resume**, the owner's, gitignored because the raw run quotes it verbatim.

That is the entire evidence base. A rubric tuned until it agrees with its author on
examples its author wrote is a rubric with one reader, and no measurement on this map or
the last one can detect that. It is the largest untested assumption in the project and
neither map had a ticket for it until now.

## What has to be decided

1. **What a usable test set looks like.** How many, at what spread of quality, and
   covering which of the four behaviours — a set where every resume is a strong AI
   engineer tests nothing, and neither does one where every resume is bad.
2. **Where they come from.** Real resumes are personal data belonging to people who did
   not volunteer them for this. Public sources, synthetic-but-not-self-written,
   consented submissions, and anonymisation are all options with different costs, and
   the cheapest option is the one that quietly reintroduces the problem: resumes written
   by a model to test a rubric scored by a model.
3. **What is committed and what is not.** The raw baseline is already gitignored for
   quoting resume text; `baseline/run-summary.json` is the redacted form that keeps the
   arithmetic checkable. Whatever this decides has to survive the same treatment.

Unblocked from the start, and deliberately: it needs no code, it gates the only
measurement that matters, and it is the one thing on this map that cannot be finished
by writing software.

Done when: the test set is specified, its provenance and privacy handling are decided,
and enough of it exists to run 09 on.

## Answered

**Three tiers, and only the first is committed.** 30 invented documents written from
briefs drawn out of the job-posting corpus (tier 1, `corpus/resumes/synthetic/`); real
resumes, consented or the owner's, never committed and specified rather than collected
(tier 2, gitignored, empty); and the 36 existing band probes kept as a **control arm**
(tier 3). 09 runs on tier 1 today, prints tier 3 beside it, and says which tier every
number came from.

The specification, the provenance argument and the measurements are in
[acceptance-set.md](../acceptance-set.md). The short form of each of the ticket's three
questions:

1. **What a usable set looks like.** 30 documents — 30 paired band judgements and 150
   paired criterion judgements per category, so a category fails on a rate rather than
   an anecdote. Spread is drawn as *quality*, not as band: 11 of the 30 are off-track
   candidates. The binding requirement is 02's finding turned into a standing test —
   **no criterion in a behaviour category is constant across the set**. Two band quotas
   are stated and deliberately not enforced; §5 says why.
2. **Where they come from.** Written from briefs a seeded sampler draws out of
   `corpus/jds/` — 154 posting bullets, a pool rebuilt from the postings with its digest
   recorded — before any document is written. Nothing in the sampler names a category, a
   criterion or a band; how a resume *says* things is drawn per role on five independent
   axes; and **bands are observed afterwards, never targeted**. Where the set is thin the
   rule is more seeds, never an edit.
3. **What is committed.** Tier 1 is invented (no real person, employer or contact
   detail; fiction-range emails and phone numbers, asserted by test) and committed as
   text, with the PDFs generated. Tier 2 never reaches git — not the text, not a quote,
   not a locator — and what leaves it is answers, bands and hashes, the same treatment
   `baseline/run-summary.json` gets. The set freezes on a hash manifest, because a
   document that changes after a judge has read it invalidates the numbers silently.

## What running it found

**The fixtures' defect is gone.** Where `Agentic systems` and `AI-assisted coding
fluency` were band E on all seven fixtures — 60 answers, every one `no`, 22.5 composite
points carrying no information — all 19 rule-answerable criteria in the four behaviour
categories now vary across the 30 documents.

**Two `Resume craft` criteria stop discriminating on full-length documents.** C5
(`could not be anyone's`) is `no` on all 30 and C4 (`roles read differently`) is `yes` on
all 30. Both predicates are length-sensitive — C5 fails on *any* portable bullet, C2
needs an outcome in *every* role — and across all 66 documents anybody has, C5 is `yes`
on 5 of the 36 probes with six bullets or fewer and on **0 of the 30 with seven or
more**. The category was calibrated on two-role, four-bullet probes. This is evidence
for 12's open item that C4 and C5 are not independent, arriving before 09 got there, and
it goes back to the other map. Both constants are pinned by test so the finding cannot
change unnoticed.

**The band concentration is mostly the deterministic floor.** Three of four bandable
categories put over 40% of documents in D, and the anchored-versus-anywhere diagnostic
says why: `Production ownership` C2 is met 7/30 anchored and 28/30 anywhere in the
document, `Evaluation rigour` C2 11/30 against 30/30. Band D is *"claimed, but
unnameable"* and C2 is the conjunction that puts documents there. Whether the set
reaches B and C is 09's to settle — it is the first judge that can.

## What this cannot show, and is recorded rather than papered over

The session that wrote the prose had read the rubric, even though the sampler had not
and no document was aimed at a band. A model wrote the documents and models will judge
them. Agreement is not validity: two judges saying `D` is compatible with `D` being the
wrong reading. This set removes the circularity that made the old evidence base
worthless and replaces it with a smaller one it cannot remove by itself — which is what
tier 2 is for, and why it is specified with a consent record rather than quietly
dropped.

## Changed

- `scripts/draw_briefs.py`, `corpus/resumes/briefs.json` — the sampler and its draw.
- `corpus/resumes/synthetic/` — 30 documents; `manifest.json` — the freeze.
- `scripts/make_acceptance_set.py` — render, freeze, verify.
- `scripts/acceptance_coverage.py` — what the set reaches, with the floor diagnostic.
- `tests/test_acceptance_set.py` — 12 tests, including the two standing findings above.
- `corpus/resumes/README.md`, `docs/wayfinder/rubric-migration/acceptance-set.md`,
  `.gitignore`, and MAP.md.
