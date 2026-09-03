"""Turns extracted text into the structure every later stage reads.

Sections, contact block, roles with dates, and bullets. Dates are parsed into real
intervals so years-of-experience and gaps are computed, not guessed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

SECTION_SYNONYMS: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "profile", "objective", "about", "professional summary"),
    "experience": (
        "experience", "work experience", "professional experience", "employment",
        "work history", "relevant experience", "engineering experience",
    ),
    "projects": ("projects", "personal projects", "selected projects", "side projects"),
    "education": ("education", "academic background"),
    "skills": ("skills", "technical skills", "technologies", "tools", "core competencies"),
    "publications": ("publications", "papers", "research", "talks"),
    "certifications": ("certifications", "certificates", "licenses"),
    "awards": ("awards", "honors", "achievements"),
    "interests": ("interests", "hobbies", "activities"),
}

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

_MONTH_RE = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
_PRESENT_RE = r"(?:present|current|now|ongoing)"
_DATE_TOKEN = rf"(?:{_MONTH_RE}\.?\s+\d{{4}}|\d{{1,2}}[/-]\d{{4}}|\d{{4}})"
DATE_RANGE_RE = re.compile(
    rf"({_DATE_TOKEN})\s*(?:-|–|—|to|until)\s*({_DATE_TOKEN}|{_PRESENT_RE})",
    re.IGNORECASE,
)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
LINKEDIN_RE = re.compile(r"linkedin\.com/[\w/-]+", re.IGNORECASE)
GITHUB_RE = re.compile(r"github\.(?:com|io)/[\w/-]+", re.IGNORECASE)
URL_RE = re.compile(r"(?:https?://|www\.)[\w./-]+", re.IGNORECASE)

BULLET_RE = re.compile(r"^\s*(?:[•\-–*‣·o]|\d+[.)])\s+")


@dataclass
class Contact:
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""
    location: str = ""


@dataclass
class Role:
    heading: str
    title: str = ""
    company: str = ""
    start: date | None = None
    end: date | None = None
    is_current: bool = False
    bullets: list[str] = field(default_factory=list)
    line_index: int = 0

    @property
    def months(self) -> int:
        if not self.start:
            return 0
        end = self.end or date.today()
        return max(0, (end.year - self.start.year) * 12 + end.month - self.start.month)


@dataclass
class Resume:
    lines: list[str] = field(default_factory=list)
    sections: dict[str, list[str]] = field(default_factory=dict)
    section_order: list[str] = field(default_factory=list)
    contact: Contact = field(default_factory=Contact)
    roles: list[Role] = field(default_factory=list)
    summary: str = ""
    skills_text: str = ""

    @property
    def bullets(self) -> list[tuple[str, str]]:
        """(locator, text) for every experience/project bullet."""
        out: list[tuple[str, str]] = []
        for r_index, role in enumerate(self.roles):
            for b_index, bullet in enumerate(role.bullets):
                out.append((f"exp[{r_index}].bullet[{b_index}]", bullet))
        return out

    @property
    def total_months(self) -> int:
        """Union of role intervals, so overlapping roles are not double counted."""
        spans = [(r.start, r.end or date.today()) for r in self.roles if r.start]
        if not spans:
            return 0
        spans.sort()
        merged: list[list[date]] = [list(spans[0])]
        for start, end in spans[1:]:
            if start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        return sum(
            (e.year - s.year) * 12 + e.month - s.month for s, e in merged
        )

    @property
    def years_experience(self) -> float:
        return round(self.total_months / 12, 1)

    def gaps(self, min_months: int = 6) -> list[tuple[date, date]]:
        spans = sorted((r.start, r.end or date.today()) for r in self.roles if r.start)
        found = []
        for (_, prev_end), (next_start, _) in zip(spans, spans[1:]):
            months = (next_start.year - prev_end.year) * 12 + next_start.month - prev_end.month
            if months >= min_months:
                found.append((prev_end, next_start))
        return found


def _canonical_section(line: str) -> str | None:
    """A heading is short, and matches the vocabulary once punctuation is stripped."""
    stripped = line.strip().strip(":").strip()
    if not stripped or len(stripped) > 40 or BULLET_RE.match(line):
        return None
    lowered = re.sub(r"[^a-z& ]", "", stripped.lower()).strip()
    for canonical, names in SECTION_SYNONYMS.items():
        if lowered in names:
            return canonical
    return None


def _parse_token(token: str) -> date | None:
    token = token.strip().rstrip(".")
    if re.fullmatch(_PRESENT_RE, token, re.IGNORECASE):
        return None
    m = re.fullmatch(rf"({_MONTH_RE})\.?\s+(\d{{4}})", token, re.IGNORECASE)
    if m:
        return date(int(m.group(2)), _MONTHS[m.group(1).lower()[:4].rstrip(".")[:4]
                                             if m.group(1).lower()[:4] in _MONTHS
                                             else m.group(1).lower()[:3]], 1)
    m = re.fullmatch(r"(\d{1,2})[/-](\d{4})", token)
    if m:
        return date(int(m.group(2)), min(12, max(1, int(m.group(1)))), 1)
    m = re.fullmatch(r"(\d{4})", token)
    if m:
        return date(int(m.group(1)), 1, 1)
    return None


def parse_date_range(text: str) -> tuple[date | None, date | None, bool] | None:
    m = DATE_RANGE_RE.search(text)
    if not m:
        return None
    start = _parse_token(m.group(1))
    end_token = m.group(2)
    is_current = bool(re.fullmatch(_PRESENT_RE, end_token.strip(), re.IGNORECASE))
    end = None if is_current else _parse_token(end_token)
    return start, end, is_current


def _split_title_company(heading: str) -> tuple[str, str]:
    cleaned = DATE_RANGE_RE.sub("", heading).strip(" ,|-–—\t")
    for sep in (",", " at ", " | ", " – ", " - ", " — "):
        if sep in cleaned:
            left, right = cleaned.split(sep, 1)
            return left.strip(), right.strip(" ,|-–—")
    return cleaned, ""


def parse(text: str) -> Resume:
    resume = Resume(lines=text.splitlines())
    current = "header"
    resume.sections[current] = []
    for line in resume.lines:
        canonical = _canonical_section(line)
        if canonical:
            current = canonical
            resume.sections.setdefault(current, [])
            if current not in resume.section_order:
                resume.section_order.append(current)
            continue
        resume.sections.setdefault(current, []).append(line)

    header_blob = "\n".join(resume.sections.get("header", [])[:6])
    resume.contact = _parse_contact(header_blob or text[:400])
    resume.summary = " ".join(
        l.strip() for l in resume.sections.get("summary", []) if l.strip()
    )
    resume.skills_text = " ".join(
        l.strip() for l in resume.sections.get("skills", []) if l.strip()
    )
    resume.roles = _parse_roles(
        resume.sections.get("experience", []) + resume.sections.get("projects", [])
    )
    return resume


def _parse_contact(blob: str) -> Contact:
    contact = Contact()
    if m := EMAIL_RE.search(blob):
        contact.email = m.group(0)
    if m := PHONE_RE.search(blob):
        contact.phone = m.group(0)
    if m := LINKEDIN_RE.search(blob):
        contact.linkedin = m.group(0)
    if m := GITHUB_RE.search(blob):
        contact.github = m.group(0)
    for m in URL_RE.finditer(blob):
        url = m.group(0)
        if "linkedin" not in url.lower() and "github" not in url.lower():
            contact.website = url
            break
    if m := re.search(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*),\s*([A-Z]{2})\b", blob):
        contact.location = m.group(0)
    return contact


def _parse_roles(lines: list[str]) -> list[Role]:
    roles: list[Role] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if BULLET_RE.match(line):
            if roles:
                roles[-1].bullets.append(BULLET_RE.sub("", line).strip())
            continue
        parsed = parse_date_range(stripped)
        looks_like_heading = parsed is not None or (
            len(stripped) < 90 and not stripped.endswith(".") and index + 1 < len(lines)
        )
        if parsed is not None:
            title, company = _split_title_company(stripped)
            start, end, current = parsed
            roles.append(
                Role(heading=stripped, title=title, company=company, start=start,
                     end=end, is_current=current, line_index=index)
            )
        elif looks_like_heading and not roles:
            title, company = _split_title_company(stripped)
            roles.append(Role(heading=stripped, title=title, company=company, line_index=index))
        elif roles and not BULLET_RE.match(line):
            # Continuation of the previous bullet, or a date line under the heading.
            if roles[-1].bullets and stripped[0].islower():
                roles[-1].bullets[-1] += " " + stripped
            elif parsed is None and len(stripped) < 90 and roles[-1].bullets:
                title, company = _split_title_company(stripped)
                roles.append(Role(heading=stripped, title=title, company=company,
                                  line_index=index))
    return roles
