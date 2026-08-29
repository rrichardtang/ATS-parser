"""The four properties a strong bullet has, checked independently.

Deliberately not the XYZ template. Checking "accomplished X as measured by Y by
doing Z" as a *shape* would reward monotony -- which is itself an LLM tell -- and
would pass a bullet that has perfect form and no substance. These four properties
are what XYZ is a delivery vehicle for, so a bullet satisfying them reads as strong
in any construction.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# A metric is a number attached to something that varies: a rate, a duration, a
# volume, a currency, a delta. A count of people or tools is not a metric -- see
# vacuous_number(), which exists because "collaborated with 3 engineers" would
# otherwise satisfy Measurability while carrying nothing.
UNIT_RE = re.compile(
    r"""(?ix)
    \b(
      \d+(?:\.\d+)?[\s-]*(?:%|percent|pts?|points?|x\b|bps)
    | \$\s?\d[\d,.]*\s*(?:k|m|bn|b|million|billion)?
    | \d+(?:\.\d+)?\s*(?:ms|s|sec|secs|seconds|min|mins|minutes|hrs?|hours|days?|weeks?|months?)
    | \d+(?:\.\d+)?\s*(?:k|m|bn|b)?\s*(?:req|requests|qps|rps|tps|queries|tokens|rows|records|users|customers|tickets|events|images|docs|documents|samples|examples|pairs|params|parameters|gb|tb|mb)
    | p\d{2}\b
    | \d+(?:\.\d+)?\s*(?:gpus?|nodes?|replicas?|shards?)
    )
    """,
)

BARE_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b")

# Counting colleagues, meetings or tools is the classic way to satisfy a
# quantification check without saying anything.
# Allows an adjective between the number and the noun -- "5 different tools" counts
# trivia exactly as much as "5 tools" does.
VACUOUS_CONTEXT_RE = re.compile(
    r"(?i)\b\d+\s*\+?\s*(?:\w+\s+){0,2}?(engineers?|people|teams?|members?|"
    r"colleagues?|developers?|stakeholders?|meetings?|sprints?|tools?|technologies|"
    r"frameworks?|languages?|libraries|projects?|clients?)\b"
)

OUTCOME_VERBS = {
    "cut", "reduced", "increased", "raised", "improved", "grew", "shipped", "launched",
    "delivered", "eliminated", "removed", "accelerated", "doubled", "tripled", "halved",
    "saved", "boosted", "lowered", "scaled", "migrated", "automated", "unblocked",
    "recovered", "restored", "decreased", "drove", "landed", "achieved", "enabled",
}

ACTIVITY_VERBS = {
    "worked", "helped", "assisted", "participated", "contributed", "supported",
    "responsible", "involved", "collaborated", "attended", "learned", "used",
    "utilized", "leveraged", "handled", "managed", "maintained", "developed",
    "built", "created", "designed", "implemented", "wrote", "researched",
}

# Naming the thing is what makes a claim checkable. Generic gestures are not.
SPECIFIC_TOKEN_RE = re.compile(
    r"""(?x)
    \b(
      [A-Z][a-zA-Z]*(?:-[A-Za-z0-9.]+)+          # Llama-3-8B, GPT-4o-mini
    | [A-Z][a-z]+[A-Z][A-Za-z]*                  # PyTorch, TensorFlow, BigQuery
    | [A-Z]{2,8}                                 # AUC, RAG, ETL, GPU, BLEU
    | [a-z]+\.(?:py|js|ts|go|rs|sql)
    | vLLM|k8s
    )\b
    """
)

# A capitalised word mid-sentence is a name -- Airflow, Mistral, Kubernetes. Bullets
# open with a capital, so position matters: only tokens after the first count.
MIDSENTENCE_PROPER_RE = re.compile(r"(?<=[a-z,)\s])\b([A-Z][a-z]{2,})\b")

# Words that start a clause rather than name a thing.
_NOT_NAMES = {
    "The", "This", "That", "These", "Those", "Their", "There", "When", "While",
    "With", "From", "For", "And", "But", "Our", "After", "Before", "Using",
}

GENERIC_MECHANISM_RE = re.compile(
    r"(?i)\b(various|multiple|several|numerous|different|cutting-edge|state-of-the-art|"
    r"industry-standard|best practices|modern|advanced|innovative|robust|scalable)\b"
)

TEAM_SUBJECT_RE = re.compile(r"(?i)^\s*(we|our team|the team|our group|us)\b")
TEAM_ANYWHERE_RE = re.compile(r"(?i)\b(we|our team|the team)\b")
FIRST_PERSON_RE = re.compile(r"(?i)\b(i|my|me|mine)\b")


@dataclass
class InvariantResult:
    outcome: bool
    measurability: bool
    mechanism: bool
    ownership: bool

    @property
    def failures(self) -> list[str]:
        names = []
        if not self.outcome:
            names.append("outcome")
        if not self.measurability:
            names.append("measurability")
        if not self.mechanism:
            names.append("mechanism")
        if not self.ownership:
            names.append("ownership")
        return names

    @property
    def passed(self) -> int:
        return 4 - len(self.failures)


def has_metric(text: str) -> bool:
    """A number that measures something, as opposed to a number that counts trivia."""
    if UNIT_RE.search(text):
        return True
    for match in BARE_NUMBER_RE.finditer(text):
        window = text[max(0, match.start() - 30) : match.end() + 30]
        if VACUOUS_CONTEXT_RE.search(window):
            continue
        # A bare number next to a comparison word still measures something. Word
        # boundaries matter here: "to" is a substring of "tools".
        if re.search(r"(?i)\b(from|to|by|under|over|within|below|above)\b", window):
            return True
    return False


def vacuous_number(text: str) -> str | None:
    """Returns the offending span when a bullet's only number counts trivia.

    This is an audit signal, not a ranking signal: it exists to catch a rewrite that
    games Measurability rather than to grade a human's writing.
    """
    if UNIT_RE.search(text):
        return None
    m = VACUOUS_CONTEXT_RE.search(text)
    return m.group(0) if m else None


def _first_verb(text: str) -> str:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return words[0] if words else ""


def evaluate(text: str) -> InvariantResult:
    lowered = text.lower()
    first = _first_verb(text)

    measurability = has_metric(text)

    outcome = (
        first in OUTCOME_VERBS
        or any(f" {v} " in f" {lowered} " for v in OUTCOME_VERBS)
        or bool(re.search(r"(?i)\b(from|to)\b.*\b(to|from)\b", text)) and measurability
    )
    if first in ACTIVITY_VERBS and not measurability:
        outcome = False

    named = {m for m in SPECIFIC_TOKEN_RE.findall(text)}
    body = text[1:] if text else ""
    named |= {
        m for m in MIDSENTENCE_PROPER_RE.findall(body) if m not in _NOT_NAMES
    }
    specifics = len(named)
    mechanism = specifics >= 1 and not (
        GENERIC_MECHANISM_RE.search(text) and specifics < 2
    )

    ownership = not TEAM_SUBJECT_RE.match(text)
    if TEAM_ANYWHERE_RE.search(text) and not re.match(r"(?i)^\s*[a-z]+ed\b", text):
        ownership = ownership and bool(re.match(r"(?i)^\s*[A-Za-z]+ed\b", text))

    return InvariantResult(outcome, measurability, mechanism, ownership)


def portability(text: str) -> float:
    """Fraction of a bullet that survives stripping every specific.

    The no-ai-slop portability test: if a sentence could move unchanged to another
    person, company or product, it is filler. Strip the proper nouns, numbers and
    tool names; whatever is left is the generic scaffolding. A bullet that survives
    almost intact said nothing specific to begin with.
    """
    stripped = SPECIFIC_TOKEN_RE.sub("", text)
    stripped = UNIT_RE.sub("", stripped)
    stripped = BARE_NUMBER_RE.sub("", stripped)
    stripped = re.sub(r"\b[A-Z][a-zA-Z]+\b", "", stripped)
    words_before = len(re.findall(r"\w+", text)) or 1
    words_after = len(re.findall(r"\w+", stripped))
    return words_after / words_before
