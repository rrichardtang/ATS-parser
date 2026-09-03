"""Markdown and PDF export.

The PDF is built locally with ReportLab -- no headless browser, no hosted service --
so the file contains only what this code puts in it. No watermark, no branding.
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import Gate, Report

INK = colors.HexColor("#16181d")
SOFT = colors.HexColor("#5a6070")
RULE = colors.HexColor("#d8dce4")
MARK = colors.HexColor("#2b4c8c")
FLAG = colors.HexColor("#b3261e")
KEEP = colors.HexColor("#1f6f4a")

GATE_TITLES = {
    Gate.PARSER: ("Parser gate", "Whether an ATS can extract your fields at all."),
    Gate.RECRUITER: ("Recruiter scan", "The first human, reading for seconds."),
    Gate.MANAGER: ("Hiring manager read", "Whether the work described actually happened."),
}

CAVEAT = (
    "A diagnostic over named defects — not a portable “ATS score”, not a pass/fail "
    "prediction, and not comparable to another tool’s number. Each tool invents its "
    "own rubric and none is validated against interview outcomes."
)


def _escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def to_markdown(report: Report) -> str:
    lines: list[str] = [
        "# Resume diagnostics",
        "",
        f"**{report.composite:.0f}** / 100 (grade {report.grade}) — "
        f"parser gate {report.parser_subscore:.0f}, human gate {report.human_subscore:.0f}",
        "",
        f"> {CAVEAT}",
        "",
    ]
    if report.notes:
        lines += ["## Run notes", ""] + [f"- {n}" for n in report.notes] + [""]

    lines += ["## Score derivation", "", "| | Points |", "|---|---:|", "| Starting score | 100 |"]
    for row in report.ledger:
        lines.append(f"| {row.label} | {row.points:+.1f} |")
    lines += [f"| **Composite** | **{report.composite:.1f}** |", ""]

    if report.top_fixes:
        lines += ["## Top 5 fixes", ""]
        for f in report.top_fixes:
            lines.append(f"1. **{f.message}** — {f.fix}")
        lines.append("")

    for gate in (Gate.PARSER, Gate.RECRUITER, Gate.MANAGER):
        items = report.by_gate(gate)
        title, note = GATE_TITLES[gate]
        lines += [f"## {title} ({len(items)})", "", f"_{note}_", ""]
        if not items:
            lines += ["Nothing found.", ""]
            continue
        for f in items:
            cost = "advice" if f.advice_only else f"−{f.points:.1f}"
            lines.append(
                f"- `{f.locator or 'document'}` **{f.rule_id}** "
                f"[{f.severity.value}, {cost}] {f.message}"
            )
            if f.evidence and f.evidence not in ("document", "header"):
                lines.append(f"  > {f.evidence}")
            if f.fix:
                lines.append(f"  → {f.fix}")
        lines.append("")

    if report.rewrites:
        lines += ["## Suggested rewrites", "",
                  "_Proposals, not changes. `[add: …]` marks a figure you must supply._", ""]
        for r in report.rewrites:
            lines += [
                f"**{r.locator}**", "",
                "```diff",
                f"- {r.original}",
                f"+ {r.rewritten}",
                "```",
            ]
            if r.what_changed:
                lines.append(f"_{r.what_changed}_")
            lines.append("")

    return "\n".join(lines)


def to_pdf(report: Report) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=LETTER,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        topMargin=0.8 * inch, bottomMargin=0.8 * inch,
        title="Resume diagnostics", author="resume.diagnostics",
    )
    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold",
                        fontSize=17, textColor=INK, spaceAfter=2, leading=20)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold",
                        fontSize=11.5, textColor=INK, spaceBefore=14, spaceAfter=1)
    body = ParagraphStyle("body", parent=base["BodyText"], fontName="Times-Roman",
                          fontSize=9.5, leading=13, textColor=INK)
    soft = ParagraphStyle("soft", parent=body, textColor=SOFT, fontSize=8.5, leading=11)
    diag = ParagraphStyle("diag", parent=body, fontName="Courier", fontSize=7.4,
                          textColor=SOFT, leading=9)
    quote = ParagraphStyle("quote", parent=body, fontName="Courier", fontSize=7.6,
                           leftIndent=10, textColor=INK, leading=10,
                           spaceBefore=2, spaceAfter=2)
    fix = ParagraphStyle("fix", parent=body, fontSize=9, leftIndent=10, textColor=INK)
    big = ParagraphStyle("big", parent=body, fontName="Helvetica-Bold", fontSize=26,
                         textColor=INK, alignment=TA_RIGHT, leading=28)

    story: list = [Paragraph("Resume diagnostics", h1),
                   Paragraph("AI Engineer &middot; mid-level", soft),
                   HRFlowable(width="100%", color=INK, thickness=1.4, spaceBefore=6, spaceAfter=10)]

    # Ledger: the score as a derivation, same as on screen.
    rows = [["Starting score", "100"]]
    for row in report.ledger:
        rows.append([_escape(row.label)[:78], f"{row.points:+.1f}"])
    rows.append(["Composite", f"{report.composite:.1f}"])
    table = Table(rows, colWidths=[4.6 * inch, 1.1 * inch], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Courier", 7.6),
        ("FONT", (0, -1), (-1, -1), "Courier-Bold", 9),
        ("TEXTCOLOR", (1, 1), (1, -2), FLAG),
        ("TEXTCOLOR", (0, 0), (-1, 0), SOFT),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, RULE),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, INK),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story += [Paragraph("SCORE DERIVATION", diag), Spacer(1, 4), table, Spacer(1, 8)]

    summary = Table(
        [[Paragraph(f"grade {report.grade} &nbsp; parser gate {report.parser_subscore:.0f} "
                    f"&nbsp; human gate {report.human_subscore:.0f}", soft),
          Paragraph(f"{report.composite:.0f}", big)]],
        colWidths=[4.2 * inch, 1.5 * inch], hAlign="LEFT",
    )
    summary.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    story += [summary, Spacer(1, 2), Paragraph(CAVEAT, soft), Spacer(1, 6)]

    if report.notes:
        story.append(Paragraph("Run notes", h2))
        for note in report.notes:
            story.append(Paragraph(f"&bull; {_escape(note)}", soft))

    if report.top_fixes:
        story.append(Paragraph("Top 5 fixes", h2))
        for index, f in enumerate(report.top_fixes, 1):
            story.append(Paragraph(
                f"<b>{index}. {_escape(f.message)}</b> &nbsp;{_escape(f.fix)}", body))
            story.append(Spacer(1, 3))

    for gate in (Gate.PARSER, Gate.RECRUITER, Gate.MANAGER):
        items = report.by_gate(gate)
        title, note = GATE_TITLES[gate]
        story.append(Paragraph(f"{title} ({len(items)})", h2))
        story.append(Paragraph(_escape(note), soft))
        story.append(Spacer(1, 4))
        if not items:
            story.append(Paragraph("Nothing found.", soft))
            continue
        for f in items:
            cost = "advice" if f.advice_only else f"&minus;{f.points:.1f}"
            block = [Paragraph(
                f"{_escape(f.locator or 'document')} &nbsp; {_escape(f.rule_id)} &nbsp; "
                f"[{f.severity.value}, {cost}]", diag),
                Paragraph(_escape(f.message), body)]
            if f.evidence and f.evidence not in ("document", "header"):
                block.append(Paragraph(_escape(f.evidence)[:400], quote))
            if f.fix:
                block.append(Paragraph(f"&rarr; {_escape(f.fix)}", fix))
            block.append(Spacer(1, 6))
            story.append(KeepTogether(block))

    if report.rewrites:
        story.append(PageBreak())
        story.append(Paragraph("Suggested rewrites", h2))
        story.append(Paragraph(
            "Proposals, not changes. [add: …] marks a figure you must supply.", soft))
        story.append(Spacer(1, 6))
        for r in report.rewrites:
            del_style = ParagraphStyle("del", parent=quote, textColor=FLAG)
            add_style = ParagraphStyle("add", parent=quote, textColor=KEEP)
            block = [
                Paragraph(_escape(r.locator), diag),
                Paragraph("- " + _escape(r.original), del_style),
                Paragraph("+ " + _escape(r.rewritten), add_style),
            ]
            if r.what_changed:
                block.append(Paragraph(_escape(r.what_changed), soft))
            block.append(Spacer(1, 8))
            story.append(KeepTogether(block))

    # Blank the library's own producer/creator strings. Nothing about the tooling
    # belongs in a file the candidate may hand to someone else.
    def _clean(canvas, _doc):
        canvas.setCreator("")
        canvas.setProducer("")

    doc.build(story, onFirstPage=_clean, onLaterPages=_clean)
    return buffer.getvalue()
