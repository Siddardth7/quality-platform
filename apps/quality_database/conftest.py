"""Shared test fixtures for the quality-database app.

The only thing here is a synthetic-PDF builder (#329). The licensed corpus is never on
CI, so every PDF the tests read is generated in-test from text written for this repo —
no corpus bytes, nothing licensed, nothing committed. It is written by hand rather than
with ``pypdf.PdfWriter`` because pypdf can copy and stamp pages but has no API for
*drawing* text, and a text-bearing fixture is exactly what the extractor needs; the
alternative was a second dependency (``reportlab``) for ~25 lines of PDF syntax.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest


def _synthetic_pdf(pages: Sequence[str]) -> bytes:
    """A minimal PDF carrying one line of text per entry in ``pages``.

    An empty or whitespace-only entry gives a page with no usable text — how an
    image-only scan looks to a text-layer extractor.
    """
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # the page tree, filled in below once the kids are known
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    kids: list[str] = []
    for index, line in enumerate(pages):
        page_id = 4 + 2 * index
        kids.append(f"{page_id} 0 R")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>".encode()
        )
        body = f"BT /F1 12 Tf 20 100 Td ({line}) Tj ET".encode()
        objects.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(body), body))
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode()

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref_at = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref_at,
    )
    return bytes(out)


@pytest.fixture
def synthetic_pdf() -> Callable[[Sequence[str]], bytes]:
    """Build a synthetic PDF: one text line per page, no licensed content."""
    return _synthetic_pdf
