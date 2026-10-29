"""Plain text and Markdown into passages that know their section and their exact place
in the text, so a source can be highlighted where it came from.

Passages are built from whole paragraphs (split on blank lines) inside one section, up to
CHUNK_CHARS. A Markdown heading always ends a passage, so one passage never mixes two
sections. A paragraph longer than CHUNK_CHARS is split at sentence ends, and the next
piece repeats the previous piece's last sentence if it's short, to keep some context.
"""

import re
from dataclasses import dataclass

from app.config import settings

HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t#]*$")
SENTENCE_END = re.compile(r"(?<=[.!?…])[\"')\]]*\s+")
OVERLAP_MAX = 200


@dataclass
class Passage:
    start: int
    end: int
    heading: str
    text: str


def split_spans(text: str, limit: int, offset: int = 0) -> list[tuple[int, int]]:
    """(start, end) spans of at most `limit` characters, cut at sentence ends where
    possible, else at whitespace, else hard."""
    sentences, pos = [], 0
    for m in SENTENCE_END.finditer(text):
        sentences.append((pos, m.start()))
        pos = m.end()
    if pos < len(text):
        sentences.append((pos, len(text)))

    # Sentences longer than the limit are cut at the last space before it
    pieces: list[tuple[int, int]] = []
    for s, e in sentences:
        while e - s > limit:
            cut = text.rfind(" ", s, s + limit)
            cut = cut if cut > s else s + limit
            pieces.append((s, cut))
            s = cut + 1 if text[cut : cut + 1] == " " else cut
        if e > s:
            pieces.append((s, e))

    spans: list[tuple[int, int]] = []
    cur_s = cur_e = None
    last: tuple[int, int] | None = None
    for s, e in pieces:
        if cur_s is None:
            cur_s, cur_e = s, e
        elif e - cur_s <= limit:
            cur_e = e
        else:
            spans.append((cur_s, cur_e))
            # Carry the last sentence over when it's short
            if last and last[1] - last[0] <= OVERLAP_MAX and e - last[0] <= limit:
                cur_s, cur_e = last[0], e
            else:
                cur_s, cur_e = s, e
        last = (s, e)
    if cur_s is not None:
        spans.append((cur_s, cur_e))
    return [(a + offset, b + offset) for a, b in spans]


def split_long(text: str, limit: int) -> list[str]:
    return [text[a:b] for a, b in split_spans(text, limit)]


def passages(content: str, markdown: bool = True, limit: int | None = None) -> list[Passage]:
    limit = limit or settings.chunk_chars
    out: list[Passage] = []
    path: list[str] = []  # heading stack

    def heading() -> str:
        return " › ".join(path)

    # Paragraphs: runs of non-blank lines, with their offsets. Headings stand alone
    paragraphs: list[tuple[int, int, str | None]] = []  # (start, end, heading text or None)
    pos = 0
    para_start: int | None = None
    for line in content.splitlines(keepends=True):
        stripped = line.strip()
        m = HEADING.match(stripped) if markdown else None
        if not stripped or m:
            if para_start is not None:
                paragraphs.append((para_start, pos, None))
                para_start = None
            if m:
                paragraphs.append((pos, pos + len(line), f"{len(m.group(1))}:{m.group(2)}"))
        elif para_start is None:
            para_start = pos
        pos += len(line)
    if para_start is not None:
        paragraphs.append((para_start, pos, None))

    cur: Passage | None = None

    def flush() -> None:
        nonlocal cur
        if cur:
            out.append(cur)
            cur = None

    for start, end, head in paragraphs:
        if head is not None:
            flush()
            level, title = head.split(":", 1)
            del path[int(level) - 1 :]
            path.extend([""] * (int(level) - 1 - len(path)))
            path.append(title.strip())
            path[:] = [p for p in path if p]
            continue
        # Trim trailing whitespace so the highlight ends on the last character
        text = content[start:end].rstrip()
        end = start + len(text)
        if not text.strip():
            continue
        if end - start > limit:
            flush()
            for a, b in split_spans(text, limit, offset=start):
                out.append(Passage(a, b, heading(), content[a:b]))
            continue
        if cur and end - cur.start > limit:
            flush()
        if cur is None:
            cur = Passage(start, end, heading(), text)
        else:
            cur.end = end
            cur.text = content[cur.start : end]
    flush()
    return out


def markdown_title(content: str) -> str | None:
    for line in content.splitlines():
        m = HEADING.match(line.strip())
        if m and len(m.group(1)) == 1:
            return m.group(2).strip()
    return None
