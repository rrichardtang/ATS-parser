# Band probes

Short resumes written to land on a particular band, or on the boundary between two.
One directory per category.

They exist because `tests/fixtures/` cannot exercise a content rubric: four of its seven
carry the same bullets, three carry almost nothing, and every one that can be answered
lands at one end of the ladder. Ticket 05 found three of five bands unreachable for
`Production ownership`; the same is true of every category since.

These are plain text, not PDFs, and they live here rather than in `tests/fixtures/`
because they test the **rubric**, not the parser. They are handed to the probe already
readable, so a criterion disagreement is about the criterion.

Format is the minimum `ats.sections.parse` needs: a role heading with a date range, then
bullets.

| directory | ticket | probes | reaching |
|---|---|---|---|
| `production-ownership/` | 05 | 7 | E, D, C, B, A |
| `ai-assisted-coding-fluency/` | 11 | 8 | E, D, C, B, A |
| `evaluation-rigour/` | 11 | 7 | E, D, C, B, A |
| `agentic-systems/` | 11 | 7 | E, D, C, B, A |
| `resume-craft/` | 12 | 7 | E, D, C, B, A |

`tests/test_criteria_probe.py` asserts each set reaches at least four of the five bands
and that every probe parses. Two probes are written to fail rather than to pass:

- `ai-assisted-coding-fluency/8-tool-not-on-the-list.txt` is `7-fluent` with one tool
  name swapped for one the alias list has never seen. It is the standing test of 04's
  claim that a name list for AI coding tools goes stale.
- `agentic-systems/2-coding-agent-user.txt` is a heavy Cursor user who has built no
  agent. It holds the line 02 drew between building agents and using them.

`resume-craft/` differs from the other three in what its probes vary. The behaviour
categories ladder on *how much evidence exists*; craft ladders on *how many defects
remain*, so its probes are the same resume with one criterion knocked out at a time —
`6-same-job-twice` and `7-no-identity` are `5-edited` with exactly one thing wrong.
