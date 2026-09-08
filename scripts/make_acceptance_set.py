"""Renders the acceptance set to PDFs, and freezes what it renders.

The documents are committed as text and the PDFs are generated, for the reason
`tests/make_fixtures.py` gives: the inputs stay readable and reviewable in the diff.
Unlike the band probes, these are rendered rather than handed to the judge as text --
09 runs the whole pipeline, parser included, and a real resume arrives as a PDF.

Layout varies per document, deterministically from its own hash: font, body size and
margins. Real resumes do not share one template, and a set that did would let a judge
learn the template instead of reading the document. Nothing in the variation is a
parser defect -- single column, real text layer, no injection. The seven fixtures are
where extraction failures are tested and they stay there.

**Freezing.** A document that changes after a judge has read it silently invalidates
every number measured on it, and this set exists to be measured twice (09, and again
whenever the rubric moves). `manifest.json` records a hash per document; `--verify`
is what the test suite runs. Editing a document is not forbidden so much as it is a
new document: change the text, re-freeze, and say so in acceptance-set.md.

    .venv/bin/python scripts/make_acceptance_set.py             # render the PDFs
    .venv/bin/python scripts/make_acceptance_set.py --freeze    # rewrite the manifest
    .venv/bin/python scripts/make_acceptance_set.py --verify    # check it
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SET_DIR = ROOT / "corpus" / "resumes" / "synthetic"
OUT_DIR = ROOT / "corpus" / "resumes" / "rendered"
MANIFEST = ROOT / "corpus" / "resumes" / "manifest.json"
BRIEFS = ROOT / "corpus" / "resumes" / "briefs.json"

WIDTH, HEIGHT = LETTER
FONTS = [("Helvetica", "Helvetica-Bold"), ("Times-Roman", "Times-Bold")]
SIZES = [9.0, 9.5, 10.0, 10.5]
MARGINS = [54, 60, 66, 72]

SECTION_WORDS = {
    "summary", "profile", "objective", "experience", "work experience", "projects",
    "education", "skills", "publications", "certifications", "interests",
    "volunteering", "awards",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def layout(name: str) -> dict:
    """Deterministic per document, so a re-render is byte-stable for the same text."""
    seed = int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:8], 16)
    body, bold = FONTS[seed % len(FONTS)]
    return {
        "body": body,
        "bold": bold,
        "size": SIZES[(seed // 7) % len(SIZES)],
        "margin": MARGINS[(seed // 53) % len(MARGINS)],
    }


def _is_heading(line: str) -> bool:
    stripped = line.strip().rstrip(":")
    return bool(stripped) and stripped.lower() in SECTION_WORDS


def render(name: str, text: str, out: Path) -> None:
    style = layout(name)
    c = canvas.Canvas(str(out), pagesize=LETTER)
    margin, size = style["margin"], style["size"]
    leading = size * 1.45
    y = HEIGHT - margin
    first = True
    for line in text.splitlines():
        if y < margin + leading:
            c.showPage()
            y = HEIGHT - margin
        stripped = line.rstrip()
        if not stripped:
            y -= leading * 0.6
            continue
        if first:
            c.setFont(style["bold"], size + 6)
            c.drawString(margin, y, stripped)
            y -= leading * 1.6
            first = False
            continue
        if _is_heading(stripped):
            y -= leading * 0.4
            c.setFont(style["bold"], size + 0.5)
            c.drawString(margin, y, stripped.upper())
            c.setLineWidth(0.5)
            c.line(margin, y - 3, WIDTH - margin, y - 3)
            y -= leading * 1.2
            continue
        c.setFont(style["body"], size)
        indent = margin + (10 if stripped.startswith(("•", "  ")) else 0)
        c.drawString(indent, y, stripped.lstrip())
        y -= leading
    c.save()


def build_all() -> dict[str, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    made: dict[str, Path] = {}
    for source in sorted(SET_DIR.glob("*.txt")):
        out = OUT_DIR / f"{source.stem}.pdf"
        render(source.stem, source.read_text(encoding="utf-8"), out)
        made[source.stem] = out
    return made


def manifest() -> dict:
    briefs = json.loads(BRIEFS.read_text(encoding="utf-8"))
    by_id = {b["id"]: b for b in briefs["briefs"]}
    entries = []
    for source in sorted(SET_DIR.glob("*.txt")):
        brief_id = source.stem.split("-", 1)[0]
        brief = by_id.get(brief_id)
        entries.append({
            "id": source.stem,
            "brief": brief_id,
            "sha256": digest(source),
            "provenance": "synthetic-from-brief",
            "on_track": brief["on_track"] if brief else None,
            "committed": True,
        })
    return {
        "frozen": date.today().isoformat(),
        "seed": briefs["seed"],
        "work_pool_digest": briefs["work_pool"]["digest"],
        "documents": entries,
        "note": (
            "Every document here is invented: no real person, employer, address or "
            "contact detail, and no text taken from a real resume. Real resumes are "
            "tier 2 and are never committed -- see corpus/resumes/README.md."
        ),
    }


def verify() -> int:
    if not MANIFEST.exists():
        print("no manifest; run --freeze")
        return 1
    recorded = json.loads(MANIFEST.read_text(encoding="utf-8"))
    known = {e["id"]: e["sha256"] for e in recorded["documents"]}
    seen = {p.stem: digest(p) for p in sorted(SET_DIR.glob("*.txt"))}
    problems = []
    for name, sha in seen.items():
        if name not in known:
            problems.append(f"{name}: not in the manifest")
        elif known[name] != sha:
            problems.append(f"{name}: changed since it was frozen")
    for name in known:
        if name not in seen:
            problems.append(f"{name}: in the manifest, missing from the set")
    for line in problems:
        print(f"  - {line}")
    if problems:
        print(f"{len(problems)} problem(s); a changed document is a new document -- "
              "re-freeze and say so in acceptance-set.md")
        return 1
    print(f"{len(seen)} documents match the manifest frozen {recorded['frozen']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--freeze", action="store_true", help="rewrite manifest.json")
    ap.add_argument("--verify", action="store_true", help="check the manifest")
    args = ap.parse_args()

    if args.verify:
        return verify()
    if args.freeze:
        MANIFEST.write_text(json.dumps(manifest(), indent=2) + "\n", encoding="utf-8")
        print(f"froze {len(list(SET_DIR.glob('*.txt')))} documents -> "
              f"{MANIFEST.relative_to(ROOT)}")
        return 0
    made = build_all()
    print(f"{len(made)} PDFs -> {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
