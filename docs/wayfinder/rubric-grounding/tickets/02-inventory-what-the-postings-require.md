type: research (AFK)
status: open
claimed:
blocked-by: 01

# Inventory what the six postings actually require

## Question

With extraction repaired, what do these postings actually ask for — in their own
language, not the taxonomy's? Produce the evidence base the category set will be
built from: recurring requirements with document frequency, the dimensions they
emphasise, and the phrasing they use.

`ats/jd_digest.json` is not that evidence base and cannot become it: its document
frequencies are counted only over the 57 terms hand-authored in
`ats/skill_groups.py`, and its dimensions only over the five regex sets in
`ats/jd_dimensions.py`. Anything these postings require that nobody has already
named is invisible to it — which is exactly the material a category set derived
from the corpus needs. Ticket 01 closed having shown this is now the binding
constraint: `rag` reads 0/6 required over a corpus in which fluidstack asks for
"retrieval systems" and edra for "context engineering". Read the six postings in
`corpus/jds/user/` directly; the digest cross-checks what the taxonomy already
covers, it is not the source.

Start from the three findings ticket 01 hands over: the 3/6 ceiling on any named
term, the alias gap above, and nice-to-haves that appear as inline `Bonus:` bullets
rather than as sections. The first is the one to weigh hardest — if these postings
genuinely do not converge on named tools, a category set built on "what most
postings require" has less to stand on than it sounds like, and this inventory is
where that is established or refuted.

This is deliberately descriptive, not prescriptive. It answers "what is in the
corpus", so that ticket 04 can decide "what should the categories be" against
evidence rather than intuition.

Done when: `docs/wayfinder/rubric-grounding/inventory.md` exists, recording each
recurring requirement with the number of postings it appears in and at least one
verbatim quote, and naming what the taxonomy misses — enough that a reader could
use it to argue for or against any proposed category.
