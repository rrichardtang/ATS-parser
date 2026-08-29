"""PDF -> text plus the layout facts that decide whether an ATS can read it.

Geometry is the point of this module. Everything here is checked against word and
character boxes rather than inferred from the text, because "will a parser read
this" is a question about the page, not the prose.
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

import pdfplumber

# Fraction of page height treated as header/footer band.
EDGE_BAND = 0.06
# Below this many characters a page has no usable text layer.
MIN_CHARS = 40
# A gap this wide (as a fraction of page width) between x-clusters reads as a gutter.
GUTTER_FRACTION = 0.06


@dataclass
class Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    page: int

    @property
    def x_mid(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass
class ExtractedDoc:
    text: str = ""
    pages: list[str] = field(default_factory=list)
    words: list[Word] = field(default_factory=list)
    page_count: int = 0
    page_sizes: list[tuple[float, float]] = field(default_factory=list)
    has_text_layer: bool = True
    multi_column_pages: list[int] = field(default_factory=list)
    table_pages: list[int] = field(default_factory=list)
    image_pages: list[int] = field(default_factory=list)
    edge_band_text: list[str] = field(default_factory=list)
    hidden_text: list[str] = field(default_factory=list)
    font_names: set[str] = field(default_factory=set)
    exotic_bullets: set[str] = field(default_factory=set)
    error: str = ""

    def words_on(self, page: int) -> list[Word]:
        return [w for w in self.words if w.page == page]


class ExtractionError(Exception):
    """Raised for a file we cannot open at all -- encrypted, corrupt, not a PDF."""


def _is_near_white(color: object) -> bool:
    """True when a fill colour is white or near-white on a white page.

    pdfplumber reports colour as a scalar (grey), a 3-tuple (RGB) or 4-tuple (CMYK).
    """
    if color is None:
        return False
    if isinstance(color, (int, float)):
        return float(color) > 0.92
    if isinstance(color, (list, tuple)) and color:
        values = [float(c) for c in color if isinstance(c, (int, float))]
        if not values:
            return False
        if len(values) == 4:  # CMYK: all-zero ink is white
            return all(v < 0.06 for v in values)
        return all(v > 0.92 for v in values)
    return False


def _detect_gutter(words: list[Word], page_width: float) -> bool:
    """Two dense x-clusters with a clear vertical gutter between them.

    Sorting word midpoints and looking for a wide gap is enough: a genuine two-column
    layout leaves a band no word crosses, while a single column does not.
    """
    if len(words) < 40:
        return False
    mids = sorted(w.x_mid for w in words)
    threshold = page_width * GUTTER_FRACTION
    best_gap, best_at = 0.0, 0.0
    for left, right in zip(mids, mids[1:]):
        gap = right - left
        if gap > best_gap:
            best_gap, best_at = gap, left
    if best_gap < threshold:
        return False
    # Both sides must hold real content, else it is a wide margin, not a column.
    left_count = sum(1 for m in mids if m <= best_at)
    right_count = len(mids) - left_count
    if min(left_count, right_count) < len(mids) * 0.2:
        return False
    # And no word may straddle the gutter -- a full-width heading would.
    gutter_lo, gutter_hi = best_at, best_at + best_gap
    straddlers = sum(1 for w in words if w.x0 < gutter_lo and w.x1 > gutter_hi)
    return straddlers <= 1


def extract(path: str) -> ExtractedDoc:
    doc = ExtractedDoc()
    try:
        pdf = pdfplumber.open(path)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as a clean message
        raise ExtractionError(str(exc)) from exc

    with pdf:
        doc.page_count = len(pdf.pages)
        for index, page in enumerate(pdf.pages):
            width, height = float(page.width), float(page.height)
            doc.page_sizes.append((width, height))
            page_text = page.extract_text() or ""
            doc.pages.append(page_text)

            for w in page.extract_words(extra_attrs=["fontname", "size"]) or []:
                doc.words.append(
                    Word(
                        text=w["text"],
                        x0=float(w["x0"]),
                        x1=float(w["x1"]),
                        top=float(w["top"]),
                        bottom=float(w["bottom"]),
                        page=index,
                    )
                )
                if w.get("fontname"):
                    doc.font_names.add(str(w["fontname"]))

            if _detect_gutter(doc.words_on(index), width):
                doc.multi_column_pages.append(index)

            try:
                if page.find_tables():
                    doc.table_pages.append(index)
            except Exception:  # noqa: BLE001 - table finder is best-effort
                pass

            if page.images:
                doc.image_pages.append(index)

            top_limit, bottom_limit = height * EDGE_BAND, height * (1 - EDGE_BAND)
            for w in doc.words_on(index):
                if w.bottom < top_limit or w.top > bottom_limit:
                    doc.edge_band_text.append(w.text)

            doc.hidden_text.extend(_hidden_spans(page))
            doc.exotic_bullets.update(_exotic_bullets(page_text))

    for word in doc.words:
        word.text = normalize_text(word.text)
    doc.words = [w for w in doc.words if w.text]
    doc.pages = [normalize_text(p) for p in doc.pages]
    doc.text = "\n".join(doc.pages)
    doc.has_text_layer = len(doc.text.strip()) >= MIN_CHARS
    return doc


def _hidden_spans(page) -> list[str]:
    """Characters invisible to a human but read by a parser.

    White-on-white and sub-2pt text is how keyword injection is done. Workday,
    Greenhouse and Lever detect it and can attach a fraud flag to the candidate
    record, so this is the most severe thing the tool can find.
    """
    spans: list[str] = []
    buffer: list[str] = []
    for char in page.chars:
        invisible = _is_near_white(char.get("non_stroking_color")) or float(
            char.get("size", 12) or 12
        ) < 2.0
        if invisible:
            buffer.append(char.get("text", ""))
        elif buffer:
            text = "".join(buffer).strip()
            if len(text) > 3:
                spans.append(text)
            buffer = []
    if buffer:
        text = "".join(buffer).strip()
        if len(text) > 3:
            spans.append(text)
    return spans


# pdfplumber emits "(cid:N)" when a font does not map a glyph. Real resumes hit this
# constantly -- Helvetica has no bullet in its standard encoding, so a plain "•"
# round-trips as (cid:127). Left alone it silently destroys bullet parsing.
CID_RE = re.compile(r"\(cid:(\d+)\)")
_CID_BULLETS = {127, 128, 129, 149, 183}


def normalize_text(text: str) -> str:
    """Map unresolved glyph codes back to characters we can reason about."""

    def replace(match: re.Match[str]) -> str:
        code = int(match.group(1))
        if code in _CID_BULLETS:
            return "\u2022"
        # Latin-1 range codes usually round-trip directly.
        if 32 <= code < 127:
            return chr(code)
        return ""

    cleaned = CID_RE.sub(replace, text)
    return "\n".join(line.rstrip() for line in cleaned.splitlines())


STANDARD_BULLETS = {"•", "-", "–", "*", "‣", "·"}


def _exotic_bullets(text: str) -> set[str]:
    found: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        first = stripped[0]
        if not first.isalnum() and first not in STANDARD_BULLETS and not first.isascii():
            found.add(first)
    return found


def font_sprawl(doc: ExtractedDoc) -> int:
    """Distinct font families, ignoring subset prefixes and style suffixes."""
    families = set()
    for name in doc.font_names:
        base = name.split("+")[-1]
        base = base.split("-")[0].split(",")[0]
        families.add(base.lower())
    return len(families)


def line_spacing_stats(doc: ExtractedDoc) -> float:
    tops = sorted({round(w.top, 1) for w in doc.words if w.page == 0})
    gaps = [b - a for a, b in zip(tops, tops[1:]) if 0 < b - a < 60]
    return statistics.median(gaps) if gaps else 0.0
