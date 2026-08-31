"""Deterministic checks over the parsed resume.

Every rule declares a provenance, because the way this product fails is by having
a rubric nobody can argue with. `heuristic` rules -- ones resting on author
judgment rather than measurable evidence -- are capped at minor severity in
config.apply_provenance_cap and can never sink a score.
"""
from __future__ import annotations

import re
from datetime import date

from . import config
from .extract import ExtractedDoc, font_sprawl
from .invariants import evaluate
from .models import Category, Finding, Provenance, Severity
from .sections import BULLET_RE, Resume

REQUIRED_SECTIONS = {"experience", "skills", "education"}
MAX_PAGES_MID_LEVEL = 2
MIN_BULLETS_PER_ROLE = 2
MAX_BULLETS_PER_ROLE = 8
MAX_BULLET_WORDS = 30
QUANTIFICATION_TARGET = 0.50
GAP_MONTHS = 6

WEAK_OPENERS = re.compile(
    r"(?i)^\s*(responsible for|worked on|helped (?:to|with)?|assisted (?:with|in)?|"
    r"participated in|involved in|tasked with|duties includ|contributed to)\b"
)
PASSIVE_RE = re.compile(r"(?i)\b(was|were|been|being)\s+\w+(?:ed|en)\b")
FIRST_PERSON_RE = re.compile(r"(?i)(?:^|\s)(I|my|me)\b")
TEAM_SUBJECT_RE = re.compile(r"(?i)^\s*(we|our team|the team)\b")

SENIORITY_JUNIOR = re.compile(r"(?i)\b(junior|jr\.?|associate|intern|trainee|entry[- ]level)\b")
AI_TITLE_RE = re.compile(
    r"(?i)\b(ai|ml|machine learning|deep learning|research|data scien|mlops|nlp|"
    r"applied scien|llm)\b"
)


def _finding(
    rule_id: str,
    category: Category,
    severity: Severity,
    message: str,
    fix: str,
    provenance: Provenance,
    evidence: str = "",
    locator: str = "",
) -> Finding:
    return Finding(
        rule_id=rule_id,
        category=category,
        severity=config.apply_provenance_cap(severity, provenance),
        message=message,
        fix=fix,
        evidence=evidence,
        locator=locator,
        provenance=provenance,
    )


def parseability(doc: ExtractedDoc) -> list[Finding]:
    out: list[Finding] = []

    if doc.hidden_text:
        sample = doc.hidden_text[0][:90]
        out.append(_finding(
            "parse/hidden-text", Category.PARSEABILITY, Severity.CRITICAL,
            "This PDF contains text invisible to a reader but readable by a parser",
            "Delete it. Workday, Greenhouse and Lever detect hidden text and can "
            "attach a fraud flag to your candidate record.",
            Provenance.PARSER_MECHANICS, evidence=sample, locator="document",
        ))

    if not doc.has_text_layer:
        out.append(_finding(
            "parse/no-text-layer", Category.PARSEABILITY, Severity.CRITICAL,
            "This PDF has no text layer -- it is a scan, or the text is outlined",
            "Export from the source document instead of scanning or flattening.",
            Provenance.PARSER_MECHANICS, evidence="0 characters extracted",
            locator="document",
        ))
        return out

    if doc.multi_column_pages:
        pages = ", ".join(str(p + 1) for p in doc.multi_column_pages)
        out.append(_finding(
            "parse/multi-column", Category.PARSEABILITY, Severity.MAJOR,
            f"Multi-column layout on page {pages}",
            "Use a single column. Parsers linearise columns left-to-right and "
            "interleave your sections.",
            Provenance.PARSER_MECHANICS, evidence=f"page {pages}", locator="document",
        ))

    if doc.table_pages:
        out.append(_finding(
            "parse/tables", Category.PARSEABILITY, Severity.MAJOR,
            f"Table layout on page {doc.table_pages[0] + 1}",
            "Replace tables with plain paragraphs and bullets.",
            Provenance.PARSER_MECHANICS, evidence=f"page {doc.table_pages[0] + 1}",
            locator="document",
        ))

    if doc.edge_band_text:
        sample = " ".join(doc.edge_band_text[:8])[:80]
        out.append(_finding(
            "parse/edge-band", Category.PARSEABILITY, Severity.MINOR,
            "Content sits in the header/footer band",
            "Move it into the body -- some parsers drop page furniture.",
            Provenance.PARSER_MECHANICS, evidence=sample, locator="document",
        ))

    if doc.page_count > MAX_PAGES_MID_LEVEL:
        out.append(_finding(
            "parse/page-count", Category.STRUCTURE, Severity.MINOR,
            f"{doc.page_count} pages",
            f"Cut to {MAX_PAGES_MID_LEVEL}. At mid-level the third page is not read.",
            Provenance.HEURISTIC, evidence=f"{doc.page_count} pages", locator="document",
        ))

    if doc.exotic_bullets:
        glyphs = " ".join(sorted(doc.exotic_bullets))[:20]
        out.append(_finding(
            "parse/exotic-bullets", Category.PARSEABILITY, Severity.MINOR,
            f"Non-standard bullet glyphs: {glyphs}",
            "Use a plain round bullet; unusual glyphs can extract as junk.",
            Provenance.PARSER_MECHANICS, evidence=glyphs, locator="document",
        ))

    sprawl = font_sprawl(doc)
    if sprawl > 3:
        out.append(_finding(
            "parse/font-sprawl", Category.STRUCTURE, Severity.MINOR,
            f"{sprawl} font families",
            "Use at most two.",
            Provenance.HEURISTIC, evidence=f"{sprawl} families", locator="document",
        ))
    return out


def structure(resume: Resume) -> list[Finding]:
    out: list[Finding] = []
    present = set(resume.section_order)
    for missing in sorted(REQUIRED_SECTIONS - present):
        out.append(_finding(
            f"struct/missing-{missing}", Category.STRUCTURE, Severity.MAJOR,
            f"No {missing} section found",
            f"Add a clearly labelled {missing.title()} heading.",
            Provenance.PARSER_MECHANICS, evidence=f"sections: {', '.join(resume.section_order) or 'none'}",
            locator="document",
        ))

    for index, role in enumerate(resume.roles):
        locator = f"exp[{index}]"
        if role.start is None:
            out.append(_finding(
                "struct/missing-dates", Category.STRUCTURE, Severity.MAJOR,
                f"No dates on “{role.heading[:50]}”",
                "Add a month and year range.",
                Provenance.PARSER_MECHANICS, evidence=role.heading[:80], locator=locator,
            ))
        count = len(role.bullets)
        if count and count < MIN_BULLETS_PER_ROLE:
            out.append(_finding(
                "struct/thin-role", Category.STRUCTURE, Severity.MINOR,
                f"“{role.title or role.heading[:40]}” has {count} bullet",
                f"Give each role at least {MIN_BULLETS_PER_ROLE} bullets, or fold it in.",
                Provenance.HEURISTIC, evidence=role.heading[:80], locator=locator,
            ))
        if count > MAX_BULLETS_PER_ROLE:
            out.append(_finding(
                "struct/bloated-role", Category.STRUCTURE, Severity.MINOR,
                f"“{role.title or role.heading[:40]}” has {count} bullets",
                f"Keep the strongest {MAX_BULLETS_PER_ROLE}.",
                Provenance.HEURISTIC, evidence=role.heading[:80], locator=locator,
            ))

    dated = [r for r in resume.roles if r.start]
    for previous, following in zip(dated, dated[1:]):
        if previous.start and following.start and following.start > previous.start:
            out.append(_finding(
                "struct/not-reverse-chron", Category.STRUCTURE, Severity.MINOR,
                "Roles are not in reverse-chronological order",
                "Put the most recent role first.",
                Provenance.PARSER_MECHANICS,
                evidence=f"{previous.heading[:40]} before {following.heading[:40]}",
                locator="experience",
            ))
            break

    for start, end in resume.gaps(GAP_MONTHS):
        months = (end.year - start.year) * 12 + end.month - start.month
        out.append(_finding(
            "struct/employment-gap", Category.STRUCTURE, Severity.MINOR,
            f"{months}-month gap ({start:%b %Y} to {end:%b %Y})",
            "Add a line naming what you did -- contract work, study, caregiving.",
            Provenance.RECRUITER_EVIDENCE, evidence=f"{start:%b %Y}-{end:%b %Y}",
            locator="experience",
        ))
    return out


def contact(resume: Resume) -> list[Finding]:
    """Missing contact fields are real findings and cheap fixes.

    Deliberately MINOR. A public checker scoring 22/100 for a missing phone number
    is measuring one field and reporting it as a verdict; see the anti-hard-gate
    invariant in score.py.
    """
    out: list[Finding] = []
    c = resume.contact
    for field_name, value, fix in [
        ("email", c.email, "Add a professional email address."),
        ("phone", c.phone, "Add a phone number -- recruiters do call."),
        ("linkedin", c.linkedin, "Add your LinkedIn URL."),
    ]:
        if not value:
            out.append(_finding(
                f"contact/no-{field_name}", Category.STRUCTURE, Severity.MINOR,
                f"No {field_name} in the header",
                fix, Provenance.RECRUITER_EVIDENCE, evidence="header", locator="header",
            ))
    if not c.github:
        out.append(_finding(
            "contact/no-github", Category.STRUCTURE, Severity.MINOR,
            "No GitHub link",
            "Add one. For AI engineering it is the cheapest evidence you can offer.",
            Provenance.JD_DERIVED, evidence="header", locator="header",
        ))
    return out


def title_alignment(resume: Resume, target_title: str = "AI Engineer") -> list[Finding]:
    """Workday weights title match, including seniority mapping, heavily."""
    out: list[Finding] = []
    recent = resume.roles[0] if resume.roles else None
    if not recent:
        return out
    title = recent.title or recent.heading
    if not AI_TITLE_RE.search(title):
        out.append(_finding(
            "title/off-domain", Category.TITLE, Severity.MAJOR,
            f"Most recent title “{title[:50]}” does not read as AI/ML work",
            f"If the work was AI/ML, clarify accurately: “{title[:32]} (ML Platform)”. "
            "Do not invent a title you did not hold.",
            Provenance.RECRUITER_EVIDENCE, evidence=title[:80], locator="exp[0]",
        ))
    if SENIORITY_JUNIOR.search(title) and resume.years_experience >= 2.5:
        out.append(_finding(
            "title/seniority-mismatch", Category.TITLE, Severity.MINOR,
            f"Current title reads junior against {resume.years_experience:.0f} years of experience",
            "If your scope outgrew the title, say so in the bullets rather than the title.",
            Provenance.RECRUITER_EVIDENCE, evidence=title[:80], locator="exp[0]",
        ))
    return out


def content_mechanics(resume: Resume) -> list[Finding]:
    out: list[Finding] = []
    bullets = resume.bullets
    if not bullets:
        return out

    quantified = 0
    for locator, bullet in bullets:
        result = evaluate(bullet)
        if result.measurability:
            quantified += 1
        if len(result.failures) >= 2:
            out.append(_finding(
                "content/bullet-invariants", Category.RESUME_CRAFT, Severity.MAJOR,
                f"Missing {' and '.join(result.failures)}",
                _invariant_fix(result.failures),
                Provenance.RECRUITER_EVIDENCE, evidence=bullet[:120], locator=locator,
            ))
        if WEAK_OPENERS.match(bullet):
            out.append(_finding(
                "content/weak-opener", Category.RESUME_CRAFT, Severity.MINOR,
                f"Opens with “{bullet.split(',')[0][:40]}”",
                "Start with what you did and what changed.",
                Provenance.RECRUITER_EVIDENCE, evidence=bullet[:80], locator=locator,
            ))
        if PASSIVE_RE.search(bullet):
            out.append(_finding(
                "content/passive-voice", Category.RESUME_CRAFT, Severity.MINOR,
                "Passive construction hides who did the work",
                "Use an active verb with you as the subject.",
                Provenance.HEURISTIC, evidence=PASSIVE_RE.search(bullet).group(0),
                locator=locator,
            ))
        if TEAM_SUBJECT_RE.match(bullet):
            out.append(_finding(
                "content/ownership", Category.PRODUCTION_OWNERSHIP, Severity.MAJOR,
                "Bullet's subject is the team, not you",
                "Say what you did. A hiring manager is deciding about you.",
                Provenance.RECRUITER_EVIDENCE, evidence=bullet[:80], locator=locator,
            ))
        if FIRST_PERSON_RE.search(bullet):
            out.append(_finding(
                "content/first-person", Category.RESUME_CRAFT, Severity.MINOR,
                "First-person pronoun in a bullet",
                "Drop it -- resume bullets are implicitly first person.",
                Provenance.HEURISTIC, evidence=bullet[:80], locator=locator,
            ))
        if len(bullet.split()) > MAX_BULLET_WORDS:
            out.append(_finding(
                "content/long-bullet", Category.RESUME_CRAFT, Severity.MINOR,
                f"{len(bullet.split())}-word bullet",
                f"Cut to under {MAX_BULLET_WORDS} words, or split it.",
                Provenance.HEURISTIC, evidence=bullet[:100], locator=locator,
            ))

    rate = quantified / len(bullets)
    if rate < QUANTIFICATION_TARGET:
        out.append(_finding(
            "content/quantification", Category.RESUME_CRAFT, Severity.MAJOR,
            f"{rate:.0%} of bullets carry a measurable result "
            f"({quantified} of {len(bullets)})",
            f"Get to {QUANTIFICATION_TARGET:.0%}. Latency, throughput, accuracy, "
            "dataset size, cost -- whatever you actually moved.",
            Provenance.JD_DERIVED, evidence=f"{quantified}/{len(bullets)} bullets",
            locator="experience",
        ))

    out.extend(_duplicate_bullets(bullets))
    return out


def _invariant_fix(failures: list[str]) -> str:
    parts = {
        "outcome": "state what changed, not what you were assigned",
        "measurability": "add the number that moved",
        "mechanism": "name the model, tool or technique",
        "ownership": "make clear what you did",
    }
    return "; ".join(parts[f] for f in failures).capitalize() + "."


def _duplicate_bullets(bullets: list[tuple[str, str]]) -> list[Finding]:
    out: list[Finding] = []
    seen: list[tuple[str, set[str]]] = []
    for locator, text in bullets:
        tokens = {w.lower() for w in re.findall(r"\w+", text) if len(w) > 3}
        for other_locator, other in seen:
            if not tokens or not other:
                continue
            overlap = len(tokens & other) / max(len(tokens), len(other))
            if overlap > 0.8:
                out.append(_finding(
                    "content/duplicate-bullet", Category.RESUME_CRAFT, Severity.MINOR,
                    f"Near-duplicate of {other_locator}",
                    "Cut one, or differentiate the scope.",
                    Provenance.HEURISTIC, evidence=text[:90], locator=locator,
                ))
                break
        seen.append((locator, tokens))
    return out


def analyze(doc: ExtractedDoc, resume: Resume, target_title: str = "AI Engineer") -> list[Finding]:
    findings = parseability(doc)
    if not doc.has_text_layer:
        return findings
    findings += structure(resume)
    findings += contact(resume)
    findings += title_alignment(resume, target_title)
    findings += content_mechanics(resume)
    return findings
