"""Splits a pasted JD into rough requirement/nice-to-have/other spans.

A flat frequency count over the whole posting can't tell "must have Kubernetes"
from "nice to have Kubernetes" from "we offer great health insurance" (noise) --
and that distinction is exactly what should drive how a term gets weighted.

Two passes, in order, same graceful-degradation posture as the rest of this app:

1. Header detection -- same technique as ats/sections.py's resume segmentation,
   adapted for JD prose: short, title-cased lines matched against a curated
   vocabulary, everything after one classified as that bucket until the next
   header. This works whenever the posting's own structure survived copy-paste,
   which real postings from LinkedIn/Greenhouse/Lever often do (their headers are
   usually their own line even once bold formatting is stripped).
2. Sentence-level fallback, used only when NO header was found anywhere in the
   posting -- modal-verb patterns ("you will" vs. "you have / must have / N+
   years") classify individual sentences without needing a heading at all.

If neither pass classifies anything, the whole text is treated as REQUIRED. That
matches today's flat behaviour (nothing is lost), rather than dropping to REQUIRED,
which would silently make an unclassifiable posting count for nothing.
"""
from __future__ import annotations

import re

REQUIRED = "required"
NICE = "nice_to_have"
RESPONSIBILITIES = "responsibilities"
OTHER = "other"

# Header vocabulary. Deliberately wide -- JD headers vary far more than resume
# headers do, since there's no professional-terseness convention holding them
# to a small set of synonyms the way "Experience"/"Work History" does.
_HEADERS: dict[str, list[str]] = {
    RESPONSIBILITIES: [
        "about the role", "about this role", "about the opportunity",
        "the opportunity", "the role", "what you'll do", "what you will do",
        "what you'll be doing", "responsibilities", "your role", "day to day",
        "day-to-day", "role overview",
    ],
    REQUIRED: [
        "what we're looking for", "what we are looking for", "who you are",
        "what you'll bring", "what you will bring", "your background",
        "requirements", "qualifications", "minimum qualifications",
        "basic qualifications", "must haves", "must-haves", "required skills",
        "skills & experience", "skills and experience", "about you",
    ],
    NICE: [
        "nice to have", "nice-to-have", "bonus points", "bonus",
        "preferred qualifications", "preferred", "extra credit", "a plus",
    ],
    OTHER: [
        "benefits", "perks", "what we offer", "compensation", "about us",
        "about the company", "about the team", "equal opportunity",
        "how to apply", "diversity", "our values", "who we are",
    ],
}
_HEADER_RE = {
    bucket: re.compile(
        r"^\s*(?:" + "|".join(re.escape(p) for p in phrases) + r")\s*:?\s*$",
        re.IGNORECASE,
    )
    for bucket, phrases in _HEADERS.items()
}
_MAX_HEADER_LEN = 60

# Sentence-level fallback, used only when no header was found anywhere.
_RESPONSIBILITY_SENTENCE = re.compile(r"\byou('| wi)ll\b|\byou will\b", re.IGNORECASE)
_REQUIREMENT_SENTENCE = re.compile(
    r"\byou (have|need|should have)\b|\bmust have\b|\bexperience (with|in)\b|"
    r"\bproficiency (with|in)\b|\b\d+\+?\s*years?\b|\brequired\b",
    re.IGNORECASE,
)


def _header_bucket(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or len(stripped) > _MAX_HEADER_LEN:
        return None
    for bucket, pattern in _HEADER_RE.items():
        if pattern.match(stripped):
            return bucket
    return None


def classify(raw_text: str) -> dict[str, str]:
    """Returns {required, nice_to_have, responsibilities, other}, each the
    concatenated text assigned to that bucket. Buckets not present are empty."""
    lines = raw_text.splitlines()
    buckets: dict[str, list[str]] = {REQUIRED: [], NICE: [], RESPONSIBILITIES: [], OTHER: []}

    # Content before the first recognized header defaults to responsibilities, not
    # dropped -- an unlabeled opening paragraph ("We're looking for an engineer to
    # own production systems end-to-end...") is exactly where scope/ownership
    # language tends to live, and dropping it would silently lose that signal.
    # Skill-term matching stays safe either way: only required/nice count toward
    # coverage, so a company blurb landing in responsibilities can't inflate it.
    current: str = RESPONSIBILITIES
    any_header = False
    for line in lines:
        bucket = _header_bucket(line)
        if bucket:
            current = bucket
            any_header = True
            continue
        buckets[current].append(line)

    if any_header:
        return {k: "\n".join(v) for k, v in buckets.items()}

    # No headers anywhere -- fall back to sentence-level classification.
    sentences = re.split(r"(?<=[.!?])\s+", raw_text)
    classified_any = False
    for sentence in sentences:
        if _REQUIREMENT_SENTENCE.search(sentence):
            buckets[REQUIRED].append(sentence)
            classified_any = True
        elif _RESPONSIBILITY_SENTENCE.search(sentence):
            buckets[RESPONSIBILITIES].append(sentence)
            classified_any = True

    if classified_any:
        return {k: "\n".join(v) for k, v in buckets.items()}

    # Nothing classified at all -- treat the whole posting as required, matching
    # today's flat (undifferentiated) behaviour rather than silently zeroing it.
    return {REQUIRED: raw_text, NICE: "", RESPONSIBILITIES: "", OTHER: ""}
