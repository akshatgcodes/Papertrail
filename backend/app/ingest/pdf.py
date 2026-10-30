"""Read a PDF into passages that remember where they are on the page.

PyMuPDF gives text in blocks (roughly paragraphs) with bounding boxes. Chunks are built
from whole blocks on one page and stop at headings, so a source can be shown by
highlighting exactly those blocks. A block longer than a chunk is split at sentence
boundaries (`split_long`), and each piece highlights its whole block.
"""

import re
from dataclasses import dataclass, field

import pymupdf

from app.ingest.text import split_long

CHUNK_CHARS = 1000
MIN_CHARS = 30  # page numbers, running heads, stray labels


class PdfError(Exception):
    pass


@dataclass
class Passage:
    page: int
    text: str
    rects: list[list[float]] = field(default_factory=list)


def clean(text: str) -> str:
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # re-join words hyphenated across lines
    return re.sub(r"\s+", " ", text).strip()


def open_pdf(data: bytes) -> pymupdf.Document:
    if not data.startswith(b"%PDF"):
        raise PdfError("That file isn't a PDF")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:
        raise PdfError("The PDF couldn't be opened; it may be damaged") from e
    if doc.needs_pass:
        raise PdfError("The PDF is password-protected")
    return doc


def title_of(doc: pymupdf.Document, filename: str) -> str:
    meta = (doc.metadata or {}).get("title", "").strip()
    return meta or re.sub(r"\.pdf$", "", filename, flags=re.I)


def passages(doc: pymupdf.Document) -> list[Passage]:
    out: list[Passage] = []
    for page in doc:
        current: Passage | None = None
        for x0, y0, x1, y1, raw, _no, kind in page.get_text("blocks", sort=True):
            if kind != 0:  # image block
                continue
            text = clean(raw)
            if len(text) < MIN_CHARS:
                # Too short to keep, but usually a heading: end the passage here so
                # one passage doesn't straddle two sections
                if current:
                    out.append(current)
                    current = None
                continue
            rect = [round(v, 1) for v in (x0, y0, x1, y1)]
            if len(text) > CHUNK_CHARS:
                if current:
                    out.append(current)
                    current = None
                out.extend(
                    Passage(page.number, piece, [rect]) for piece in split_long(text, CHUNK_CHARS)
                )
                continue
            if current and len(current.text) + 1 + len(text) > CHUNK_CHARS:
                out.append(current)
                current = None
            if current is None:
                current = Passage(page.number, text, [rect])
            else:
                current.text += " " + text
                current.rects.append(rect)
        if current:
            out.append(current)
    return out


def render_page(data: bytes, page_no: int, rects: list[list[float]], zoom: float = 1.6) -> bytes:
    """PNG of one page with the given rectangles highlighted."""
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        page = doc[page_no]
        for r in rects:
            box = pymupdf.Rect(*r) + (-2, -2, 2, 2)
            page.draw_rect(
                box, color=(0.95, 0.65, 0.1), fill=(1, 0.85, 0.2), fill_opacity=0.35, width=0.8
            )
        return page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")
