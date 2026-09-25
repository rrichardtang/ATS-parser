type: decision (HITL)
status: open
claimed: claude
blocked-by: —

# What a document pays when its judged categories cannot be assessed

## Question

Raised by rubric-migration 07's live run. When a resume's roles do not survive
extraction, all five judged categories are withheld: no criterion has a bullet to be
about. Migration 06 left them out of the composite, which renormalises over the three
the parser gate checked. So withholding costs nothing, and on live judges `two_column`,
which no parser can read, scores 86.6 and ranks first of the seven fixtures, 14.2 above
`strong`.

What should a withheld category contribute to the composite?
