"""Slop patterns ported from the no-ai-slop skill (MIT, Peter Yang), scoped to
resume form. See vendor/no-ai-slop/ for the source text and licence.

Two adaptations the source does not make, both deliberate:

1. Scope. The skill targets prose. A resume bullet is a different form, so every
   pattern declares where it legitimately applies. Flagging a bullet for lacking a
   conversational cadence would be noise.
2. No scoring of authorship. The skill's rule -- "AI detectors guess, named
   patterns are evidence the user can check" -- is why nothing here produces an
   AI-likelihood number. Each hit carries the quoted span and a fix.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from .models import Provenance, Severity


class Scope(str, Enum):
    BULLET = "bullet"
    SUMMARY = "summary"
    DOCUMENT = "document"


@dataclass(frozen=True)
class SlopPattern:
    id: str
    scope: Scope
    fix: str
    severity: Severity = Severity.MINOR
    regex: re.Pattern[str] | None = None
    detector: Callable[[str], list[str]] | None = None
    provenance: Provenance = Provenance.RECRUITER_EVIDENCE

    def find(self, text: str) -> list[str]:
        if self.detector is not None:
            return self.detector(text)
        if self.regex is None:
            return []
        return [m.group(0) for m in self.regex.finditer(text)]


def _words(*terms: str) -> re.Pattern[str]:
    return re.compile(r"(?i)\b(" + "|".join(terms) + r")\b")


# Banned outright by the skill. Trimmed to terms that are disproportionately
# LLM-usage rather than merely formal: "spearheaded" predates LLMs by decades and
# is not included, though the skill's own list is broader.
BANNED = _words(
    "delve", "delving", "delved", "foster", "fostering", "leverage", "leveraging",
    "leveraged", "utilize", "utilizing", "utilized", "facilitate", "facilitating",
    "empower", "empowering", "streamline", "streamlining", "robust", "cutting-edge",
    "paradigm shift", "game changer", "tapestry", "realm", "beacon", "multifaceted",
    "meticulous", "meticulously", "intricate", "paramount", "transformative",
    "elevate", "elevating", "embark", "supercharge", "harness", "harnessing",
    "ever-evolving", "seamless", "seamlessly", "holistic", "synergy", "synergies",
)

# Trailing -ing clauses that pretend to explain significance.
SUPERFICIAL = re.compile(
    r"(?i),\s*(highlighting|underscoring|reflecting|showcasing|demonstrating|"
    r"emphasizing|illustrating|signifying|showing)\b[^.]*"
)

PUFFERY = re.compile(
    r"(?i)\b(stands as a testament|marks a pivotal|plays a (?:vital|key|crucial) role|"
    r"solidif\w+ (?:its|my|their) position|underscores? (?:its|my|the) significance|"
    r"commitment to excellence|passion for excellence|proven track record of success|"
    r"a testament to)\b"
)

FAKE_STRONG_VERB = re.compile(
    r"(?i)\b(serv(?:es|ed|ing) as a|act(?:s|ed|ing) as a|function(?:s|ed|ing) as a)\s+"
    r"(?:centralized|central|single|unified|comprehensive)?\s*"
    r"(hub|solution|platform|resource|vehicle|framework)\b"
)

WEASEL = re.compile(
    r"(?i)\b(experts agree|industry reports suggest|many argue|widely regarded as|"
    r"studies show|it is well known|research suggests)\b"
)

BINARY_CONTRAST = re.compile(
    r"(?i)((?:it'?s|this is|that'?s) not (?:just )?(?:about )?[^.]{2,50}?\.\s*(?:it'?s|but)\b"
    r"|the question isn'?t[^.]{2,60}?,?\s*it'?s\b"
    r"|not only[^.]{2,60}?but also\b)"
)

NEGATIVE_LISTING = re.compile(r"(?i)\bnot a [^.]{2,30}\.\s*not a [^.]{2,30}\.")

THROAT_CLEARING = re.compile(
    r"(?i)\b(here'?s the thing|here'?s what i mean|let me be clear|i'?ll be honest|"
    r"the uncomfortable truth is|make no mistake)\b"
)

FAUX_INSIGHT = re.compile(
    r"(?i)\b(this is the part most people skip|what most people get wrong|"
    r"here'?s what nobody tells you|the part everyone misses|what they don'?t tell you)\b"
)

RHETORICAL = re.compile(
    r"(?i)\b(what if i told you|think about it:|plot twist:|here'?s the kicker)"
)

METADISCOURSE = re.compile(
    r"(?i)\b(that last part matters|the key point is|as you can see|"
    r"this distinction matters|in other words|it'?s worth noting|"
    r"it'?s important to note)\b"
)

EMPTY_PHRASE = re.compile(
    r"(?i)\b(at the end of the day|when it comes to|at its core|in today'?s world|"
    r"in the age of|in the world of|the reality is|going forward)\b"
)

COLON_REVEAL = re.compile(r"(?m)^[A-Z][\w ]{2,40}:\s+[a-z][^.\n]{10,}$")

SUMMARY_RECAP = re.compile(r"(?i)\b(in conclusion|ultimately|overall,|to sum up)\b")


def _em_dash_clusters(text: str) -> list[str]:
    """One em dash can beat a comma. Three in a line is a rhythm crutch."""
    hits = []
    for line in text.splitlines():
        if line.count("—") >= 2:
            hits.append(line.strip()[:120])
    return hits


def _emoji_headings(text: str) -> list[str]:
    emoji = re.compile(
        "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
    )
    return [l.strip() for l in text.splitlines() if emoji.search(l)]


PATTERNS: list[SlopPattern] = [
    SlopPattern("slop/banned-word", Scope.BULLET, "Use the plain verb for what you did.",
                Severity.MINOR, regex=BANNED),
    SlopPattern("slop/superficial-analysis", Scope.BULLET,
                "Replace the trailing clause with the concrete result.",
                Severity.MAJOR, regex=SUPERFICIAL),
    SlopPattern("slop/importance-puffery", Scope.BULLET,
                "State the fact and let the reader judge whether it matters.",
                Severity.MAJOR, regex=PUFFERY),
    SlopPattern("slop/fake-strong-verb", Scope.BULLET,
                "Say what it does: 'tracks sponsors, drafts and approvals in one place'.",
                Severity.MINOR, regex=FAKE_STRONG_VERB),
    SlopPattern("slop/weasel-attribution", Scope.BULLET,
                "Name the source or cut the claim.", Severity.MAJOR, regex=WEASEL),
    SlopPattern("slop/empty-phrase", Scope.SUMMARY,
                "Cut it and state the point.", Severity.MINOR, regex=EMPTY_PHRASE),
    SlopPattern("slop/binary-contrast", Scope.SUMMARY,
                "State the second half directly.", Severity.MAJOR, regex=BINARY_CONTRAST),
    SlopPattern("slop/negative-listing", Scope.SUMMARY,
                "Just say what it is.", Severity.MINOR, regex=NEGATIVE_LISTING),
    SlopPattern("slop/throat-clearing", Scope.SUMMARY,
                "Cut the opener and lead with the point.", Severity.MINOR,
                regex=THROAT_CLEARING),
    SlopPattern("slop/faux-insight", Scope.SUMMARY,
                "Cut the setup; let the claim stand alone.", Severity.MAJOR,
                regex=FAUX_INSIGHT),
    SlopPattern("slop/rhetorical-setup", Scope.SUMMARY,
                "Drop the setup and make the point.", Severity.MINOR, regex=RHETORICAL),
    SlopPattern("slop/metadiscourse", Scope.SUMMARY,
                "Delete the aside, or replace it with the supporting fact.",
                Severity.MINOR, regex=METADISCOURSE),
    SlopPattern("slop/colon-reveal", Scope.SUMMARY,
                "Rewrite as a plain sentence.", Severity.MINOR, regex=COLON_REVEAL),
    SlopPattern("slop/summary-recap", Scope.SUMMARY,
                "End on the last concrete point.", Severity.MINOR, regex=SUMMARY_RECAP),
    SlopPattern("slop/em-dash-cluster", Scope.DOCUMENT,
                "Use commas or periods; keep at most one em dash.", Severity.MINOR,
                detector=_em_dash_clusters),
    SlopPattern("slop/emoji-heading", Scope.DOCUMENT,
                "Remove the emoji; format should follow content.", Severity.MINOR,
                detector=_emoji_headings),
]

BY_ID = {p.id: p for p in PATTERNS}
PATTERN_IDS = sorted(BY_ID)
