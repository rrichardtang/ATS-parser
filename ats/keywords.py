"""Taxonomy coverage and JD gap analysis.

Weights come from corpus-measured document frequency (see scripts/build_taxonomy.py),
not from intuition. Coverage is only half the check: stuffing is penalised, because
semantic matchers score keywords in context and mark down repetition.
"""
from __future__ import annotations

import functools
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .models import Category, Finding, Provenance, Severity
from .sections import Resume

TAXONOMY_PATH = Path(__file__).with_name("taxonomy.json")

# A term repeated far above its natural rate reads as stuffing to a semantic matcher.
STUFFING_REPEAT_LIMIT = 6
# A skills line this long with no supporting evidence is a dump, not a profile.
SKILLS_DUMP_TERMS = 25
# Terms this important that are missing get named individually.
IMPORTANT_WEIGHT = 0.35

SOFT_SKILLS = re.compile(
    r"(?i)\b(team ?player|hard[- ]working|detail[- ]oriented|self[- ]starter|"
    r"go[- ]getter|passionate|motivated|excellent communication|problem[- ]solving|"
    r"leadership|teamwork|communication|time management|adaptable|synergy)\b"
)


@dataclass
class Coverage:
    matched: dict[str, float] = field(default_factory=dict)
    missing: dict[str, float] = field(default_factory=dict)
    by_group: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def score(self) -> float:
        total = sum(self.matched.values()) + sum(self.missing.values())
        return sum(self.matched.values()) / total if total else 1.0


@functools.lru_cache(maxsize=1)
def taxonomy() -> dict:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


def _mentions(text: str, aliases: list[str]) -> int:
    return sum(len(re.findall(rf"(?<!\w){re.escape(a)}(?!\w)", text)) for a in aliases)


def coverage(text: str) -> Coverage:
    lowered = text.lower()
    result = Coverage()
    group_totals: dict[str, list[int]] = {}
    for key, entry in taxonomy()["terms"].items():
        if entry["weight"] <= 0:
            continue
        hit = _mentions(lowered, entry["aliases"]) > 0
        (result.matched if hit else result.missing)[key] = entry["weight"]
        counts = group_totals.setdefault(entry["group"], [0, 0])
        counts[1] += 1
        if hit:
            counts[0] += 1
    result.by_group = {g: (m, t) for g, (m, t) in group_totals.items()}
    return result


def analyze(resume: Resume, full_text: str, jd_text: str = "") -> list[Finding]:
    out: list[Finding] = []
    cov = coverage(full_text)

    for group, (matched, total) in sorted(cov.by_group.items()):
        if total and matched / total < 0.34:
            gaps = sorted(
                (k for k in cov.missing if k.startswith(f"{group}/")),
                key=lambda k: -cov.missing[k],
            )[:4]
            names = ", ".join(k.split("/", 1)[1] for k in gaps)
            out.append(Finding(
                rule_id=f"kw/thin-{group.replace('_', '-')}",
                category=Category.RELEVANCE,
                severity=Severity.MAJOR if group in {"evaluation", "llm_systems"} else Severity.MINOR,
                message=f"Thin coverage of {group.replace('_', ' ')} "
                        f"({matched} of {total} terms)",
                fix=f"If you have done this work, name it: {names}.",
                evidence=f"missing: {names}",
                locator="skills",
                provenance=Provenance.JD_DERIVED,
            ))

    out.extend(_stuffing(resume, full_text))
    out.extend(_unsupported_skills(resume))
    if jd_text.strip():
        out.extend(_jd_gap(full_text, jd_text))
    return out


def _stuffing(resume: Resume, full_text: str) -> list[Finding]:
    out: list[Finding] = []
    lowered = full_text.lower()

    for key, entry in taxonomy()["terms"].items():
        count = _mentions(lowered, entry["aliases"])
        if count > STUFFING_REPEAT_LIMIT:
            out.append(Finding(
                rule_id="kw/over-repetition",
                category=Category.RELEVANCE,
                severity=Severity.MINOR,
                message=f"“{entry['term']}” appears {count} times",
                fix="Say it once where it is load-bearing. Semantic matchers mark "
                    "down repetition rather than rewarding it.",
                evidence=f"{entry['term']} x{count}",
                locator="document",
                provenance=Provenance.RECRUITER_EVIDENCE,
            ))

    skills = resume.skills_text
    if skills:
        terms = [t.strip() for t in re.split(r"[,;|/]", skills) if t.strip()]
        if len(terms) > SKILLS_DUMP_TERMS:
            out.append(Finding(
                rule_id="kw/skills-dump",
                category=Category.RELEVANCE,
                severity=Severity.MINOR,
                message=f"Skills section lists {len(terms)} items with no grouping",
                fix="Group by area and cut anything you would not want interviewed.",
                evidence=skills[:110],
                locator="skills",
                provenance=Provenance.RECRUITER_EVIDENCE,
            ))
        if soft := SOFT_SKILLS.findall(skills):
            out.append(Finding(
                rule_id="kw/soft-skill-padding",
                category=Category.RELEVANCE,
                severity=Severity.MINOR,
                message=f"Soft skills in a technical skills list: {', '.join(sorted(set(soft))[:4])}",
                fix="Cut them. They are unverifiable and they dilute the technical signal.",
                evidence=", ".join(sorted(set(soft))[:6]),
                locator="skills",
                provenance=Provenance.RECRUITER_EVIDENCE,
            ))
    return out


def _unsupported_skills(resume: Resume) -> list[Finding]:
    """A skill claimed in Skills but absent from Experience is an unbacked claim."""
    if not resume.skills_text:
        return []
    evidence_blob = " ".join(
        [b for _, b in resume.bullets]
        + resume.sections.get("projects", [])
        + [resume.summary]
    ).lower()
    claimed = [
        t.strip() for t in re.split(r"[,;|]", resume.skills_text)
        if 2 < len(t.strip()) < 28
    ]
    unsupported = [
        t for t in claimed
        if not re.search(rf"(?<!\w){re.escape(t.lower())}(?!\w)", evidence_blob)
        and not SOFT_SKILLS.search(t)
    ]
    if len(unsupported) < 4:
        return []
    return [Finding(
        rule_id="kw/unsupported-skills",
        category=Category.CREDIBILITY,
        severity=Severity.MINOR,
        message=f"{len(unsupported)} skills appear only in the Skills list, "
                "with nothing in Experience or Projects behind them",
        fix="Show one of each in a bullet, or drop it. Interviewers probe this list.",
        evidence=", ".join(unsupported[:8]),
        locator="skills",
        provenance=Provenance.RECRUITER_EVIDENCE,
    )]


JD_TERM_RE = re.compile(r"(?<!\w)([A-Za-z][\w.+#-]{2,})(?!\w)")
JD_STOPWORDS = {
    "the", "and", "for", "with", "you", "our", "will", "are", "have", "this", "that",
    "your", "work", "team", "role", "experience", "years", "requirements", "nice",
    "should", "able", "strong", "using", "used", "them", "from", "into", "across",
    "such", "like", "including", "well", "more", "than", "who", "can", "not", "but",
    "job", "candidate", "candidates", "responsibilities", "qualifications", "plus",
    "about", "what", "how", "why", "their", "they", "when", "where", "some", "any",
}


def _jd_gap(resume_text: str, jd_text: str) -> list[Finding]:
    """Diff the pasted JD's requirement terms against the resume."""
    resume_lower = resume_text.lower()
    jd_lower = jd_text.lower()

    taxo_missing = [
        (key, entry) for key, entry in taxonomy()["terms"].items()
        if _mentions(jd_lower, entry["aliases"]) and not _mentions(resume_lower, entry["aliases"])
    ]

    counts: dict[str, int] = {}
    for match in JD_TERM_RE.finditer(jd_text):
        token = match.group(1)
        low = token.lower()
        if low in JD_STOPWORDS or len(low) < 3:
            continue
        if token[0].isupper() or any(c.isdigit() for c in token) or "." in token:
            counts[low] = counts.get(low, 0) + 1
    proper_missing = sorted(
        (t for t, c in counts.items() if c >= 2 and not re.search(rf"(?<!\w){re.escape(t)}(?!\w)", resume_lower)),
        key=lambda t: -counts[t],
    )[:10]

    out: list[Finding] = []
    if taxo_missing:
        important = [k for k, e in taxo_missing if e["weight"] >= IMPORTANT_WEIGHT]
        rest = [k for k, e in taxo_missing if e["weight"] < IMPORTANT_WEIGHT]
        if important:
            names = ", ".join(k.split("/", 1)[1] for k in important[:6])
            out.append(Finding(
                rule_id="jd/missing-core",
                category=Category.RELEVANCE,
                severity=Severity.MAJOR,
                message=f"The job asks for {len(important)} core things your resume never mentions",
                fix=f"Address these if you have them: {names}.",
                evidence=names,
                locator="document",
                provenance=Provenance.JD_DERIVED,
            ))
        if rest:
            names = ", ".join(k.split("/", 1)[1] for k in rest[:6])
            out.append(Finding(
                rule_id="jd/missing-secondary",
                category=Category.RELEVANCE,
                severity=Severity.MINOR,
                message=f"Secondary requirements not mentioned: {names}",
                fix="Add where true; do not pad.",
                evidence=names,
                locator="document",
                provenance=Provenance.JD_DERIVED,
            ))
    if proper_missing:
        out.append(Finding(
            rule_id="jd/missing-named-tools",
            category=Category.RELEVANCE,
            severity=Severity.MINOR,
            message="Tools named repeatedly in the job post and absent here: "
                    + ", ".join(proper_missing[:6]),
            fix="Name the ones you have used. Recruiters search on exactly these.",
            evidence=", ".join(proper_missing[:8]),
            locator="skills",
            provenance=Provenance.JD_DERIVED,
        ))
    return out
