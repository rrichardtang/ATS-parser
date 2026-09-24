---
name: protocol
description: How to run this harness. Use before spawning bob-the-builder or felix-the-fixer, when choosing a model for a subagent, when running the build-and-review loop, before a git push, or when asked which planning skill to use.
---

# Harness protocol

Installed as the `harness` plugin, every name below is namespaced: the agents are
`harness:bob-the-builder` and `harness:felix-the-fixer`, and the skills are `harness:caveman`,
`harness:wayfinder` and so on. Pass the namespaced name as the Agent tool's `subagent_type`.
Installed by the legacy `install.sh` sync, the same names appear bare.

## caveman

The `caveman` skill (ultra-compressed output, ~65% token cut) is installed and available via
`/caveman` or by saying "caveman mode" / "less tokens" / etc. **It is off by default in
interactive sessions** — nothing here turns it on automatically. `bob-the-builder` and
`felix-the-fixer` (below) each **preload** it via the `skills:` field in their frontmatter, since
they're the token/latency-sensitive part of this setup; the main session stays normal prose unless
you ask for it directly.

Preloading (`skills:` in a subagent's frontmatter) injects a skill's full body into that
subagent's context at startup, which is stronger than letting it call `Skill(...)` mid-run: the
skill shapes the work from the first token instead of after the agent has already decided how to
approach it, and it cannot be skipped. `bob-the-builder` preloads `ponytail` for exactly this
reason — clean code comes from constraints applied while writing, not from an audit afterwards.
Note that a skill marked `disable-model-invocation: true` can be neither preloaded nor invoked by
an agent; that flag makes a skill user-only, so never put it on one an agent is meant to use.

## Model selection for subagents

Neither `bob-the-builder` nor `felix-the-fixer` pins a model — the `model:` frontmatter field is
deliberately absent from both. The orchestrating (main) agent picks one **per spawn**, from how
hard *that particular task* looks, and passes it as the `model` parameter of the `Agent` tool. A
frontmatter model cannot tell a one-line rename from a concurrency rewrite; you can.

Pass it on **every** spawn. Omitting it does not fall back to something sensible — with no
frontmatter model and no configured default, the subagent inherits the caller's model, so a
trivial task handed off from an Opus session quietly runs on Opus.

Rough calibration. The task decides, not the role:

| Model | When |
|---|---|
| `haiku` | Fully specified and mechanical: a rename, deleting dead code, applying a fix you have already diagnosed, the same edit repeated across many files. |
| `sonnet` | The common case. Ordinary implementation against an approved plan; reviewing a small, self-contained diff. |
| `opus` | Genuinely hard: concurrency, state machines, protocol or shared-state changes, security-sensitive code, cross-cutting refactors, or requirements that are still fuzzy. |

Then adjust as the work shows you what it is:
- **Review at or above the model that wrote the code.** A cheap reviewer over an expensive
  implementer is the one pairing that reliably wastes both.
- **Escalate a round that failed.** If `felix-the-fixer` reports "not converging", or the same
  finding survives a round, raise `bob-the-builder`'s model for the next one instead of
  re-spawning at the same size — the 3-round cap spent entirely at the wrong size buys nothing.
- **Difficulty is reasoning, not line count.** A 400-line mechanical rename is `haiku` work; a
  five-line change to a locking protocol is `opus` work.
- **Say which model you picked and why** when you report a round, so the choice is reviewable
  rather than invisible.

(The `model` parameter also accepts `fable`; it is outside this rubric — pick it only on purpose.)

## Coding ↔ Review Loop (opt-in)

`bob-the-builder` (implements) and `felix-the-fixer` (reviews) can work a plan back and forth
instead of you driving every change by hand. **This is opt-in** — only run it when explicitly
asked to, after a plan has been approved. Most tasks are still handled directly.

When running it:
- **Cap at 3 rounds** of `bob-the-builder` → `felix-the-fixer`. This is a hard cutoff, not a
  suggestion — an unbounded review loop is worse than a bounded one that sometimes needs a human.
- **Round 1:** `bob-the-builder` implements against the approved plan; `felix-the-fixer` reviews
  the diff.
- **Round 2+:** carry forward *every* prior round's findings into `bob-the-builder`'s next
  prompt — subagents are stateless per spawn, they don't remember earlier rounds on their own.
  `bob-the-builder` states up front whether the previous fix addressed the review's root cause
  or only patched the flagged lines before making new edits. Recurring or reshaped findings
  across rounds are the signal to fix the underlying cause, not keep patching symptoms — and
  `felix-the-fixer` is instructed to call this out explicitly as "not converging" when it sees it.
- **After round 3**, if `felix-the-fixer` still finds issues: stop. Do not start a 4th round
  automatically. Summarize what's still wrong and ask how to proceed.

`bob-the-builder` also runs a `thermo-nuclear-code-quality-review` self-check on its own diff
before stopping (its own instructions, "Finishing"). That skill is deliberately **not** gated with
`disable-model-invocation`, unlike the planning front doors: its consumer is an agent, not a
person, and the flag would block the `Skill` call bob depends on. The self-check is a structural pass (file size, spaghetti
conditionals, thin wrappers), not a substitute for `felix-the-fixer`'s independent correctness and
simplification review.

**Notes boundary:** if the repo you're in has a living-notes convention (a `PROJECT_NOTES/`
directory or equivalent), only the orchestrating (main) agent reads and writes it. Extract just
the task-relevant slice — the specific bug, decision, or preference that matters for this task —
into what you send `bob-the-builder`/`felix-the-fixer`; don't have them read the file directly.
After they report a completed round, you decide what (if anything) graduates into that repo's
notes. `bob-the-builder` and `felix-the-fixer` each keep their own smaller, role-scoped log
instead — `.claude/agent-notes/bob.md` and `.claude/agent-notes/felix.md` in whatever repo
they're working in — for things future rounds of *that specific role* should know, separate from
the project's higher-level notes.

## Planning skills (opt-in)

`wayfinder` and `grill-with-docs` are front doors for planning code changes in the main session —
**explicit-invoke only** (`disable-model-invocation: true`), so neither fires on its own. That flag
blocks the `Skill` tool as well as auto-triggering, so **you** start them by typing `/wayfinder` or
`/grill-with-docs`; the agent cannot reach them, and asking it to is a dead end.
`grill-with-docs` sharpens a plan within one session (interview via `grilling`, glossary/ADR
capture via `domain-modeling`). `wayfinder` is for work too large for one session: it charts a
shared map of decision tickets on the repo's issue tracker (falling back to local markdown) and
works them one at a time — its body is denser than this summary should try to restate, and the
agent can read `${CLAUDE_PLUGIN_ROOT}/skills/wayfinder/SKILL.md` directly for the full protocol.

Their building blocks are separate, standalone skills, each still available on its own:
- `grilling` — the interview primitive; auto-triggers on "grill" phrasing, not gated like the two
  above.
- `domain-modeling` — builds/sharpens a project's `CONTEXT.md` glossary and ADRs; can auto-trigger
  when terminology is being discussed.
- `research` — delegates a documentation/API question to a background agent; can auto-trigger.
- `prototype` — throwaway code to answer a design question (state-model logic or UI shape); can
  auto-trigger.

Unlike `wayfinder`/`grill-with-docs`, these four are not `disable-model-invocation`-gated — that's
upstream's design (they're useful standalone, e.g. "grill me about this" without going through
wayfinder), not something layered on here.
