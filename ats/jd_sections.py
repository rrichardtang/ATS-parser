"""Splits a pasted JD into rough requirement/nice-to-have/other spans.

A flat frequency count over the whole posting can't tell "must have Kubernetes"
from "nice to have Kubernetes" from "we offer great health insurance" (noise) --
and that distinction is exactly what should drive how a term gets weighted.

Three passes, in order, same graceful-degradation posture as the rest of this app:

1. Header detection -- same technique as ats/sections.py's resume segmentation,
   adapted for JD prose: short, title-cased lines matched against a curated
   vocabulary, everything after one classified as that bucket until the next
   header. This works whenever the posting's own structure survived copy-paste,
   which real postings from LinkedIn/Greenhouse/Lever often do (their headers are
   usually their own line even once bold formatting is stripped). Matching runs
   on a punctuation-normalized copy of the line, so a header only differs from
   the vocabulary by its apostrophe glyph still matches -- see _normalize.
2. Requirements rescue -- headers were found, but none of them was a requirements
   header, so the requirements list is sitting in `responsibilities` counting for
   nothing. Requirement-shaped lines are moved across. This is the guard for a
   posting whose requirements header isn't in the vocabulary yet: it fails
   quietly otherwise, since the posting still parses and still yields spans.
3. Sentence-level fallback, used only when NO header was found anywhere in the
   posting -- modal-verb patterns ("you will" vs. "you have / must have / N+
   years") classify individual sentences without needing a heading at all.

If none of them classifies anything, the whole text is treated as REQUIRED. That
matches today's flat behaviour (nothing is lost), rather than dropping to REQUIRED,
which would silently make an unclassifiable posting count for nothing.
"""
from __future__ import annotations

import re

REQUIRED = "required"
NICE = "nice_to_have"
RESPONSIBILITIES = "responsibilities"
OTHER = "other"

# Careers-site copy-paste carries typographic punctuation: LinkedIn, Greenhouse
# and Lever all render "What You'll Do" with U+2019, not an ASCII apostrophe. A
# vocabulary spelled with ' misses those lines entirely, and the corpus proves it
# isn't hypothetical -- it holds both "What We're Looking For" and "What We’re
# Looking For", the same header from two postings, one matching and one not.
# Matching runs on the normalized copy; bucket contents stay verbatim.
_PUNCTUATION = str.maketrans({
    # single quotes and the modifier apostrophe
    "‘": "'", "’": "'", "ʼ": "'",
    # double quotes, en/em dash, non-breaking space
    "“": '"', "”": '"', "–": "-", "—": "-", " ": " ",
})


def _normalize(text: str) -> str:
    return text.translate(_PUNCTUATION)


# Header vocabulary. Deliberately wide -- JD headers vary far more than resume
# headers do, since there's no professional-terseness convention holding them
# to a small set of synonyms the way "Experience"/"Work History" does.
_HEADERS: dict[str, list[str]] = {
    RESPONSIBILITIES: [
        "about the role", "about this role", "about the opportunity",
        "the opportunity", "the role", "what you'll do", "what you will do",
        "what you'll be doing", "responsibilities", "your role", "day to day",
        "day-to-day", "role overview", "role scope", "scope of the role",
    ],
    REQUIRED: [
        "what we're looking for", "what we are looking for", "who you are",
        "what you'll bring", "what you will bring", "your background",
        "requirements", "qualifications", "minimum qualifications",
        "basic qualifications", "must haves", "must-haves", "required skills",
        "skills & experience", "skills and experience", "about you",
        "what you need", "what you'll need", "what you will need",
    ],
    NICE: [
        "nice to have", "nice-to-have", "bonus points", "bonus",
        "preferred qualifications", "preferred", "extra credit", "a plus",
        # A stack listing is not a requirements list: the posting in this corpus
        # that has one prefaces it with "we don't hire to a narrow checklist".
        # The tools still matter, so nice-to-have (reduced weight) rather than
        # responsibilities (counts toward no skill at all) is the honest bucket.
        "technical environment", "core engineering stack", "tech stack",
        "our stack", "technologies we use",
    ],
    OTHER: [
        "benefits", "perks", "what we offer", "compensation", "about us",
        "about the company", "about the team", "equal opportunity",
        "how to apply", "diversity", "our values", "who we are",
    ],
}

# Header families whose tail varies too freely to enumerate as phrases. The
# conditional fit-statement ("You May Be a Good Fit If You Have", "You Might Be a
# Good Fit If You") is how frontier-lab postings introduce their requirements
# list instead of a noun heading -- two of the six postings in this corpus, and
# neither was matched by any phrase above.
_HEADER_FAMILIES: dict[str, list[str]] = {
    REQUIRED: [
        # The trailing clause runs free ("...If You Have", "...If You", "...If
        # You've"), so it is matched loosely; _MAX_HEADER_LEN is what keeps a
        # sentence of body prose from being read as a heading.
        r"you (?:may|might|could|would) be an? (?:good|great|strong|ideal) fit"
        r"(?: if you\b[a-z' ]*)?",
    ],
}

_HEADER_RE = {
    bucket: re.compile(
        r"^\s*(?:"
        + "|".join(
            [re.escape(p) for p in phrases]
            + _HEADER_FAMILIES.get(bucket, [])
        )
        + r")\s*:?\s*$",
        re.IGNORECASE,
    )
    for bucket, phrases in _HEADERS.items()
}
_MAX_HEADER_LEN = 60

# Sentence-level patterns: the fallback below when no header exists at all, and
# the rescue pass when headers exist but none of them was a requirements header.
_RESPONSIBILITY_SENTENCE = re.compile(r"\byou('| wi)ll\b|\byou will\b", re.IGNORECASE)
_REQUIREMENT_SENTENCE = re.compile(
    r"\byou (have|need|should have)\b|\bmust have\b|\bexperience (with|in)\b|"
    r"\bproficiency (with|in)\b|\b\d+\+?\s*years?\b|\brequired\b",
    re.IGNORECASE,
)


def _header_bucket(line: str) -> str | None:
    stripped = _normalize(line).strip()
    if not stripped or len(stripped) > _MAX_HEADER_LEN:
        return None
    for bucket, pattern in _HEADER_RE.items():
        if pattern.match(stripped):
            return bucket
    return None


def _rescue_requirements(buckets: dict[str, list[str]]) -> None:
    """Headers were found but none was a requirements header -- move
    requirement-shaped lines out of responsibilities, in place.

    A posting whose requirements heading isn't in the vocabulary drops that whole
    list into `responsibilities` (the pre-header default), where it counts toward
    no skill at all. That failure is invisible from the outside: the posting still
    parses and still returns four spans, one of them just silently empty. Lines
    move rather than copy, so no term is counted twice.
    """
    if "".join(buckets[REQUIRED]).strip():
        return
    kept: list[str] = []
    promoted: list[str] = []
    for line in buckets[RESPONSIBILITIES]:
        target = promoted if _REQUIREMENT_SENTENCE.search(_normalize(line)) else kept
        target.append(line)
    if promoted:
        buckets[RESPONSIBILITIES] = kept
        buckets[REQUIRED] = promoted


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
        _rescue_requirements(buckets)
        return {k: "\n".join(v) for k, v in buckets.items()}

    # No headers anywhere -- fall back to sentence-level classification.
    sentences = re.split(r"(?<=[.!?])\s+", raw_text)
    classified_any = False
    for sentence in sentences:
        probe = _normalize(sentence)
        if _REQUIREMENT_SENTENCE.search(probe):
            buckets[REQUIRED].append(sentence)
            classified_any = True
        elif _RESPONSIBILITY_SENTENCE.search(probe):
            buckets[RESPONSIBILITIES].append(sentence)
            classified_any = True

    if classified_any:
        return {k: "\n".join(v) for k, v in buckets.items()}

    # Nothing classified at all -- treat the whole posting as required, matching
    # today's flat (undifferentiated) behaviour rather than silently zeroing it.
    return {REQUIRED: raw_text, NICE: "", RESPONSIBILITIES: "", OTHER: ""}
