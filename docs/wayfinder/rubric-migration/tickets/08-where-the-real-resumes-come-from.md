type: grilling (HITL)
status: open
claimed:
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
