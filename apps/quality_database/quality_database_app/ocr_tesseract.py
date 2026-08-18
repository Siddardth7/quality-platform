"""Real local OCR backend — optional, hand-run only (M4-2c, #335).

**Not on the CI path and not in the coverage gate**, the same posture as
``embed_fastembed.py`` and the Streamlit ``pages/`` exclusions: it needs the optional
``ocr`` dependency group *and* a system ``tesseract`` binary, neither of which CI
installs. Install it for a real extraction run:

```bash
brew install tesseract          # or: apt-get install tesseract-ocr
uv sync --extra ocr
uv run python -m quality_database_app.ocr_tesseract path/to/scan.pdf 1
```

Rasterization is **PyMuPDF** (``fitz``) rather than ``pdf2image``/poppler: PyMuPDF ships
its own renderer in a pure pip wheel, so the whole stack needs exactly one system binary
(``tesseract``) instead of two. Everything runs on this machine — no page image and no
corpus text ever leaves it, per M4-5 (RULE 14) and the corpus-is-private policy.

Ceiling: OCR output is not bit-for-bit stable across tesseract versions or DPI settings,
which is the other reason this file stays out of the CI determinism-checked path — the
seam (``quality_database_app.ocr.Ocr``) is deterministic given a deterministic backend,
this backend is only deterministic for a fixed tesseract install. Swapping engines
touches this file only.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

#: 300 dpi is tesseract's own documented sweet spot for scanned text; below ~200 its
#: accuracy falls off, above ~400 it costs time for no gain.
DEFAULT_DPI = 300
DEFAULT_LANG = "eng"


class TesseractOcr:
    """`quality_database_app.ocr.Ocr` backed by PyMuPDF rasterization + local tesseract."""

    def __init__(self, dpi: int = DEFAULT_DPI, lang: str = DEFAULT_LANG) -> None:
        try:
            import fitz
            import pytesseract
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "PyMuPDF/pytesseract are not installed. Run `uv sync --extra ocr` (and "
                "install the system `tesseract` binary) for a real OCR run; CI uses "
                "quality_database_app.ocr.NullOcr."
            ) from exc
        self._fitz = fitz
        self._pytesseract = pytesseract
        self._image = Image
        self._dpi = dpi
        self._lang = lang

    def text_for_page(self, path: Path, page_number: int) -> str:
        """Rasterize the 1-indexed page ``page_number`` and recognize it, or ``""``.

        Returns ``""`` for any page that cannot be rendered or recognized, so a bad page
        is a dropped page rather than a failed extraction run — ``extract()`` treats an
        empty result exactly like a blank page.

        ponytail: reopens the document per page. OCR itself costs ~1s a page, so the
        open dominates nothing; batch the open if a whole-book run ever gets hot.
        """
        try:
            with self._fitz.open(path) as document:
                page = document[page_number - 1]
                png = page.get_pixmap(dpi=self._dpi).tobytes("png")
            image = self._image.open(io.BytesIO(png))
            return str(self._pytesseract.image_to_string(image, lang=self._lang))
        except Exception:  # noqa: BLE001 - any render/recognize failure is "no text"
            return ""


def demo() -> None:
    """Hand-run smoke check: OCR one page of a real on-machine scan and print it.

    Not a test and not gated — the corpus is not on CI and neither is tesseract. Run it
    after installing the extra to confirm the whole rasterize -> recognize path works:

    ```bash
    uv run python -m quality_database_app.ocr_tesseract "$CORPUS_ROOT/ISO-9001-2015.pdf" 12
    ```
    """
    path, page_number = Path(sys.argv[1]), int(sys.argv[2])
    text = TesseractOcr().text_for_page(path, page_number)
    assert text.strip(), f"no text recognized on page {page_number} of {path}"
    print(f"page {page_number}: {len(text.split())} words\n{text[:500]}")


if __name__ == "__main__":  # pragma: no cover - hand-run only
    demo()
