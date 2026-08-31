"""The dedicated slop pass.

Runs separately from the general content analysis because, folded into a six-way
prompt, slop detection gets shallow attention. Deterministic patterns run here;
the LLM half is a separate call (see prompts.slop_judge).

Nothing in this module produces an AI-likelihood number. Per the no-ai-slop skill:
detectors guess, named patterns are evidence the user can check.
"""
from __future__ import annotations

import re

from .invariants import has_metric, portability
from .models import Category, Finding, Gate, Provenance, Severity
from .sections import Resume
from .slop_patterns import PATTERNS, Scope

# Spans where a banned word is a name, not a style choice. "Harness" is a CI
# product; "Robust Intelligence" was a company. Matching inside these would
# produce a confident false positive on a factually correct resume.
PROTECTED_RE = re.compile(
    r"""(?x)
      \b(?:Harness|Robust\ Intelligence|Streamlit|Elevate|Delve|Fostering|
         Synergy|Beacon|Tapestry|Realm|Paradigm|Catalyst)\b
    | \b[A-Z][a-z]+\ (?:Inc|LLC|Ltd|Labs|AI|Technologies|Systems|Corp)\b
    | \b(?:https?://|www\.)\S+
    | `[^`]+`
    """
)

# A banned word is not slop when it is the ordinary technical name for the thing.
# "eval harness" and "test harness" are standard vocabulary; flagging them would be
# a confident false positive on a factually correct resume.
NEUTRAL_CONTEXT = re.compile(
    r"""(?ix)
      \b(?:eval|evaluation|test|testing|training|benchmark|CI|build)\s+harness\b
    | \bharness(?:es|ed|ing)?\s+(?:the\s+)?(?:GPU|CPU|cluster|parallelism)\b
    | \brobust(?:ness)?\s+(?:to|against)\s+\w+
    | \bstreamlit\b
    """
)

# Portability above this means the bullet is mostly generic scaffolding.
PORTABILITY_LIMIT = 0.82
# Bullets whose lengths cluster this tightly read as machine-generated uniformity.
# Coefficient of variation, so the check scales with bullet length instead of
# firing on any resume that happens to write medium-length bullets.
RHYTHM_CV_LIMIT = 0.10
RHYTHM_MIN_BULLETS = 5


def _protected_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in PROTECTED_RE.finditer(text)]


def _is_protected(text: str, fragment: str) -> bool:
    spans = _protected_spans(text) + [
        (m.start(), m.end()) for m in NEUTRAL_CONTEXT.finditer(text)
    ]
    if not spans:
        return False
    for match in re.finditer(re.escape(fragment), text):
        if not any(s <= match.start() and match.end() <= e for s, e in spans):
            return False
    return True


def _scan(text: str, scope: Scope, locator: str) -> list[Finding]:
    findings: list[Finding] = []
    for pattern in PATTERNS:
        if pattern.scope is not scope:
            continue
        for hit in pattern.find(text):
            if _is_protected(text, hit):
                continue
            findings.append(
                Finding(
                    rule_id=pattern.id,
                    category=Category.RESUME_CRAFT,
                    gate=Gate.MANAGER,
                    severity=pattern.severity,
                    message=f"{pattern.id.split('/', 1)[1].replace('-', ' ')}: “{hit.strip()}”",
                    fix=pattern.fix,
                    evidence=hit.strip(),
                    locator=locator,
                    provenance=pattern.provenance,
                )
            )
    return findings


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, str]] = set()
    out: list[Finding] = []
    for f in findings:
        key = (f.rule_id, f.evidence.lower(), f.locator)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def analyze(resume: Resume, full_text: str) -> list[Finding]:
    findings: list[Finding] = []

    for locator, bullet in resume.bullets:
        findings.extend(_scan(bullet, Scope.BULLET, locator))
        score = portability(bullet)
        # A real metric is unportable by construction: it cannot move to another
        # candidate unchanged. Only unmeasured bullets can be generic scaffolding.
        if score > PORTABILITY_LIMIT and len(bullet.split()) >= 8 and not has_metric(bullet):
            findings.append(
                Finding(
                    rule_id="slop/portable",
                    category=Category.RESUME_CRAFT,
                    gate=Gate.MANAGER,
                    severity=Severity.MAJOR,
                    message=(
                        f"{score:.0%} of this bullet survives stripping every name, "
                        "number and tool -- it would fit any candidate at any company"
                    ),
                    fix="Name the system, the metric, and what changed.",
                    evidence=bullet[:120],
                    locator=locator,
                    provenance=Provenance.RECRUITER_EVIDENCE,
                )
            )

    if resume.summary:
        findings.extend(_scan(resume.summary, Scope.SUMMARY, "summary"))
        findings.extend(_scan(resume.summary, Scope.BULLET, "summary"))

    findings.extend(_scan(full_text, Scope.DOCUMENT, "document"))
    findings.extend(_rhythm(resume))
    findings.extend(_synonym_cycling(resume))
    return _dedupe(findings)


def _rhythm(resume: Resume) -> list[Finding]:
    """Near-identical bullet shape across every role is a strong LLM tell.

    Note this is exactly why the XYZ template is not enforced: applying one formula
    to every bullet would produce this pattern by construction.
    """
    bullets = [b for _, b in resume.bullets]
    if len(bullets) < RHYTHM_MIN_BULLETS:
        return []
    lengths = [len(b.split()) for b in bullets]
    mean = sum(lengths) / len(lengths)
    stdev = (sum((l - mean) ** 2 for l in lengths) / len(lengths)) ** 0.5
    cv = stdev / mean if mean else 1.0
    openers = [b.split()[0].lower() for b in bullets if b.split()]
    repeated_opener = len(set(openers)) <= max(2, len(openers) // 4)
    if cv < RHYTHM_CV_LIMIT or repeated_opener:
        reason = (
            f"every bullet is within {stdev:.1f} words of {mean:.0f}"
            if cv < RHYTHM_CV_LIMIT
            else f"{len(openers) - len(set(openers))} bullets share an opening word"
        )
        return [
            Finding(
                rule_id="slop/robotic-rhythm",
                category=Category.RESUME_CRAFT,
                gate=Gate.MANAGER,
                severity=Severity.MINOR,
                message=f"Bullets are uniform in shape -- {reason}",
                fix="Vary length and construction; let the content set the shape.",
                evidence=bullets[0][:100],
                locator="experience",
                provenance=Provenance.RECRUITER_EVIDENCE,
            )
        ]
    return []


CYCLE_GROUPS = [
    {"built", "created", "developed", "engineered", "constructed", "crafted"},
    {"improved", "enhanced", "optimized", "refined", "elevated", "boosted"},
    {"led", "spearheaded", "drove", "orchestrated", "championed"},
]


def _synonym_cycling(resume: Resume) -> list[Finding]:
    """Rotating synonyms for style is a tell. If the clear word is right, repeat it."""
    bullets = [b.lower() for _, b in resume.bullets]
    if len(bullets) < 4:
        return []
    findings = []
    for group in CYCLE_GROUPS:
        used = {w for w in group if any(re.search(rf"\b{w}\b", b) for b in bullets)}
        if len(used) >= 3:
            findings.append(
                Finding(
                    rule_id="slop/synonym-cycling",
                    category=Category.RESUME_CRAFT,
                    gate=Gate.MANAGER,
                    severity=Severity.MINOR,
                    message=f"Rotating synonyms for one idea: {', '.join(sorted(used))}",
                    fix="Pick the clearest verb and reuse it.",
                    evidence=", ".join(sorted(used)),
                    locator="experience",
                    provenance=Provenance.RECRUITER_EVIDENCE,
                )
            )
    return findings
