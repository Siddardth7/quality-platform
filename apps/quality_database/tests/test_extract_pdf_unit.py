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
from quality_database_app.extract_pdf import MIN_WORDS, extract

PdfBuilder = Callable[[Sequence[str]], bytes]


def _write(tmp_path: Path, builder: PdfBuilder, pages: Sequence[str]) -> Path:
    path = tmp_path / "source.pdf"
    path.write_bytes(builder(pages))
    return path


def _page(prefix: str) -> str:
    """A page of at least `MIN_WORDS` words — anything shorter is junk (#335, RULE 15)."""
    return prefix + " lorem ipsum" * 15


def _words(n: int) -> str:
    """A page of exactly ``n`` space-separated words (for the MIN_WORDS boundary)."""
    return " ".join(["word"] * n)


class _FakeOcr:
    """A hand-written ``Ocr`` double (not ``NullOcr``): returns a fixed string and counts
    every page it is asked for, so a test can prove OCR was (or was not) invoked and that
    its text — not the empty pypdf text — is what reaches the segment (#335, spec §5.3/5.5).
    """

    def __init__(self, text: str = "") -> None:
        self._text = text
        self.calls: list[tuple[Path, int]] = []

    def text_for_page(self, path: Path, page_number: int) -> str:
        self.calls.append((path, page_number))
        return self._text


def test_extract_gives_one_segment_per_page_with_1_indexed_pages(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    path = _write(
        tmp_path, synthetic_pdf, [_page("Section 1 opening text"), _page("Section 2 body text")]
    )
    segments = extract(path)

    assert [s.page for s in segments] == [1, 2]
    assert [s.clause for s in segments] == [None, None]  # no heading structure in raw PDF text
    assert "Section 1 opening text" in segments[0].text
    assert "Section 2 body text" in segments[1].text


def test_extract_drops_a_page_with_no_usable_text_and_keeps_the_rest(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    # Page 2 is whitespace-only: a mixed text/image document still yields its readable pages.
    path = _write(
        tmp_path, synthetic_pdf, [_page("First page text"), "   ", _page("Third page text")]
    )
    segments = extract(path)

    assert [s.page for s in segments] == [1, 3]


def test_extract_returns_nothing_for_an_image_only_pdf(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    # Every page blank — how the ledger's true scans read with the default NullOcr (#335).
    path = _write(tmp_path, synthetic_pdf, ["", ""])
    assert extract(path) == []


def test_extract_is_deterministic(tmp_path: Path, synthetic_pdf: PdfBuilder) -> None:
    path = _write(tmp_path, synthetic_pdf, [_page("Page one text"), _page("Page two text")])
    assert extract(path) == extract(path)


def test_extract_raises_oserror_for_a_file_that_is_not_a_pdf(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"this is not a PDF at all\n")
    with pytest.raises(OSError, match="not a readable PDF"):
        extract(path)


def test_extract_raises_oserror_for_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        extract(tmp_path / "gone.pdf")


# --- #335 word-count threshold + OCR seam (spec §4, §5) -----------------------------


def test_below_threshold_page_with_null_ocr_is_dropped(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    """§5.1 the junk-leak fix: a short page with no OCR backend contributes no segment.
    Negative control: MIN_WORDS = 0 keeps it, this test then fails."""
    path = _write(tmp_path, synthetic_pdf, [_words(MIN_WORDS - 1)])
    assert extract(path) == []


def test_page_at_threshold_is_kept(tmp_path: Path, synthetic_pdf: PdfBuilder) -> None:
    """§5.2 boundary: a page of exactly MIN_WORDS words is content, not junk. This pins
    `>=` against a `>` mutation — a one-word-narrower window would drop it."""
    path = _write(tmp_path, synthetic_pdf, [_words(MIN_WORDS)])
    segments = extract(path)
    assert [s.page for s in segments] == [1]


def test_below_threshold_page_recovered_by_substantive_ocr_carries_ocr_text(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    """§5.3 THE FLAGGED GAP: a below-threshold page whose real Ocr returns substantive
    text becomes a segment carrying the *OCR* text, not the empty pypdf text."""
    ocr = _FakeOcr("recovered " + "scanned word " * MIN_WORDS)
    path = _write(tmp_path, synthetic_pdf, [_words(MIN_WORDS - 1)])
    segments = extract(path, ocr)

    assert [s.page for s in segments] == [1]           # OCR page number is pypdf's (RULE 13)
    assert "recovered" in segments[0].text             # the OCR text reached the segment
    assert "word word" not in segments[0].text         # not the pypdf junk that was replaced
    assert ocr.calls == [(path, 1)]                    # OCR was consulted for the junk page


def test_below_threshold_page_with_below_threshold_ocr_is_dropped(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    """§5.4 a junk page whose OCR is also below threshold (blank scan / noise) -> no
    segment. Negative control: MIN_WORDS = 0 keeps it, this test then fails."""
    ocr = _FakeOcr("only three words")
    path = _write(tmp_path, synthetic_pdf, [_words(MIN_WORDS - 1)])
    assert extract(path, ocr) == []


def test_ocr_is_not_invoked_for_a_substantive_page(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    """§5.5 OCR-fallback-only: a page that clears the threshold on its pypdf text is never
    re-recognized. Western-Electric p3 (real ~120-word foreword) stays a pypdf segment."""
    ocr = _FakeOcr("this OCR text must never appear " + "x " * MIN_WORDS)
    path = _write(tmp_path, synthetic_pdf, [_page("Genuine foreword prose")])
    segments = extract(path, ocr)

    assert ocr.calls == []                                  # fallback never fired
    assert "Genuine foreword prose" in segments[0].text     # kept text is the pypdf text
    assert "must never appear" not in segments[0].text


def test_null_ocr_reproduces_pre_335_image_only_behaviour(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    """§5.6 regression guard: an image-only PDF with the default NullOcr still -> []."""
    path = _write(tmp_path, synthetic_pdf, ["", ""])
    assert extract(path) == []


def test_extract_is_deterministic_with_a_fake_ocr(
    tmp_path: Path, synthetic_pdf: PdfBuilder
) -> None:
    """§5.7 determinism holds given a deterministic Ocr."""
    path = _write(tmp_path, synthetic_pdf, [_words(MIN_WORDS - 1)])
    assert extract(path, _FakeOcr("recovered " + "scanned word " * MIN_WORDS)) == extract(
        path, _FakeOcr("recovered " + "scanned word " * MIN_WORDS)
    )
