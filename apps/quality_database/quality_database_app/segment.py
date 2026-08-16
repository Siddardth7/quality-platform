"""Split an extracted Markdown source into locatable segments (M4-2, #283).

Two design points, both grounded in the actual on-machine files rather than assumed:

**Page markers are source-specific.** The FMEA & VDA handbook `.md` marks page breaks
with a footer line ``- N -`` (165 occurrences); the MSA manual uses a bare-digit line
(``1``, ``2``, ...). There is no universal regex, so the pattern is a table keyed by
``source_id`` — a config table is the ceiling here, not a plugin architecture.

**A marker is a footer**, i.e. it closes the page whose text precedes it. A marker is
accepted only when its number exceeds the current page, so a stray numeric line (a
table cell of ``1``, say) cannot fabricate a page number or reset the count. Text
after the last marker has no determinable page and gets ``None``.

Segmentation itself is the standard heading-boundary split: a segment runs from one
Markdown heading to the next, carrying that heading as its clause. Text before the
first heading (copyright boilerplate) has ``clause=None``.

Cleaning is **format-only and never content-repairing**: trailing whitespace stripped,
runs of blank lines collapsed, page-marker lines removed. Nothing inside a line is
touched, so OCR damage (the #256 ``Hih``/``g`` cell-merge) survives verbatim — the
pipeline must not "fix" what it cannot verify.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

HEADING = re.compile(r"^#{1,6}\s+(.*\S)\s*$")

#: Page-marker pattern per ``source_id``; group 1 is the page number. A source with no
#: entry here segments fine and simply gets ``page=None`` on every record.
PAGE_MARKERS: dict[str, re.Pattern[str]] = {
    "fmea-vda-2019": re.compile(r"^-\s(\d+)\s-\s*$"),
    "msa-4th": re.compile(r"^(\d+)\s*$"),
}


@dataclass(frozen=True)
class Segment:
    """One heading-delimited chunk: where it sits, and its cleaned text."""

    clause: str | None
    page: int | None
    text: str


def page_marker_for(source_id: str) -> re.Pattern[str] | None:
    """The page-marker pattern for ``source_id``, or ``None`` if the source has none."""
    return PAGE_MARKERS.get(source_id)


def _page_by_line(lines: list[str], pattern: re.Pattern[str] | None) -> list[int | None]:
    """Page number for each line index, from footer markers; ``None`` where unknown."""
    pages: list[int | None] = [None] * len(lines)
    if pattern is None:
        return pages
    current = 0
    start = 0
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match is None:
            continue
        number = int(match.group(1))
        if number <= current:  # out-of-order digit line: not a page footer, ignore it
            continue
        for filled in range(start, index + 1):
            pages[filled] = number
        current = number
        start = index + 1
    return pages


def _normalize(lines: list[str]) -> str:
    """Format-only cleanup: strip trailing whitespace, collapse blank runs, trim ends."""
    cleaned: list[str] = []
    for raw in lines:
        line = raw.rstrip()
        if not line and (not cleaned or not cleaned[-1]):
            continue
        cleaned.append(line)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return "\n".join(cleaned)


def segment(text: str, page_pattern: re.Pattern[str] | None) -> list[Segment]:
    """Split ``text`` into heading-delimited segments.

    Deterministic: the same text and pattern yield the same list on every run. A
    segment whose text normalizes to empty (a heading-less, blank prefix) is dropped —
    an empty record would carry no content and no clause.
    """
    lines = text.splitlines()
    pages = _page_by_line(lines, page_pattern)

    segments: list[Segment] = []
    clause: str | None = None
    buffer: list[str] = []
    anchor: int | None = None

    def flush() -> None:
        body = _normalize(buffer)
        if body:
            segments.append(Segment(clause=clause, page=None if anchor is None else pages[anchor], text=body))

    for index, line in enumerate(lines):
        if page_pattern is not None and page_pattern.match(line):
            continue  # an extraction artefact, not content
        heading = HEADING.match(line)
        if heading:
            flush()
            clause = heading.group(1)
            buffer = [line]
            anchor = index
            continue
        buffer.append(line)
        if anchor is None and line.strip():
            anchor = index
    flush()
    return segments
