# The acceptance set: what 09 measures on, and where it came from

Ticket 08. The evidence base before this was seven PDF fixtures, thirty-six band probes
and one uncommittable real resume, and every one of those documents was written by a
session that was also judging it. This is the specification that replaces it, the
provenance and privacy decisions behind it, and what the set actually reaches when it
is read back.

*(Thirty-six, not the twenty-nine the ticket and MAP say: 7 + 8 + 7 + 7 for the four
behaviour categories, plus the 7 `resume-craft/` probes 12 added afterwards. The count
was never updated. It changes nothing except that the old evidence base was slightly
larger than advertised and no less self-written.)*

## 1. The decision, in short

Three tiers, and only the first is committed.

| tier | what | how many | committed | what it can support |
|---|---|---|---|---|
| **1** | invented documents written from briefs drawn out of the posting corpus | 30 | yes | 09's agreement measurement |
| **2** | real resumes, the owner's or consented | ≥10, when they exist | **never** | whether the rubric's bands mean anything about real candidates |
| **3** | the existing 36 band probes | 36 | already | the control arm — see §6 |

Tier 1 exists now, in `corpus/resumes/synthetic/`, and 09 can run on it today. Tier 2 is
specified, gitignored and empty; it is what would upgrade 09's verdict from *these two
judges agree* to *these two judges agree about real resumes*. Tier 3 is not retired: 09
runs on it too, because the gap between agreement there and agreement on tier 1 is the
first measurement anybody has of what writing your own test set was worth.

## 2. What a usable test set looks like

The ticket asked for three things: how many, at what spread, covering which behaviours.

**How many: 30.** Not a power calculation — there is no prior worth putting a number
on — but the smallest set where the measurement 09 makes is legible. Thirty documents
give each category 30 paired band judgements and 150 paired criterion judgements per
provider pair; one criterion disagreement is 0.7% and one band disagreement 3.3%, so a
category can fail on a rate rather than on an anecdote. Below about 20 a single split
swamps the number, which is exactly the position the 36 probes leave `Resume craft` in.

**What spread: quality, not band.** A set where every document is a strong AI engineer
tests nothing and neither does one where every document is bad, so the sampler draws an
off-track candidate about 30% of the time — a backend engineer with no AI work, a data
analyst moving toward ML, an academic leaving a lab — and their work is drawn mostly
from the ordinary-engineering half of the posting pool. Eleven of the thirty are
off-track.

**Which behaviours: all four, and none of them constant.** This is the requirement 02
found the fixtures failing: `Agentic systems` and `AI-assisted coding fluency` were band
E on all seven, 60 recorded answers all `no`, so 22.5 of the composite's points carried
no information and any agreement measured there was agreement about a constant. The
standing form of that requirement is *no criterion in a behaviour category is constant
across the set*, and it is `tests/test_acceptance_set.py`, not a paragraph.

Two quotas are stated and deliberately **not** enforced: every band reached by at least
3 documents, and no band holding more than 40%. §5 says why they cannot be checked here.

## 3. Where they come from

Four options, and the trap the ticket named is that the cheapest one reintroduces the
problem.

| option | cost | what it buys |
|---|---|---|
| public resumes, scraped | personal data of people who did not volunteer; licensing; uncommittable | real ambiguity, real distribution |
| consented submissions | needs a person to ask people, and time | the same, plus a defensible provenance |
| a model writing resumes with the rubric in view | free | **nothing** — a rubric agreeing with documents written to satisfy it |
| documents written from briefs that never mention the rubric | cheap | non-circular in the one way 09 needs; silent about validity |

Tier 1 is the fourth, built so the third cannot creep back in:

- **The content is drawn, not chosen.** `scripts/draw_briefs.py` seeds a sampler from
  `corpus/jds/` — 154 requirement and responsibility bullets across the generic and
  personal posting corpora — and draws each document's career before any of it is
  written: track, seniority, employers, domains, career texture, document shape, and
  2–4 posting bullets per role as the work that role is about. The pool is rebuilt from
  the postings each run and its digest is in `briefs.json`, so tuning it toward a
  criterion means editing a posting, which the taxonomy would notice.
- **How the resume *says* it is drawn per role, on five independent axes**: whether
  numbers appear, how specifically things are named, whose voice the bullets are in,
  whether anything after launch is mentioned, whether a setback is admitted. These are
  the axes every resume-writing guide names, and they overlap the criteria — they had
  to, or the set would be constant like the fixtures. What matters is that they are
  drawn independently, per role, from a per-document seed. A document's band in a
  category is the interaction of three to five separate draws across two to five roles.
  Nobody aims that, including the person writing the prose.
- **Bands are observed afterwards and never targeted.** §5 is what the set reached, read
  back off the documents. Where it is thin, the rule is more seeds — never an edit to a
  document that already exists.

Two freedoms the writing took, both recorded because they are where a thumb could go on
the scale. Role index 0 is the most recent role. Where a draw contradicts itself — a
"junior, ~1 year" candidate drawn three roles totalling six years, an "academic leaving
the lab" drawn a big-tech employer — the prose resolves it the most plausible way, and
never by touching the five detail axes, which are what the bands turn on.

## 4. What is committed, and what is not

`baseline/run-summary.json` is the precedent: the raw run is gitignored because it
quotes resume text, and the redacted form keeps the arithmetic checkable. The same
treatment, stated as three rules:

1. **Tier 1 is invented and is committed.** No real person, employer, address, phone or
   email, and nothing lifted from a real resume. Emails are `@example.com` and phone
   numbers are in the 555-01xx fiction range, asserted by a test rather than by care.
2. **Tier 2 never reaches git.** Not the PDF, not the text, not a quote, not a locator
   that reproduces one. `corpus/resumes/real/` is gitignored and carries a consent
   record per document (`<name>.consent.json`: source, date, scope, how to withdraw).
   What leaves it is criterion answers, bands and hashes — 09's arithmetic, checkable,
   with the resume absent. The one real resume the project already has is the owner's
   and is handled the same way.
3. **The set freezes.** `manifest.json` holds a hash per document; a document that
   changes after a judge has read it silently invalidates every number measured on it.
   `--verify` is in the test suite. Changing a document is not forbidden; it is a *new*
   document, and re-freezing means saying so here.

The PDFs are generated rather than committed, following `tests/make_fixtures.py`: the
text stays reviewable in the diff. Layout varies per document — font, body size,
margins, from the document's own hash — because real resumes do not share a template
and a judge should not be able to learn one. The variation introduces no parser defect:
single column, real text layer, no injection. Extraction failures are the seven
fixtures' job and stay there.

## 5. What the set reaches

`scripts/acceptance_coverage.py`, deterministic judge, no provider. All 30 parse; all 30
render to a PDF the parser reads; none is withheld.

### Bands, and the criteria under them

| category | E | D | C | B | A |
|---|---|---|---|---|---|
| Production ownership | 3 | 22 | 1 | 0 | 4 |
| Evaluation rigour | 10 | 12 | 6 | 0 | 2 |
| Agentic systems | 4 | 20 | 3 | 1 | 2 |
| Resume craft | 1 | 23 | 6 | 0 | 0 |
| AI-assisted coding fluency | — the deterministic judge abstains; C5 has no rule channel |

**The requirement is met: no criterion in a behaviour category is constant.** Against
the fixtures' 60 answers all `no` across two whole categories, the four behaviour
categories now vary on all 19 criteria a rule can answer — `Agentic systems` C1 26/30,
C5 6/30; `Evaluation rigour` C1 20/30, C4 9/30; `AI-assisted coding fluency` C1 4/30,
which is thin and is real: naming Cursor or Claude Code on a resume is still rare.

**The band concentration is mostly the floor, not the set.** Three of the four bandable
categories put over 40% of documents in D, which would be a coverage failure if the
judge could be trusted at the boundary. It cannot: an anchored criterion is answered
inside the bullet that settled its anchor, and a resume that names its system in the
*next* bullet answers `no` from the regex and `yes` from any reader.

| criterion | met, anchored | the same predicate anywhere in the document |
|---|---|---|
| Production ownership C2 (named system) | 7/30 | 28/30 |
| Evaluation rigour C2 (named metric and number) | 11/30 | 30/30 |
| Agentic systems C2 (named system) | 6/30 | 28/30 |
| AI-assisted coding fluency C3 (changed practice) | 2/30 | 24/30 |

Band D is *"claimed, but unnameable, or nothing says it ran"* in three of these
categories, and C2 is the conjunction that puts documents there. So the band quotas are
printed as notes rather than enforced as failures: **09 is the first judge that can
settle whether this set reaches B and C, and if it does not, the fix is more seeds.**

### A finding the probes were too short to see

`Resume craft` C4 is `yes` on all 30 and C5 is `no` on all 30, and both are properties of
the predicates rather than of the set:

| | documents | mean roles | mean bullets | C2 met | C5 met |
|---|---|---|---|---|---|
| the 36 band probes | 36 | 1.2 | 3.4 | 27/36 | 5/36 |
| this set | 30 | 3.2 | 11.7 | 1/30 | 0/30 |

C5 (`could not be anyone's`) fails a document if **any** bullet is portable, and C2
(`names what changed`) needs an outcome bullet in **every** role. Both get strictly
harder with length, and the measurement is unambiguous: across all 66 documents, C5 is
`yes` on 5 of the 36 with six bullets or fewer and on **0 of the 30 with seven or
more**. C4 (`roles read differently`) inverts for the same reason — with three or four
roles in different domains, no two are a retelling.

The category was calibrated on two-role, four-bullet probes. On documents the length of
real resumes, two of its five criteria stop discriminating, which drags every document
into D and is the reason `Resume craft` reaches three bands here rather than five. That
is a rubric finding, not a set defect, and it belongs to the other map: it is evidence
for 12's open item that C4 and C5 are not independent, arriving from a direction 12 did
not look. 09 pre-registered `Resume craft` as where this should fail first. It failed
before 09 got there. `tests/test_acceptance_set.py` pins both constants so the finding
cannot change unnoticed.

### The deterministic-only composite

Every document through `ats.pipeline.analyze` with no provider: 47.9 (`19-academic-terse-mid`)
to 67.2 (`10-new-grad-agentic`), 13 documents at D and 17 at F, 25 to 59 findings each.
The judged categories are unassessed on this path — 06's renormalisation — so this
number is the deterministic layer's spread and nothing about the rubric. It is here as a
smoke test: 30 documents, 30 distinct composites, no clustering at a cap, no crash.

## 6. What this set cannot show, said plainly

- **The session that wrote the prose had read the rubric.** The sampler had not, the
  briefs do not mention it, and no document was aimed at a band — but the prose was
  written by a party who knows what the criteria ask. That is the residual circularity
  and it does not go to zero without tier 2.
- **A model wrote the documents and models will judge them.** Prose written by one model
  may be legible to another in ways a human's resume is not, which would inflate
  agreement. Nothing here measures that. Tier 2 does.
- **Nothing here says a band is *correct*.** Agreement is not validity. That the two
  judges both say `D` is compatible with `D` being the wrong reading of the document,
  and no synthetic set can close that: it needs real resumes and someone who knows the
  candidate.
- **It is one draw.** Seed 20260908, 30 documents, one pool digest. Extending the draw
  is cheap and adds documents without moving existing ones — briefs are seeded
  per-document for that reason — but the set as it stands is a sample of one sampler.

The honest summary: this set removes the circularity that made the *old* evidence base
worthless, and replaces it with a smaller circularity it cannot remove by itself.

## 7. What 09 should do with it

1. **Run tier 1 and tier 3 separately and print both.** The probes were written and
   judged by the same sessions; these were not. If criterion agreement is materially
   higher on the probes, that difference is the measurement of what self-written test
   sets were buying, and it is the first number anybody has for it.
2. **Report the band quotas §5 could not certify.** With two model judges, `Production
   ownership` B and C either fill or they do not. If they do not, draw more briefs —
   `--count 40` extends without disturbing documents 1–30 — and never edit a document.
3. **Do not fold `Resume craft`'s constants into a tolerance verdict** without saying
   the length finding out loud. Two of its five criteria do not discriminate on
   full-length documents, and a category with three live criteria has a different
   agreement profile from one with five.
4. **Say which tier every number came from.** A tolerance verdict on tier 1 is a claim
   about invented documents. It is a much better claim than the fixtures could support
   and it is still not the claim the other map's Destination makes.

## 8. Changed

- `scripts/draw_briefs.py` — new. The sampler: a pool rebuilt from `corpus/jds/`, and a
  seeded per-document draw of career, register, shape and the five detail axes. Names no
  category, criterion or band.
- `corpus/resumes/briefs.json` — the 30 drawn briefs, the seed and the pool digest.
- `corpus/resumes/synthetic/*.txt` — the 30 documents, written from those briefs.
- `corpus/resumes/manifest.json` — the freeze: a hash per document, verified by the
  suite.
- `scripts/make_acceptance_set.py` — renders the PDFs (gitignored), freezes and verifies.
- `scripts/acceptance_coverage.py` — what the set reaches, with the anchored-versus-
  anywhere diagnostic that says how much of a thin band is the floor.
- `tests/test_acceptance_set.py` — 12 tests: the size floor, every document parses and
  renders, the manifest and the briefs reproduce from their seed, the pool still comes
  from the postings, no invented contact detail escapes the fiction ranges, the quality
  spread holds, **no behaviour criterion is constant**, and `Resume craft`'s two
  constants are pinned to the finding above.
- `corpus/resumes/README.md` — the operating manual, including how to add tier 2.
- `.gitignore` — `corpus/resumes/rendered/` and `corpus/resumes/real/`.
