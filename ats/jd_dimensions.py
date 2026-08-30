"""Qualitative requirement signals -- phrases that don't name a skill but describe
scope, seniority, or ownership expectations, so they can't go in the skill taxonomy.

"Own production systems end-to-end" isn't a keyword to add coverage for; it's a
signal about which *existing* rubric dimension matters most for a target role.
Each dimension here maps directly onto a check this codebase already makes:

  ownership        -> ats/invariants.py Ownership invariant; content/ownership
  production       -> ats/human.py credibility(): cred/no-production, cred/notebook-only
  evaluation       -> ats/human.py credibility(): cred/no-evaluation
  seniority        -> title/seniority-mismatch in ats/rules.py::title_alignment

Frequency across the user's curated postings never creates a new rubric axis --
it only ever scales how much an existing one is weighted for that user's runs (see
config.dimension_multiplier). "leadership" is tracked here for visibility but has
no scoring target yet -- keywords.py currently treats it as bonus-only, never a
penalty, and there's nothing to amplify until that changes.

Deliberately left out: cross-functional collaboration. Its natural phrasing
("partnered with product and design") is close enough to the ownership-dilution
pattern ("the team shipped X") that wiring it in without resolving that collision
would reward and penalise the same sentence shape at once.
"""
from __future__ import annotations

import re

DIMENSIONS: dict[str, list[str]] = {
    "ownership": [
        r"own(?:s|ed|ership)? .{0,20}(production|the full lifecycle|end.to.end)",
        r"end.to.end ownership",
        r"full(?: project| product)? lifecycle",
        r"design(?:ed)? (?:to|through) deployment",
        r"from design to deploy",
    ],
    "production": [
        r"\bon.call\b",
        r"incident response",
        r"\bslas?\b",
        r"\bslos?\b",
        r"\bproduction[- ](?:grade|system|service|environment|llm)",
        # Ship verb and destination, allowing words between them --
        # "shipped something meaningful to production" doesn't sit adjacent.
        r"\bship(?:ped|ping)?\b.{0,25}\bto (?:users|production|customers)\b",
        # "iteration in production", "into production", "reached production" --
        # broader than requiring a ship verb, since plenty of postings describe
        # production ownership without literally saying "ship."
        r"\b(?:in|into|reach(?:ed|ing)?)\s+production\b",
        r"\breliability\b",
    ],
    "evaluation": [
        r"rigorous evals?\b",
        r"evaluation (?:methodology|framework|harness)",
        r"offline (?:and|/|&) online metrics",
        r"measure (?:model )?quality",
        r"a/b test",
    ],
    "seniority": [
        r"ambiguous problems?",
        r"\b0 ?(?:to|-) ?1\b",
        r"greenfield",
        r"minimal (?:guidance|oversight)",
        r"self.directed",
    ],
    "leadership": [
        r"mentor(?:s|ed|ing)? (?:other )?engineers?",
        r"set(?:s|ting)? technical direction",
        r"lead(?:s|ing)? (?:a )?(?:team|project)",
        r"grow(?:s|ing)? (?:the team|other engineers)",
    ],
}

_COMPILED = {
    name: [re.compile(p, re.IGNORECASE) for p in patterns]
    for name, patterns in DIMENSIONS.items()
}


def scan(text: str) -> set[str]:
    """Which dimensions this posting's text signals, by pattern match. A boolean
    hit per posting, not a raw count -- a dimension mentioned five times in one
    posting shouldn't outweigh one mentioned once each in five different postings
    (same document-frequency-over-raw-count reasoning as the skill taxonomy)."""
    hit = set()
    for name, patterns in _COMPILED.items():
        if any(p.search(text) for p in patterns):
            hit.add(name)
    return hit
