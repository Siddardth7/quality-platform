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

**Text layer first, OCR only as a fallback (#335).** ``pypdf`` reads an embedded text
layer and nothing else, so an image-only scan extracts to zero characters. A page whose
text layer is below :data:`MIN_WORDS` is retried through the
:class:`~quality_database_app.ocr.Ocr` seam; the default ``NullOcr`` recognizes nothing,
so the CI path is unchanged and needs no system binary. A real backend lives in
``ocr_tesseract.py`` behind the optional ``ocr`` extra.
Extraction never touches ``extraction_quality`` — confidence still comes solely from the
SME-reviewed ledger (RULE 1), whatever produced the text.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from quality_database_app.ocr import NullOcr, Ocr
from quality_database_app.segment import Segment, _normalize

#: A page needs this many words to count as content (RULE 15). Evidence: the three junk
#: pages the ledger's two junk-text-layer scans leak run 3-24 words, while the shortest
#: real page found (western-electric-1956 p3, the 1956 foreword) runs ~120.
#: ponytail: a word-count heuristic with a known ceiling, like segment.py's RULE 2/3 —
#: a longer advert still leaks and a genuinely short real page is still dropped. Upgrade
#: path is per-source calibration, not content classification.
MIN_WORDS = 30


def _is_substantive(body: str) -> bool:
    """Whether ``body`` carries enough words to be worth a record."""
    return len(body.split()) >= MIN_WORDS


def extract(path: Path, ocr: Ocr | None = None) -> list[Segment]:
    """One :class:`Segment` per PDF page carrying at least :data:`MIN_WORDS` words.

    ``clause`` is always ``None``; ``page`` is pypdf's 1-indexed page number — including
    for OCR'd pages, whose *text* comes from ``ocr`` but whose position still comes from
    the document's own page tree (RULE 13).

    ``ocr`` is consulted **only** for a page whose text layer is below threshold, so a
    readable page is never re-recognized; it defaults to
    :class:`~quality_database_app.ocr.NullOcr`, which recovers nothing. A page that is
    below threshold both before and after OCR contributes no segment.

    Deterministic given a deterministic ``ocr``: the same file yields the same list on
    every run.

    Raises
    ------
    OSError
        If the file cannot be read *or* pypdf cannot parse it (corrupt, encrypted,
        truncated). Wrapping the pypdf error keeps ``pipeline.run()``'s single
        skip-and-log path for unreadable sources, rather than growing a second one.
    """
    ocr = NullOcr() if ocr is None else ocr
    try:
        reader = PdfReader(path)
        pages = [page.extract_text() for page in reader.pages]
    except PyPdfError as exc:
        raise OSError(f"not a readable PDF: {exc}") from exc

    segments = []
    for number, text in enumerate(pages, start=1):
        body = _normalize(text.splitlines())
        if not _is_substantive(body):
            body = _normalize(ocr.text_for_page(path, number).splitlines())
        if _is_substantive(body):
            segments.append(Segment(clause=None, page=number, text=body))
    return segments
