type: task (AFK)
status: open
claimed:
blocked-by: —

# Unmet criteria come back as drafts

## Question

What does the candidate get for a criterion nothing on the resume speaks to?

## Decided

3 October (the owner): a fill-in-the-blanks draft. Every fact the resume lacks is a
typed placeholder, `[add: what you shipped]`, `[add: users served]`. No question-and-
answer step.

## What to build

1. **Carry unmet criteria onto the report.** Today `pipeline.analyze` drops
   `content.meta["unmet"]` and `Report` has no field for it. Add one, and keep it when
   the report is saved for a later "Generate rewrites" click.
2. **Draft them in pass 3.** Each unmet criterion becomes a target with no original
   bullet: the criterion text, the role it most plausibly belongs to, that role's
   bullets as context, and the posting digest. The writer returns a new bullet built
   from placeholders plus any fact already in that role (03's rule).
3. **Gate them differently.** Since 05, `ensemble.select_rewrite` compares a candidate with
   the original bullet: no new bullet-level rule, and a fixed one where rules fired. A
   draft has no original, so neither comparison applies, and `select_rewrite` reads the
   original from `resume.bullets` by locator, which a draft does not have. Drafts need
   their own gate. The fact-check still applies: every figure and specific must come from
   the role or sit inside `[add: …]`, and the draft should trip no bullet-level rule.
4. **Show them.** Decide where a draft sits in the report (see the map's *Not yet
   specified*) and render it in the HTML, Markdown and PDF reports.

Budget: drafts share pass 3's call, so count how many unmet criteria a typical resume
has before deciding whether they share `MAX_REWRITE_TARGETS` or get their own cap.

## Done when

A resume with unmet criteria gets one draft each (up to the cap), every draft passes the
fact-check, tests cover both, and Felix has approved it.

## Found
