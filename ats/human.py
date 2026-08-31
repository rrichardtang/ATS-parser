"""The second gate: what happens after a parser reads the file cleanly.

Two readers, and they fail differently. A recruiter scans for seconds, mostly the
top third of page one. A hiring manager then asks whether the work is real. A
resume can pass the parser perfectly and lose at either.

The recruiter checks here reuse the page-1 word boxes from extract.py, so
"your best evidence is below the fold" is measured against actual geometry rather
than guessed from text order.
"""
from __future__ import annotations

import re

from .extract import ExtractedDoc
from .invariants import SPECIFIC_TOKEN_RE
from .models import Category, Finding, Gate, Provenance, Severity
from .sections import Resume

FOLD_FRACTION = 0.33

ROLE_IDENTITY_RE = re.compile(
    r"(?i)\b(ai|ml|machine learning|deep learning|software|data|research|mlops|nlp)\s+"
    r"(engineer|scientist|developer|researcher)\b"
)

EVAL_RE = re.compile(
    r"(?i)\b(eval(?:uation|s)?|benchmark|accuracy|precision|recall|f1|auc|roc|bleu|"
    r"rouge|perplexity|held[- ]out|test set|ground truth|labell?ed|annotat|"
    r"a/b test|offline metric|groundedness|hallucination rate)\b"
)

PRODUCTION_RE = re.compile(
    r"(?i)\b(production|prod|deployed|shipped|serving|live|users?|customers?|traffic|"
    r"uptime|sla|slo|on[- ]call|incident|p9\d|qps|rps|throughput|latency|rollout|"
    r"canary|req/min|requests per second)\b"
)

NOTEBOOK_RE = re.compile(
    r"(?i)\b(jupyter|notebook|colab|kaggle|coursework|class project|tutorial|"
    r"bootcamp|proof of concept|poc)\b"
)


def _fold_text(doc: ExtractedDoc) -> str:
    """Everything in the top third of page one, in reading order."""
    if not doc.page_sizes:
        return ""
    height = doc.page_sizes[0][1]
    limit = height * FOLD_FRACTION
    words = [w for w in doc.words_on(0) if w.top <= limit]
    words.sort(key=lambda w: (round(w.top / 4), w.x0))
    return " ".join(w.text for w in words)


def recruiter_scan(doc: ExtractedDoc, resume: Resume) -> list[Finding]:
    out: list[Finding] = []
    fold = _fold_text(doc)

    if not fold:
        return out

    has_identity = bool(ROLE_IDENTITY_RE.search(fold))
    has_evidence = bool(SPECIFIC_TOKEN_RE.search(fold)) or bool(
        re.search(r"\d", fold)
    )

    if not has_identity:
        out.append(Finding(
            rule_id="scan/no-identity-above-fold",
            category=Category.RESUME_CRAFT,
            gate=Gate.RECRUITER,
            severity=Severity.MAJOR,
            message="Nothing in the top third of page 1 says what you are",
            fix="Put a role line near the top: “AI Engineer, 3 yrs — LLM serving and evals.”",
            evidence=fold[:120] or "(empty)",
            locator="page1.fold",
            provenance=Provenance.RECRUITER_EVIDENCE,
        ))

    if not has_evidence:
        out.append(Finding(
            rule_id="scan/no-evidence-above-fold",
            category=Category.RESUME_CRAFT,
            gate=Gate.RECRUITER,
            severity=Severity.MAJOR,
            message="No concrete evidence -- no tool, model or number -- above the fold",
            fix="Move your strongest technical result into the top third of page 1.",
            evidence=fold[:120],
            locator="page1.fold",
            provenance=Provenance.RECRUITER_EVIDENCE,
        ))

    out.extend(_experience_outranked(doc, resume))

    if not resume.summary and not has_identity:
        out.append(Finding(
            rule_id="scan/no-summary",
            category=Category.RESUME_CRAFT,
            gate=Gate.RECRUITER,
            severity=Severity.MINOR,
            message="No summary line stating what you are",
            fix="One line. What you are, how long, what you work on.",
            evidence="(no summary section)",
            locator="document",
            provenance=Provenance.RECRUITER_EVIDENCE,
        ))

    out.extend(_career_arc(resume))
    return out


# Sections that should never come before Experience on a mid-level resume.
OPTIONAL_BEFORE_EXPERIENCE = ("interests", "awards", "certifications", "publications")


def _experience_outranked(doc: ExtractedDoc, resume: Resume) -> list[Finding]:
    """Depth alone is not the defect -- being outranked by optional sections is.

    A recruiter reads top-down. Anything above Experience is spending the seconds
    that Experience needed, so the check names the sections to move rather than
    asserting an arbitrary "must appear in the top N%".
    """
    order = resume.section_order
    if "experience" not in order:
        return []
    position = order.index("experience")
    above = [s for s in order[:position] if s in OPTIONAL_BEFORE_EXPERIENCE]
    page, top = _first_role_position(doc, resume)
    below_fold = page is not None and (
        page > 0 or top > doc.page_sizes[0][1] * FOLD_FRACTION
    )
    if not above or not below_fold:
        return []
    where = f"page {page + 1}" if page else "below the fold"
    return [Finding(
        rule_id="scan/experience-outranked",
        category=Category.RESUME_CRAFT,
        gate=Gate.RECRUITER,
        severity=Severity.MAJOR,
        message=(
            f"{' and '.join(s.title() for s in above)} appear before Experience, "
            f"pushing your first role {where}"
        ),
        fix=f"Move Experience above {' and '.join(above)}.",
        evidence=" > ".join(order[: position + 1]),
        locator="document",
        provenance=Provenance.RECRUITER_EVIDENCE,
    )]


def _first_role_position(doc: ExtractedDoc, resume: Resume) -> tuple[int | None, float]:
    if not resume.roles:
        return None, 0.0
    needle = (resume.roles[0].company or resume.roles[0].title or "").split()
    if not needle:
        return None, 0.0
    token = needle[0]
    for word in doc.words:
        if word.text.strip(",.|") == token.strip(",.|"):
            return word.page, word.top
    return None, 0.0


def _career_arc(resume: Resume) -> list[Finding]:
    """An unexplained pivot is a question a recruiter will not stop to answer."""
    dated = [r for r in resume.roles if r.start]
    if len(dated) < 2:
        return []
    titles = [(r.title or r.heading).lower() for r in dated]
    ai_flags = [bool(re.search(r"(ai|ml|machine learning|data|research)", t)) for t in titles]
    if ai_flags and ai_flags[0] and not any(ai_flags[1:]):
        return [Finding(
            rule_id="scan/unexplained-pivot",
            category=Category.RESUME_CRAFT,
            gate=Gate.RECRUITER,
            severity=Severity.MINOR,
            message="Your current role is AI/ML but no earlier role reads that way",
            fix="Add one line showing the bridge -- the first ML work you shipped and when.",
            evidence=" -> ".join(t[:26] for t in reversed(titles)),
            locator="experience",
            provenance=Provenance.RECRUITER_EVIDENCE,
        )]
    return []


def credibility(resume: Resume) -> list[Finding]:
    """The hiring manager's question: did this actually happen?"""
    out: list[Finding] = []
    bullets = [b for _, b in resume.bullets]
    blob = " ".join(bullets) + " " + resume.summary

    if bullets and not EVAL_RE.search(blob):
        out.append(Finding(
            rule_id="cred/no-evaluation",
            category=Category.EVALUATION_RIGOUR,
            severity=Severity.MAJOR,
            message="No bullet says how model quality was measured",
            fix="Name one eval: the metric, the dataset, and the number before and after.",
            evidence="no eval/benchmark/accuracy language in any bullet",
            locator="experience",
            provenance=Provenance.JD_DERIVED,
        ))

    if bullets and not PRODUCTION_RE.search(blob):
        out.append(Finding(
            rule_id="cred/no-production",
            category=Category.PRODUCTION_OWNERSHIP,
            severity=Severity.MAJOR,
            message="Nothing shows the work reached production",
            fix="Add scale, latency, traffic or uptime for something you shipped.",
            evidence="no production/serving/latency language in any bullet",
            locator="experience",
            provenance=Provenance.JD_DERIVED,
        ))

    if NOTEBOOK_RE.search(blob) and not PRODUCTION_RE.search(blob):
        out.append(Finding(
            rule_id="cred/notebook-only",
            category=None,
            gate=Gate.MANAGER,
            advice_only=True,
            severity=Severity.MINOR,
            message="Work reads as notebook or coursework rather than shipped systems",
            fix="Lead with something that ran in production, however small.",
            evidence=NOTEBOOK_RE.search(blob).group(0),
            locator="experience",
            provenance=Provenance.JD_DERIVED,
        ))

    projects = resume.sections.get("projects", [])
    if projects and not any(re.search(r"(?i)(github|https?://|gitlab)", l) for l in projects):
        out.append(Finding(
            rule_id="cred/unlinked-projects",
            category=None,
            gate=Gate.MANAGER,
            advice_only=True,
            severity=Severity.MINOR,
            message="Projects are listed but not linked",
            fix="Link each one. An unlinked project is a claim; a linked one is evidence.",
            evidence=projects[0][:80] if projects else "",
            locator="projects",
            provenance=Provenance.JD_DERIVED,
        ))

    # `cred/no-named-models` was retired here (rule-mapping.md §4). It fired when a
    # closed list of 15 model families matched nothing -- no Gemini, no DeepSeek, no
    # Cohere, and a `gpt-?\d` that does not match `o3` -- against the fastest-moving
    # vocabulary in the corpus, so "Fine-tuned Gemini 1.5" fired it. The property it
    # gestured at has an owner now: C2, the named system, in `Production ownership`.
    return out


def analyze(doc: ExtractedDoc, resume: Resume) -> list[Finding]:
    if not doc.has_text_layer:
        return []
    return recruiter_scan(doc, resume) + credibility(resume)
