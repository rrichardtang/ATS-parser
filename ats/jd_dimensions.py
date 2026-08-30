"""Qualitative requirement signals -- phrases that don't name a skill but describe a
behaviour the posting expects, so they can't go in the skill taxonomy.

"Own production systems end-to-end" isn't a keyword to add coverage for; it is the
posting stating a behaviour, and document frequency over behaviours is what sets a
rubric category's weight (ticket 04) and scales a rule's cost (config.RULE_DIMENSION).

Each dimension is a behaviour, and the rubric categories are unions of them:

  production, ownership, reliability -> Production ownership   (04 merges the three)
  agentic                            -> Agentic systems
  evaluation                         -> Evaluation rigour
  ai_assisted_coding                 -> AI-assisted coding fluency
  seniority                          -> title/seniority-mismatch in ats/rules.py
  experience_gate                    -> no target yet; recorded, never scored

See CATEGORY_DIMENSIONS below for the mapping and category_document_frequency() for
the count 04's weights are derived from.

**Patterns are families, not sentences.** Each is a verb set crossed with an object
set, because the corpus these were written against is six postings and the point of
deriving weight from a corpus is that the seventh posting moves it without anyone
editing this file. A pattern that only matches one posting's phrasing is overfitting
and belongs in the test, not here. `docs/wayfinder/rubric-grounding/dimension-scan.md`
records the counts each family reproduces and the quote behind each.

Deliberately left out: cross-functional collaboration. Its natural phrasing
("partnered with product and design") is close enough to the ownership-dilution
pattern ("the team shipped X") that wiring it in without resolving that collision
would reward and penalise the same sentence shape at once.

Removed in ticket 09: "leadership". It had no scoring target, read 0/6 on the real
corpus, and a dimension nothing consumes is an invitation to wire it up without
deciding what it should cost.
"""
from __future__ import annotations

import re

# Verb families reused across dimensions, so "shipped" and "deployed" are never
# spelled out in one dimension and forgotten in another.
_SHIP = r"(?:ship|shipp?(?:ed|ing)|deploy(?:ed|ing|ment)?|launch(?:ed|ing)?|releas(?:e|ed|ing)|roll(?:ed)? out|rollout)"
_DESTINATION = r"(?:production|prod|users?|customers?|live|traffic|the field|market)"
_BUILD = r"(?:build|building|built|design(?:ed|ing)?|develop(?:ed|ing|ment)?|implement(?:ed|ing)?|extend(?:ed|ing)?|create?d?|ship(?:ped|ping)?)"

DIMENSIONS: dict[str, list[str]] = {
    # Did the work reach somewhere real, and does the posting talk about it running?
    "production": [
        # "in production", "into production", "to production", "reached production"
        r"\b(?:in|into|to|reach(?:ed|ing)?|within)\s+production\b",
        # "production LLM systems", "production code", "production-grade experiences"
        r"\bproduction[- ](?:grade|quality|code|system|systems|service|services|environment|application|applications|llm|ml|ai|logs|traffic|readiness|ready)\b",
        # a ship verb with a destination, allowing words between them
        rf"\b{_SHIP}\b[^.]{{0,40}}\b{_DESTINATION}\b",
        r"\bon.call\b",
        r"\bincident (?:response|management)\b",
        r"\bsl[ao]s?\b",
        r"\b(?:live|real|production)\s+traffic\b",
    ],
    # Does responsibility span a lifecycle rather than stopping at the handoff?
    "ownership": [
        # "own models end to end", "owning them through ambiguity", "technical ownership"
        r"(?<!\byour )(?<!\bour )(?<!\btheir )(?<!\bmy )(?<!\bits )\bown(?:s|ed|ing|ership)\b",
        r"\bend[ -]?to[ -]?end\b",
        # a lifecycle span: "from discovery through deployment", "from concept to production"
        r"\bfrom\b[^.]{0,80}?\b(?:through|to|into)\b[^.]{0,40}?\b(?:production|deployment|deploy|adoption|launch|release|rollout|delivery)\b",
        # staying with it: "help operate what you build after launch"
        r"\b(?:operate|operating|operation|maintain(?:ing)?|support(?:ing)?|iterat(?:e|ing|ion))\b[^.]{0,60}\b(?:after launch|in production|post.launch|what you (?:build|ship))",
        r"\bafter launch\b",
        r"\bfull(?: project| product)? lifecycle\b",
    ],
    # Is the candidate answerable for how the thing behaves once it is running?
    "reliability": [
        r"\breliabilit(?:y|ies)\b|\breliable\b",
        r"\brobustness\b",
        r"\buptime\b|\bavailability\b",
        r"\bguardrails?\b",
        r"\btrustworthy\b|\bauditability\b|\bauditable\b",
        r"\bmonitor(?:s|ed|ing)?\b",
        r"\b(?:failure|error) (?:modes?|analysis|handling)\b",
    ],
    # Systems that reason over context, call tools and act -- built, advised on, or used.
    "agentic": [
        r"\bagentic\b",
        r"\bagents?\b",
        r"\btool[- ](?:use|using|calling)\b",
        r"\bautonomous\b|\bautonomy\b",
    ],
    # Measuring quality with something that could return a negative answer.
    "evaluation": [
        r"\bevals?\b|\bevaluations?\b|\bevaling\b",
        r"\bevaluation (?:suites?|frameworks?|harnesses?|methodolog\w+|tooling)\b",
        r"\bbenchmark(?:s|ed|ing)?\b",
        r"\ba/b test",
        r"\bmeasure\b[^.]{0,40}\b(?:quality|performance|regressions?|accuracy)\b",
        r"\bregressions?\b[^.]{0,30}\b(?:test|suite|catch|caught|measure)|\b(?:test|suite|measure)\w*[^.]{0,30}\bregressions?\b",
    ],
    # Working with AI coding tools as a practice, not building them.
    "ai_assisted_coding": [
        r"\bai[- ]assisted\b",
        r"\bai[- ](?:coding|dev|development)\b",
        r"\b(?:coding|dev|development)\s+(?:models?|agents?|assistants?)\b",
        r"\bagentic (?:development|coding|engineering)\b",
        r"\b(?:copilot|cursor|claude code|codeium|windsurf|aider)\b",
        rf"\b(?:with|using)\s+ai\s+(?:coding\s+)?tools?\b",
    ],
    # Working without a spec, which is what the seniority rule is about.
    "seniority": [
        r"ambiguous problems?|\bambiguity\b",
        r"\b0 ?(?:to|-) ?1\b",
        r"greenfield",
        r"minimal (?:guidance|oversight|supervision)",
        r"self.directed",
    ],
    # A numeric experience gate. Recorded because half the corpus states one and no
    # dimension saw it (02); nothing scores it, and nothing should until a rule exists.
    "experience_gate": [
        r"\b\d+\+?\s*(?:-|to)?\s*\d*\+?\s*years?\b[^.]{0,40}\bexperience\b",
        r"\bexperience\b[^.]{0,20}\b\d+\+?\s*years?\b",
    ],
}

# 04's rubric categories are unions of these behaviours: a posting counts toward a
# category if it states any of them. The merge is 04's separability judgement --
# production, ownership and reliability arrive in single clauses in this corpus --
# not an artifact of the patterns.
CATEGORY_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "Production ownership": ("production", "ownership", "reliability"),
    "Agentic systems": ("agentic",),
    "Evaluation rigour": ("evaluation",),
    "AI-assisted coding fluency": ("ai_assisted_coding",),
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


def categories_for(dimensions: set[str]) -> set[str]:
    """The rubric categories one posting's dimension hits count toward."""
    return {
        category for category, members in CATEGORY_DIMENSIONS.items()
        if dimensions.intersection(members)
    }


def category_document_frequency(per_posting: list[set[str]]) -> dict[str, int]:
    """How many postings state each category's behaviour. This is the number 04
    derives category weight from."""
    counts = {category: 0 for category in CATEGORY_DIMENSIONS}
    for dimensions in per_posting:
        for category in categories_for(dimensions):
            counts[category] += 1
    return counts


def derived_weights(counts: dict[str, int], total: int, budget: float) -> dict[str, float]:
    """Split `budget` points across the behaviour categories in proportion to their
    document frequency.

    `budget` is a parameter and not a constant on purpose: 04 settled that df sets
    these weights and left how many of the composite's 100 points the derived block
    gets as an open question on the map. This function is the derivation; the number
    it divides is still authored.

    A category no posting states gets 0 and does not consume budget -- the corpus
    saying nothing about a behaviour is the corpus saying it is not worth points.
    """
    if total <= 0:
        return {category: 0.0 for category in counts}
    shares = {category: count / total for category, count in counts.items()}
    denominator = sum(shares.values())
    if denominator == 0:
        return {category: 0.0 for category in counts}
    return {
        category: round(budget * share / denominator, 2)
        for category, share in shares.items()
    }
