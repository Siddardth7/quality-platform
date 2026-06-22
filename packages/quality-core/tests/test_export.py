"""
tests/test_export.py
Tests for quality_core/io/export.py — the shared export primitives (W04-1).

The formula-injection regression that used to live in the FMEA app now lives here,
against the core sanitizer, so every app that reuses `export_csv` inherits the
protection (and the guard travels with the code).
"""

import re

import pandas as pd
from quality_core.io.export import (
    FORMULA_PREFIXES,
    export_csv,
    safe_text,
    sanitize_for_export,
)


def test_formula_prefixes():
    assert FORMULA_PREFIXES == ("=", "+", "-", "@", "\t", "\r")


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
