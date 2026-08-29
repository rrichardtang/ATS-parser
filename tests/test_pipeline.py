"""End-to-end behaviour on real PDFs, and the rules that must hold across a run."""
import pytest

from ats.extract import ExtractionError, extract
from ats.models import Gate, Provenance, Severity
from ats.pipeline import RunInput, analyze
from ats.report import to_markdown, to_pdf
from ats.sections import parse


def test_strong_resume_is_nearly_clean(analyzed):
    report = analyzed["strong"]
    assert report.composite >= 90
    assert not [f for f in report.findings if f.severity is Severity.CRITICAL]


def test_missing_phone_barely_moves_the_score(analyzed):
    """The anti-hard-gate commitment, end to end on real files.

    These two PDFs differ only in the phone number. A public checker returned
    22/100 for exactly this.
    """
    delta = analyzed["strong"].composite - analyzed["no_phone"].composite
    assert 0 < delta < 5, f"missing phone moved the score by {delta:.1f} points"


def test_hidden_text_is_the_top_finding(analyzed):
    report = analyzed["hidden_text"]
    top = report.findings[0]
    assert top.rule_id == "parse/hidden-text"
    assert top.severity is Severity.CRITICAL
    assert "fraud" in top.fix.lower()


def test_scanned_pdf_fails_cleanly_without_crashing(analyzed):
    report = analyzed["scanned"]
    assert any(f.rule_id == "parse/no-text-layer" for f in report.findings)


def test_two_column_hits_the_parser_gate_not_the_human_gate(analyzed):
    report = analyzed["two_column"]
    assert any(f.rule_id == "parse/multi-column" for f in report.findings)
    assert report.parser_subscore < report.human_subscore


def test_slop_resume_fails_the_human_gate_while_parsing_fine(analyzed):
    """The two gates must move independently, or modelling both bought nothing."""
    report = analyzed["slop"]
    assert report.parser_subscore > 90
    assert report.human_subscore < 60


def test_buried_experience_is_a_recruiter_finding(analyzed):
    report = analyzed["buried_evidence"]
    ids = {f.rule_id for f in report.by_gate(Gate.RECRUITER)}
    assert "scan/experience-outranked" in ids


def test_every_finding_declares_provenance(analyzed):
    for name, report in analyzed.items():
        for f in report.findings:
            assert isinstance(f.provenance, Provenance), f"{name}/{f.rule_id}"


def test_heuristic_findings_never_exceed_minor(analyzed):
    """A rule resting on judgment must not be able to sink someone's score."""
    for name, report in analyzed.items():
        for f in report.findings:
            if f.provenance is Provenance.HEURISTIC and f.source == "deterministic":
                assert f.severity is Severity.MINOR, f"{name}/{f.rule_id}"


def test_every_finding_has_a_fix_and_evidence(analyzed):
    for name, report in analyzed.items():
        for f in report.findings:
            assert f.fix.strip(), f"{name}/{f.rule_id} has no fix"
            assert f.evidence.strip() or f.locator == "document", f"{name}/{f.rule_id}"


def test_ledger_reconciles_on_every_fixture(analyzed):
    for name, report in analyzed.items():
        total = 100.0 + sum(row.points for row in report.ledger)
        assert abs(total - report.composite) < 0.05, name


def test_top_fixes_are_distinct_problems(analyzed):
    for name, report in analyzed.items():
        ids = [f.rule_id for f in report.top_fixes]
        assert len(ids) == len(set(ids)), f"{name} repeats a rule in top fixes"


def test_no_key_produces_a_complete_partial_report(analyzed):
    report = analyzed["slop"]
    assert report.partial
    assert any("No API key" in n for n in report.notes)
    assert len(report.findings) > 10


def test_corrupt_file_raises_cleanly(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 this is not really a pdf")
    with pytest.raises(ExtractionError):
        extract(str(bad))


def test_exports_render_for_every_fixture(analyzed):
    for name, report in analyzed.items():
        markdown = to_markdown(report)
        assert "# Resume diagnostics" in markdown
        pdf = to_pdf(report)
        assert pdf.startswith(b"%PDF")


def test_exported_pdf_carries_no_branding(analyzed):
    """Generated locally by ReportLab, so it contains only our own content."""
    import io

    import pdfplumber

    pdf = to_pdf(analyzed["strong"])
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        text = " ".join(page.extract_text() or "" for page in doc.pages).lower()
        assert doc.metadata.get("Producer", "") == ""
        for word in ("watermark", "trial", "evaluation copy", "reportlab"):
            assert word not in text


def test_cid_glyphs_are_normalised():
    """pdfplumber emits (cid:N) for unmapped glyphs; left alone it destroys bullets."""
    from ats.extract import normalize_text

    assert normalize_text("(cid:127) Cut latency") == "• Cut latency"


def test_unreadable_pdf_does_not_score_well(analyzed):
    """A file no ATS can read must not come out near-perfect.

    Nothing downstream runs when there is no text layer, so every other category
    sits at its default. Reporting that as a high score would be worse than
    useless.
    """
    report = analyzed["scanned"]
    assert report.composite <= 15
    assert report.parser_subscore == 0.0
    assert report.human_subscore == 0.0
    assert any("nothing beyond the file itself" in n.lower() for n in report.notes)
