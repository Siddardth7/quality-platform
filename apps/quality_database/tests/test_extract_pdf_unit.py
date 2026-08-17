"""PDF text-layer extraction (M4-2b, #329), on synthetic PDFs only — CI-safe.

Pins the three narrowings the extractor is allowed to make: one segment per page with a
real 1-indexed page number, ``clause`` always ``None``, and a page with no usable text
contributing nothing. The image-only case (every page blank) is what the ledger's five
un-OCR'd scans look like here, and an unparseable file must surface as ``OSError`` so
``pipeline.run()`` skips it through its existing path.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from quality_database_app.extract_pdf import extract

PdfBuilder = Callable[[Sequence[str]], bytes]


def _write(tmp_path: Path, builder: PdfBuilder, pages: Sequence[str]) -> Path:
    path = tmp_path / "source.pdf"
    path.write_bytes(builder(pages))
    return path


def test_extract_gives_one_segment_per_page_with_1_indexed_pages(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    path = _write(tmp_path, synthetic_pdf, ["Section 1 opening text", "Section 2 body text"])
    segments = extract(path)

    assert [s.page for s in segments] == [1, 2]
    assert [s.clause for s in segments] == [None, None]  # no heading structure in raw PDF text
    assert "Section 1 opening text" in segments[0].text
    assert "Section 2 body text" in segments[1].text


def test_extract_drops_a_page_with_no_usable_text_and_keeps_the_rest(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    # Page 2 is whitespace-only: a mixed text/image document still yields its readable pages.
    path = _write(tmp_path, synthetic_pdf, ["First page text", "   ", "Third page text"])
    segments = extract(path)

    assert [s.page for s in segments] == [1, 3]


def test_extract_returns_nothing_for_an_image_only_pdf(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    # Every page blank — how the ledger's five un-OCR'd scans read (#335).
    path = _write(tmp_path, synthetic_pdf, ["", ""])
    assert extract(path) == []


def test_extract_is_deterministic(tmp_path: Path, synthetic_pdf: PdfBuilder) -> None:
    path = _write(tmp_path, synthetic_pdf, ["Page one text", "Page two text"])
    assert extract(path) == extract(path)


def test_extract_raises_oserror_for_a_file_that_is_not_a_pdf(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"this is not a PDF at all\n")
    with pytest.raises(OSError, match="not a readable PDF"):
        extract(path)


def test_extract_raises_oserror_for_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        extract(tmp_path / "gone.pdf")
