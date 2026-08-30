type: grilling (HITL)
status: open
claimed:
blocked-by: 04

# Does Coverage duplicate the deterministic keyword rules?

## Question

`ats/keywords.py` already emits `jd/missing-core`, `jd/missing-secondary` and
`jd/missing-named-tools` against the digest, and `kw/unsupported-skills` against the
resume. A `Coverage` category scored by the model would measure something close to
the same thing from the same source.

Two mechanisms scoring one property is how a resume gets penalised twice for one gap.
Decide which layer owns coverage: the deterministic rules feed it as evidence and the
model does not score it, the model owns it and the rules are retired, or they measure
genuinely different things and both stay — stated precisely enough to defend.
