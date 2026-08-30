"""Orchestrates a run: extract -> sections -> deterministic -> LLM passes -> score.

Passes 1 and 2 run concurrently; pass 3 depends on both. With no key the
deterministic half still produces a complete report, marked partial.
"""
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field

from . import config, human, keywords, passes, rules, slop
from .extract import ExtractedDoc, ExtractionError, extract
from .llm import Provider, providers_from
from .models import Category, Finding, Report
from .score import build
from .sections import Resume, parse

__all__ = [
    "RunInput", "analyze", "generate_rewrites", "parse_resume", "ExtractionError",
]


@dataclass
class RunInput:
    pdf_path: str
    jd_text: str = ""
    # Empty means "not explicitly set" -- analyze() resolves it from the personal
    # JD corpus's digest (config.target_titles()) when one exists, falling back to
    # "AI Engineer" only when neither is available. Never both a real default and
    # a way to tell "the caller chose this" apart, so the sentinel has to be empty.
    target_title: str = ""
    keys: dict[str, str] = field(default_factory=dict)
    models: dict[str, str] = field(default_factory=dict)
    ensemble_mode: str = "default"
    enable_rewrites: bool = True


def parse_resume(pdf_path: str) -> Resume:
    """Extract + parse only, no scoring. Lets a caller hold onto the parsed Resume
    (bullet text by locator) for a later generate_rewrites() call without having to
    re-run analyze() or keep the PDF around."""
    doc = extract(pdf_path)
    return parse(doc.text)


def deterministic(
    doc: ExtractedDoc, resume: Resume, jd_text: str, target_title: str
) -> list[Finding]:
    findings = rules.analyze(doc, resume, target_title)
    if not doc.has_text_layer:
        return findings
    findings += slop.analyze(resume, doc.text)
    findings += human.analyze(doc, resume)
    findings += keywords.analyze(resume, doc.text, jd_text)
    return findings


def _resolve_target_title(explicit: str) -> str:
    if explicit:
        return explicit
    titles = config.target_titles()
    return titles[0] if titles else "AI Engineer"


def analyze(run: RunInput) -> Report:
    doc = extract(run.pdf_path)
    resume = parse(doc.text)
    target_title = _resolve_target_title(run.target_title)
    findings = deterministic(doc, resume, run.jd_text, target_title)

    providers = providers_from(run.keys, run.models)
    settings = config.ensemble_settings(run.ensemble_mode)
    notes: list[str] = []
    meta: dict = {
        "mode": settings["mode"],
        "providers": [p.label for p in providers],
        "deterministic_findings": len(findings),
    }

    if not providers or not doc.has_text_layer:
        if not providers:
            notes.append(
                "No API key supplied. Deterministic checks only -- everything "
                "mechanically checkable is here; substance and slop judgement are not."
            )
        return build(findings, partial=True, notes=notes, run_meta=meta)

    caught = [f.evidence for f in findings if f.rule_id.startswith("slop/")]

    digest = config.jd_digest()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        content_future = pool.submit(
            passes.content_pass, providers, resume, doc.text, run.jd_text,
            findings, int(settings["content_samples"]), float(settings["temperature"]),
            digest,
        )
        slop_future = pool.submit(
            passes.slop_pass, providers, resume, caught,
            int(settings["slop_samples"]), int(settings["slop_vote_k"]),
            float(settings["temperature"]),
        )
        content = _safe(content_future, "content")
        slop_result = _safe(slop_future, "slop")

    findings += content.data
    findings += slop_result.data
    meta["pass1"] = {k: v for k, v in content.meta.items() if k != "scores"}
    meta["pass2"] = slop_result.meta
    notes += [f"Content pass degraded: {e}" for e in content.errors[:2]]
    notes += [f"Slop pass degraded: {e}" for e in slop_result.errors[:2]]

    rewrites = []
    if run.enable_rewrites:
        rewrite_result = _safe(
            None, "rewrite",
            fn=lambda: passes.rewrite_pass(
                providers, resume, findings,
                int(settings["rewrite_objectives"]), int(settings["rewrite_samples"]),
                bool(settings["rewrite_judge"]), float(settings["rewrite_margin"]),
                float(settings["temperature"]), digest,
            ),
        )
        rewrites = rewrite_result.data
        meta["pass3"] = rewrite_result.meta
        notes += [f"Rewrite pass degraded: {e}" for e in rewrite_result.errors[:2]]

    llm_scores = {}
    for name, values in (content.meta.get("scores") or {}).items():
        try:
            llm_scores[Category(name)] = values
        except ValueError:
            continue

    partial = bool(content.errors or slop_result.errors) or len(providers) < 2
    if len(providers) == 1:
        notes.append(
            f"One provider ({providers[0].name}). Cross-provider ensembling is off, "
            "so slop findings carry a single model's blindspots."
        )

    report = build(
        findings, llm_categories=llm_scores, partial=partial, notes=notes, run_meta=meta
    )
    report.rewrites = rewrites
    return report


def generate_rewrites(
    report: Report,
    resume: Resume,
    keys: dict[str, str],
    models: dict[str, str],
    ensemble_mode: str = "default",
) -> Report:
    """Pass 3 alone, run on demand against an already-scored report.

    Kept separate from analyze() so a caller (the web UI) can gate generation
    behind an explicit action -- scoring a resume never implies paying for
    rewrite generation too. Mutates and returns `report`; `resume` is whatever
    parse_resume() returned when the report was first built.
    """
    providers = providers_from(keys, models)
    if not providers:
        report.notes.append(
            "No API key supplied -- nothing to generate rewrites with."
        )
        return report

    settings = config.ensemble_settings(ensemble_mode)
    rewrite_result = _safe(
        None, "rewrite",
        fn=lambda: passes.rewrite_pass(
            providers, resume, report.findings,
            int(settings["rewrite_objectives"]), int(settings["rewrite_samples"]),
            bool(settings["rewrite_judge"]), float(settings["rewrite_margin"]),
            float(settings["temperature"]), config.jd_digest(),
        ),
    )
    report.rewrites = rewrite_result.data
    report.run_meta["pass3"] = rewrite_result.meta
    report.notes += [f"Rewrite pass degraded: {e}" for e in rewrite_result.errors[:2]]
    return report


def _safe(future, label: str, fn=None):
    """A failing pass degrades to empty rather than losing the whole report."""
    from .ensemble import PassResult

    try:
        return future.result() if future is not None else fn()
    except Exception as exc:  # noqa: BLE001
        return PassResult(errors=[f"{label}: {exc}"])


def run_deterministic_only(run: RunInput) -> Report:
    run.keys = {}
    return analyze(run)
