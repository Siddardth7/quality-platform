"""PDF -> page-level text extraction (M4-2b, #329).

The PDF counterpart to :mod:`quality_database_app.segment`: it produces the same
:class:`~quality_database_app.segment.Segment` shape, so everything downstream of
extraction (``pipeline.build_records`` and M4-3's chunking) is format-agnostic.

Three deliberate narrowings, all SME-locked in #329:

**One Segment per page, never per heading.** Raw extracted PDF text carries no Markdown
structure, so there is no heading boundary to split on and ``clause`` is always ``None``.
Inventing a "the first line of a page is a heading" heuristic would be a guess this
pipeline cannot verify — the same reasoning that keeps cleaning format-only (RULE 4).

**Page numbers are real, not heuristic.** ``page`` is pypdf's own page index, 1-indexed
so it reads the way a citation does. This is strictly more reliable than the Markdown
path's footer-marker regex table (RULE 2/3), which infers page breaks from the text.

**Text layer only; no OCR.** ``pypdf`` reads an embedded text layer and nothing else. The
five image-only scans in the ledger extract to zero characters; the pipeline skips and
logs them rather than emitting an empty row, and OCR for them is follow-up issue #335.
Extraction never touches ``extraction_quality`` — confidence still comes solely from the
SME-reviewed ledger (RULE 1).
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from quality_database_app.segment import Segment, _normalize


def extract(path: Path) -> list[Segment]:
    """One :class:`Segment` per PDF page that has extractable text.

    ``clause`` is always ``None``; ``page`` is the 1-indexed page number. A page whose
    text normalizes to empty contributes no segment, mirroring ``segment.segment()``'s
    empty-body rule — a mixed text/image document still yields its readable pages.

    Deterministic: the same file yields the same list on every run.

    Raises
    ------
    OSError
        If the file cannot be read *or* pypdf cannot parse it (corrupt, encrypted,
        truncated). Wrapping the pypdf error keeps ``pipeline.run()``'s single
        skip-and-log path for unreadable sources, rather than growing a second one.
    """
    try:
        reader = PdfReader(path)
        pages = [page.extract_text() for page in reader.pages]
    except PyPdfError as exc:
        raise OSError(f"not a readable PDF: {exc}") from exc

    segments = []
    for number, text in enumerate(pages, start=1):
        body = _normalize(text.splitlines())
        if body:
            segments.append(Segment(clause=None, page=number, text=body))
    return segments
