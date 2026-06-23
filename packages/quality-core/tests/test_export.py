"""
tests/test_export.py
Tests for quality_core/io/export.py — the shared export primitives (W04-1).

The formula-injection regression that used to live in the FMEA app now lives here,
against the core sanitizer, so every app that reuses `export_csv` inherits the
protection (and the guard travels with the code).
"""

import re

import openpyxl
import pandas as pd
import pytest
from quality_core.io.export import (
    FORMULA_PREFIXES,
    export_csv,
    pdf_subheader,
    pdf_summary_cells,
    pdf_title,
    safe_text,
    sanitize_cell,
    sanitize_for_export,
    write_keyvalue_sheet,
)


class _RecordingPdf:
    """Minimal duck-typed stand-in for an fpdf2 PDF, so the core PDF-chrome helpers
    can be tested without depending on fpdf2 (a consumer-app dependency)."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.w, self.l_margin, self.r_margin = 210.0, 10.0, 10.0

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return record


def test_formula_prefixes():
    assert FORMULA_PREFIXES == ("=", "+", "-", "@", "\t", "\r")


# --- write_keyvalue_sheet title ---------------------------------------------


def test_write_keyvalue_sheet_sets_title_and_values():
    wb = openpyxl.Workbook()
    ws = wb.active
    write_keyvalue_sheet(ws, [("Key", "Val"), ("N", 3)], title="Meta")
    assert ws.title == "Meta"
    assert ws.cell(1, 1).value == "Key"
    assert ws.cell(2, 2).value == 3


def test_write_keyvalue_sheet_title_optional():
    wb = openpyxl.Workbook()
    ws = wb.active
    original = ws.title
    write_keyvalue_sheet(ws, [("a", "b")])
    assert ws.title == original  # unchanged when no title given


# --- PDF chrome helpers ------------------------------------------------------


def test_pdf_title_emits_sanitized_centered_bar():
    pdf = _RecordingPdf()
    pdf_title(pdf, "Report — Summary")  # em dash must be Latin-1 sanitized
    methods = [c[0] for c in pdf.calls]
    assert "set_fill_color" in methods
    cell_text = [c[1][2] for c in pdf.calls if c[0] == "cell"]
    assert cell_text == ["Report - Summary"]  # em dash → hyphen


def test_pdf_subheader_renders_one_centered_line():
    pdf = _RecordingPdf()
    pdf_subheader(pdf, "Generated: 2026")
    cells = [c for c in pdf.calls if c[0] == "cell"]
    assert len(cells) == 1
    assert cells[0][1][2] == "Generated: 2026"


def test_pdf_summary_cells_emits_label_and_value_per_metric():
    pdf = _RecordingPdf()
    pdf_summary_cells(pdf, [("Cp", "1.4"), ("Cpk", "1.2"), ("Pp", "1.3")])
    cells = [c for c in pdf.calls if c[0] == "cell"]
    assert len(cells) == 6  # 3 labels + 3 values
    expected_w = (210.0 - 20.0) / 3
    assert all(c[1][0] == pytest.approx(expected_w) for c in cells)
    assert cells[0][1][2] == "Cp" and cells[3][1][2] == "1.4"


def test_sanitize_cell_scalar_matches_dataframe_escaping():
    # The scalar helper escapes exactly what sanitize_for_export escapes per cell.
    assert sanitize_cell("=evil") == "'=evil"
    assert sanitize_cell("\t=cmd") == "'\t=cmd"  # control-prefixed formula
    assert sanitize_cell("  -1+2") == "'  -1+2"  # whitespace-bypass
    assert sanitize_cell("safe") == "safe"
    assert sanitize_cell(42) == 42  # non-strings pass through
    assert sanitize_cell(None) is None
    # Idempotent: an already-escaped value is not double-escaped.
    assert sanitize_cell(sanitize_cell("=x")) == "'=x"


def test_sanitize_escapes_formula_prefixes():
    df = pd.DataFrame(
        [{"a": "=evil", "b": "+bad", "c": "-exploit", "d": "@nope", "e": "safe"}]
    )
    out = sanitize_for_export(df)
    assert out.loc[0, "a"] == "'=evil"
    assert out.loc[0, "b"] == "'+bad"
    assert out.loc[0, "c"] == "'-exploit"
    assert out.loc[0, "d"] == "'@nope"
    assert out.loc[0, "e"] == "safe"  # untouched


def test_sanitize_escapes_whitespace_and_control_prefixed_formulas():
    """Leading Tab/CR/whitespace before a formula char must not bypass escaping.

    Spreadsheets strip leading whitespace before formula detection, so these are
    still evaluated if left unescaped (OWASP CSV-injection trigger set).
    """
    df = pd.DataFrame(
        [{
            "tab": "\t=cmd|'/C calc'!A1",
            "cr": "\r=evil",
            "space": " =1+1",
            "newline": "\n=x",
            "plainspace": "  hello",   # leading space, no formula → safe
        }]
    )
    out = sanitize_for_export(df)
    assert out.loc[0, "tab"] == "'\t=cmd|'/C calc'!A1"
    assert out.loc[0, "cr"] == "'\r=evil"
    assert out.loc[0, "space"] == "' =1+1"
    assert out.loc[0, "newline"] == "'\n=x"
    assert out.loc[0, "plainspace"] == "  hello"  # untouched


def test_sanitize_is_idempotent():
    """Re-sanitizing must not double-escape an already-escaped value."""
    df = pd.DataFrame([{"a": "=evil", "b": "\t=tabbed", "c": " =spaced"}])
    once = sanitize_for_export(df)
    twice = sanitize_for_export(once)
    assert twice.loc[0, "a"] == "'=evil"      # apostrophe-prefixed → no longer matches
    assert twice.loc[0, "b"] == "'\t=tabbed"  # not re-escaped
    assert twice.loc[0, "c"] == "' =spaced"


def test_sanitize_leaves_non_strings_and_copies():
    df = pd.DataFrame([{"n": 5, "f": 1.5, "b": True}])
    out = sanitize_for_export(df)
    assert out.loc[0, "n"] == 5 and out.loc[0, "f"] == 1.5 and bool(out.loc[0, "b"]) is True
    assert out is not df  # returns a copy


def test_export_csv_no_formula_injection():
    df = pd.DataFrame([{"x": "=SUM(1,2)", "y": "+bad", "z": "-exploit", "w": "@nope"}])
    csv_text = export_csv(df).decode("utf-8")
    for raw in ("=SUM(1,2)", "+bad", "-exploit", "@nope"):
        pattern = r"(?<!['])(?:(?<=,)|(?<=\n))" + re.escape(raw)
        assert not re.search(pattern, csv_text), f"unescaped {raw!r} found in CSV"


def test_safe_text_maps_unicode_to_latin1():
    assert safe_text("9–10 × ≥") == "9-10 x >="
    # Result must be encodable as Latin-1 (fpdf2 core-font safe).
    safe_text("greek Ω emoji 🎯").encode("latin-1")
