"""The OCR seam (M4-2c, #335).

:class:`Ocr` is the only OCR surface ``extract_pdf.py`` / ``pipeline.py`` know about,
the same shape as :class:`~quality_database_app.embed.Embedder`: a Protocol here, a
deterministic offline default here, and the dependency-heavy real backend in a sibling
module (``ocr_tesseract.py``) that CI never imports.

:class:`NullOcr` is the **only OCR CI runs** and the default everywhere: it recognizes
nothing, so a below-threshold page stays dropped and ``extract()`` reproduces its exact
pre-#335 behaviour when no backend is configured. That keeps the gate free of the
system ``tesseract`` binary, which is not a ``pip`` install and which no CI step
installs (RULE 15).

OCR supplies **text only**. Page numbers still come from pypdf's page tree (RULE 13) and
``extraction_quality`` still comes solely from the SME-reviewed ledger (RULE 1) — an OCR
backend must never emit a second, code-derived confidence signal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Ocr(Protocol):
    """Anything that can recognize text on one page of a PDF."""

    def text_for_page(self, path: Path, page_number: int) -> str:
        """OCR text for the 1-indexed page ``page_number`` of ``path``.

        Returns ``""`` when nothing is recognizable — never raises for an unreadable
        page, so a failed recognition is a dropped page, not a failed extraction run.
        """


class NullOcr:
    """The no-op default: no OCR backend configured, so no page is ever recovered."""

    def text_for_page(self, path: Path, page_number: int) -> str:
        return ""
