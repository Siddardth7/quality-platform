"""
tests/test_validate.py
Tests for quality_core/io/validate.py — the shared validated-ingest boundary (W04-2).

The module is app-agnostic, so these tests drive it with a toy `Widget` schema
(a numeric range field + a unique-key dataset rule) rather than any real FMEA/SPC
model. Wiring the real apps onto this boundary is W04-4 (SPC) and W04-6 (FMEA).
"""

from __future__ import annotations

import io
import os
from typing import Annotated

import openpyxl.xml
import pandas as pd
import pydantic
import pytest
from quality_core.io.validate import (
    DEFAULT_MAX_UPLOAD_BYTES,
    IngestError,
    TableSchema,
    clean_pydantic_message,
    load_table,
    load_table_from_path,
    read_table,
    read_table_from_path,
    validate_table,
)

# --- Toy app-agnostic schema -------------------------------------------------


class WidgetRow(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True)

    ID: Annotated[int, pydantic.Field(gt=0)]
    Name: Annotated[str, pydantic.Field(min_length=1)]
    Score: Annotated[int, pydantic.Field(ge=1, le=10)]


class WidgetDataset(pydantic.BaseModel):
    rows: list[WidgetRow]

    @pydantic.model_validator(mode="after")
    def unique_ids(self) -> "WidgetDataset":
        ids = [r.ID for r in self.rows]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"duplicate IDs found: {dupes}")
        return self


class AssertingDataset(pydantic.BaseModel):
    """Cross-row rule expressed with `assert`, so Pydantic prefixes the message
    with 'Assertion failed, ' rather than 'Value error, '."""

    rows: list[WidgetRow]

    @pydantic.model_validator(mode="after")
    def at_most_one(self) -> "AssertingDataset":
        assert len(self.rows) <= 1, "no more than one widget allowed"
        return self


class LooseRow(pydantic.BaseModel):
    """Non-strict model: without NaN→None normalisation, a blank cell would
    silently coerce to the literal string 'nan'."""

    ID: int
    Name: str


class RaisingRow(pydantic.BaseModel):
    """Row model whose *model* validator raises, so Pydantic prefixes the message
    with 'Value error, ' and reports it with an empty `loc` (#207)."""

    ID: int
    Name: str
    Low: int
    High: int

    @pydantic.model_validator(mode="after")
    def high_beats_low(self) -> "RaisingRow":
        if self.High <= self.Low:
            raise ValueError("High must be greater than Low")
        return self


class AssertingRow(pydantic.BaseModel):
    """The same row-level rule expressed with `assert`, so Pydantic prefixes the
    message with 'Assertion failed, ' instead."""

    ID: int
    Name: str
    Low: int
    High: int

    @pydantic.model_validator(mode="after")
    def high_beats_low(self) -> "AssertingRow":
        assert self.High > self.Low, "High must be greater than Low"
        return self


class OptRow(pydantic.BaseModel):
    """Toy row model with declarable optional columns (#200).

    Non-strict (unlike ``WidgetRow``) so a CSV-parsed numpy scalar coerces, and a
    blank cell arrives as ``None`` and is accepted by the nullable fields.
    """

    ID: Annotated[int, pydantic.Field(gt=0)]
    Name: Annotated[str, pydantic.Field(min_length=1)]
    Note: Annotated[str | None, pydantic.Field(default=None, max_length=5)] = None
    Weight: Annotated[float | None, pydantic.Field(default=None, gt=0)] = None


OPT_SCHEMA = TableSchema(
    name="Opt",
    row_model=OptRow,
    required_columns=("ID", "Name"),
    optional_columns=("Note", "Weight"),
)


SCHEMA = TableSchema(
    name="Widget",
    row_model=WidgetRow,
    dataset_model=WidgetDataset,
    template_hint="data/widget_template.csv",
)

GOOD_ROWS = [
    {"ID": 1, "Name": "alpha", "Score": 5},
    {"ID": 2, "Name": "beta", "Score": 9},
]


def _csv_bytes(rows: list[dict[str, object]], name: str = "widgets.csv") -> io.BytesIO:
    buf = io.BytesIO(pd.DataFrame(rows).to_csv(index=False).encode())
    buf.name = name  # mimic a Streamlit UploadedFile
    return buf


def _xlsx_bytes(rows: list[dict[str, object]], name: str = "widgets.xlsx") -> io.BytesIO:
    raw = io.BytesIO()
    pd.DataFrame(rows).to_excel(raw, index=False)
    buf = io.BytesIO(raw.getvalue())
    buf.name = name
    return buf


# --- TableSchema -------------------------------------------------------------


def test_required_columns_default_to_model_fields():
    assert SCHEMA.required_columns == ("ID", "Name", "Score")


def test_required_columns_override_is_respected():
    schema = TableSchema(name="W", row_model=WidgetRow, required_columns=("ID", "Name"))
    assert schema.required_columns == ("ID", "Name")


def test_ingest_error_is_a_value_error():
    # Existing `except ValueError` ingest paths must keep catching ingest failures.
    assert issubclass(IngestError, ValueError)


# --- read_table --------------------------------------------------------------


def test_read_table_csv_roundtrip():
    df = read_table(_csv_bytes(GOOD_ROWS))
    assert list(df.columns) == ["ID", "Name", "Score"]
    assert len(df) == 2


def test_read_table_xlsx_roundtrip():
    df = read_table(_xlsx_bytes(GOOD_ROWS))
    assert len(df) == 2


def test_xlsx_ingest_has_xml_bomb_hardening_enabled():
    """The .xlsx read path is hardened against XML-bomb payloads (#202, audit A11).

    `read_table` dispatches .xlsx to `pd.read_excel` (validate.py:274), which parses the
    workbook XML with openpyxl. openpyxl swaps in defusedxml's parser only while
    `openpyxl.xml.DEFUSEDXML` is true, and that flag is `defusedxml_available() and
    defusedxml_env_set()` — installed AND not disabled by `OPENPYXL_DEFUSEDXML`. It is
    bound once at import time, so both halves are asserted as observed, not monkeypatched.

    quality-core declares `defusedxml` as a direct dependency precisely because this flag
    is the only thing hardening that read; before #202 it was true only by accident,
    transitively via fpdf2, which no core code path requires.
    """
    # ponytail: assert the flag, not an XML-bomb payload — a payload fixture would be
    # testing openpyxl's parser. Upgrade to one only if we ever parse XML ourselves.
    assert openpyxl.xml.defusedxml_available() is True
    assert openpyxl.xml.DEFUSEDXML is True
    # `openpyxl/xml/functions.py` checks `if LXML is True:` *before* the defusedxml branch,
    # so an lxml in the environment silently routes the parse away from defusedxml. That is
    # not itself a regression (lxml is used with resolve_entities=False), but it would leave
    # the two asserts above green while naming a path they no longer exercise. Pin it, so
    # adding lxml is a deliberate decision that has to update this test.
    assert openpyxl.xml.LXML is False


def test_read_table_rejects_bytes_without_filename():
    # A bytes source has no `.name`; filename= is required (edge case 8).
    with pytest.raises(IngestError, match="no file name"):
        read_table(pd.DataFrame(GOOD_ROWS).to_csv(index=False).encode())


def test_read_table_accepts_raw_bytes_with_filename():
    df = read_table(
        pd.DataFrame(GOOD_ROWS).to_csv(index=False).encode(), filename="widgets.csv"
    )
    assert len(df) == 2


def test_read_table_accepts_bytearray_with_filename():
    df = read_table(
        bytearray(pd.DataFrame(GOOD_ROWS).to_csv(index=False).encode()), filename="widgets.csv"
    )
    assert len(df) == 2


def test_read_table_rejects_unsupported_extension():
    buf = io.BytesIO(b"not,a,sheet")
    buf.name = "widgets.txt"
    with pytest.raises(IngestError, match="Unsupported file type"):
        read_table(buf)


def test_read_table_filename_override_for_nameless_buffer():
    buf = io.BytesIO(pd.DataFrame(GOOD_ROWS).to_csv(index=False).encode())  # no .name
    df = read_table(buf, filename="anything.csv")
    assert len(df) == 2


def test_read_table_nameless_buffer_is_friendly():
    buf = io.BytesIO(b"ID,Name,Score\n1,a,5\n")  # no .name, no filename
    with pytest.raises(IngestError, match="no file name"):
        read_table(buf)


def test_read_table_unsupported_type_reported_before_size():
    # The file-type check must win over the size check, so the user learns the
    # more fundamental problem first. Uses a real over-ceiling buffer so this
    # exercises order, not a `.size` shortcut.
    buf = io.BytesIO(b"x" * (DEFAULT_MAX_UPLOAD_BYTES + 1))
    buf.name = "archive.zip"
    with pytest.raises(IngestError, match="Unsupported file type"):
        read_table(buf)


def test_read_table_corrupt_excel_is_friendly():
    buf = io.BytesIO(b"this is not really an excel file")
    buf.name = "broken.xlsx"
    with pytest.raises(IngestError, match="Could not read"):
        read_table(buf)


# --- R1 (HIGH) / measured byte ceiling ---------------------------------------


def test_r1_oversized_bytesio_with_no_size_attribute_is_rejected():
    """R1 (#199, HIGH): an 8 MB io.BytesIO with NO `.size` attribute and a 1 KB
    ceiling must be rejected outright — the parse must never run."""
    buf = io.BytesIO(b"x" * (8 * 1024 * 1024))
    buf.name = "huge.csv"
    assert not hasattr(buf, "size")
    with pytest.raises(IngestError, match="exceeds the 0 MB limit"):
        read_table(buf, max_bytes=1024)


def test_read_table_enforces_size_limit_with_real_bytes():
    # Rewritten per #199: a faked `.size` no longer means anything: the
    # ceiling is enforced against the stream's *measured* (real) length.
    buf = io.BytesIO(b"x" * (DEFAULT_MAX_UPLOAD_BYTES + 1))
    buf.name = "huge.csv"
    with pytest.raises(IngestError, match="exceeds the 20 MB limit"):
        read_table(buf)


def test_read_table_size_limit_can_be_disabled_with_real_bytes():
    # Rewritten per #199 (was `.size`-faked): a real over-ceiling buffer still
    # parses when max_bytes=None explicitly opts out of the byte gate.
    df = read_table(_csv_bytes(GOOD_ROWS), max_bytes=None)
    assert len(df) == 2


def test_read_table_hostile_small_size_attribute_does_not_shrink_the_ceiling():
    # Edge case 2: `.size = 1` on an 8 MB buffer must still be accepted, since
    # `.size` is never consulted — only the measured length matters.
    buf = _csv_bytes(GOOD_ROWS)
    buf.size = 1  # type: ignore[attr-defined]
    assert len(read_table(buf)) == 2


def test_read_table_hostile_huge_size_attribute_does_not_trigger_rejection():
    # Edge case 2, other direction: `.size = 10**12` on a tiny buffer must
    # still be accepted.
    buf = _csv_bytes(GOOD_ROWS)
    buf.size = 10**12  # type: ignore[attr-defined]
    assert len(read_table(buf)) == 2


def test_read_table_empty_stream_is_friendly_not_a_new_behaviour():
    # Edge case 3: 0 bytes passes the size gate, then fails at parse.
    buf = io.BytesIO(b"")
    buf.name = "empty.csv"
    with pytest.raises(IngestError, match="Could not read"):
        read_table(buf)


def test_read_table_stream_position_restored_before_parse():
    # Edge case 4: measuring the stream (seek to EOF and back) must restore
    # the position the caller left the stream at *before* pandas parses it —
    # not reset it to 0. Prepend junk before a non-zero starting offset, seek
    # there first (as a caller positioned mid-stream would), and confirm the
    # parse reads from that position rather than from 0 or from EOF.
    junk = b"garbage-prefix-not-csv,,,\n"
    payload = junk + pd.DataFrame(GOOD_ROWS).to_csv(index=False).encode()
    buf = io.BytesIO(payload)
    buf.name = "widgets.csv"
    buf.seek(len(junk))
    df = read_table(buf)
    assert list(df.columns) == ["ID", "Name", "Score"]
    assert len(df) == 2


def test_read_table_missing_tell_is_unmeasurable():
    # Edge case 1: `tell` entirely missing → AttributeError caught, fail closed.
    class _NoTell:
        name = "widgets.csv"

        def seek(self, *a, **k):
            return 0

        def read(self, *a, **k):
            return b""

    with pytest.raises(IngestError, match="could not be measured"):
        read_table(_NoTell())  # type: ignore[arg-type]


def test_read_table_missing_seek_is_unmeasurable():
    # Edge case 1: `seek` entirely missing → AttributeError caught, fail closed.
    class _NoSeekMethod:
        name = "widgets.csv"

        def tell(self, *a, **k):
            return 0

        def read(self, *a, **k):
            return b""

    with pytest.raises(IngestError, match="could not be measured"):
        read_table(_NoSeekMethod())  # type: ignore[arg-type]


def test_read_table_seek_raising_oserror_is_unmeasurable():
    # Edge case 1: seek() raising OSError/io.UnsupportedOperation (e.g. a
    # socket/pipe-backed file-like) → IngestError, never a parse.
    class _Unseekable(io.BytesIO):
        name = "widgets.csv"

        def seek(self, *a, **k):  # noqa: D102 - test double
            raise io.UnsupportedOperation("not seekable")

    buf = _Unseekable(pd.DataFrame(GOOD_ROWS).to_csv(index=False).encode())
    with pytest.raises(IngestError, match="could not be measured"):
        read_table(buf)


def test_read_table_not_seekable_attribute_missing_entirely():
    # Edge case 1: an object with no tell/seek attributes at all (not just a
    # BytesIO subclass with a broken method) is also unmeasurable.
    class _NoSeek:
        name = "widgets.csv"

        def read(self, *a, **k):
            return b""

    with pytest.raises(IngestError, match="could not be measured"):
        read_table(_NoSeek())  # type: ignore[arg-type]


# --- Row / column caps --------------------------------------------------------


def _rows(n: int) -> list[dict[str, object]]:
    return [{"ID": i + 1, "Name": f"n{i}", "Score": 5} for i in range(n)]


def test_read_table_row_cap_at_cap_is_accepted():
    df = read_table(_csv_bytes(_rows(3)), max_rows=3)
    assert len(df) == 3


def test_read_table_row_cap_over_cap_is_rejected():
    with pytest.raises(IngestError, match="more than 3 rows"):
        read_table(_csv_bytes(_rows(4)), max_rows=3)


def test_read_table_row_cap_none_disables_it():
    df = read_table(_csv_bytes(_rows(10)), max_rows=None)
    assert len(df) == 10


def test_read_table_column_cap_at_cap_is_accepted():
    rows = [{f"c{i}": 1 for i in range(3)}]
    df = read_table(_csv_bytes(rows), max_columns=3)
    assert df.shape[1] == 3


def test_read_table_column_cap_over_cap_is_rejected():
    rows = [{f"c{i}": 1 for i in range(4)}]
    with pytest.raises(IngestError, match="more than 3 columns"):
        read_table(_csv_bytes(rows), max_columns=3)


def test_read_table_column_cap_none_disables_it():
    rows = [{f"c{i}": 1 for i in range(4)}]
    df = read_table(_csv_bytes(rows), max_columns=None)
    assert df.shape[1] == 4


def test_read_table_byte_gate_applies_to_xlsx_too():
    buf = _xlsx_bytes(GOOD_ROWS)
    size = len(buf.getvalue())
    with pytest.raises(IngestError, match="exceeds"):
        read_table(buf, max_bytes=size - 1)


# --- read_table_from_path ------------------------------------------------------


def test_read_table_from_path_happy(tmp_path):
    p = tmp_path / "widgets.csv"
    pd.DataFrame(GOOD_ROWS).to_csv(p, index=False)
    df = read_table_from_path(p)  # pathlib.Path
    assert len(df) == 2


def test_read_table_from_path_accepts_str(tmp_path):
    p = tmp_path / "widgets.csv"
    pd.DataFrame(GOOD_ROWS).to_csv(p, index=False)
    df = read_table_from_path(str(p))  # plain string path → os.fspath
    assert len(df) == 2


def test_read_table_from_path_missing_is_friendly():
    with pytest.raises(IngestError, match="Could not read"):
        read_table_from_path("/no/such/widgets.csv")


def test_read_table_from_path_directory_is_friendly(tmp_path):
    # R2 (MEDIUM), part 1: a directory is a real filesystem object but not
    # openable as a file — must fail the same friendly way as "missing".
    with pytest.raises(IngestError, match="Could not read"):
        read_table_from_path(tmp_path)


def test_read_table_from_path_url_shaped_string_reaches_no_network():
    # R2 (MEDIUM), part 2: a URL-shaped string is simply an unreadable local
    # path — proven behaviourally (the reject path), not only via mypy.
    with pytest.raises(IngestError, match="Could not read"):
        read_table_from_path("http://169.254.169.254/latest/meta-data")


def test_read_table_from_path_file_uri_shaped_string_is_rejected():
    with pytest.raises(IngestError, match="Could not read"):
        read_table_from_path("file:///etc/passwd")


def test_read_table_from_path_propagates_size_limit(tmp_path):
    p = tmp_path / "widgets.csv"
    pd.DataFrame(GOOD_ROWS).to_csv(p, index=False)
    with pytest.raises(IngestError, match="exceeds"):
        read_table_from_path(p, max_bytes=1)


def test_read_table_from_path_propagates_row_cap(tmp_path):
    p = tmp_path / "widgets.csv"
    pd.DataFrame(_rows(4)).to_csv(p, index=False)
    with pytest.raises(IngestError, match="more than 3 rows"):
        read_table_from_path(p, max_rows=3)


def test_read_table_from_path_str_and_pathlike_resolve_same_name(tmp_path):
    p = tmp_path / "widgets.csv"
    pd.DataFrame(GOOD_ROWS).to_csv(p, index=False)
    assert os.fspath(p) == str(p)
    assert len(read_table_from_path(p)) == len(read_table_from_path(str(p)))


# --- validate_table ----------------------------------------------------------


def test_validate_happy_path_returns_validated_columns():
    df = pd.DataFrame(GOOD_ROWS)
    out = validate_table(df, SCHEMA)
    # #200: a narrowed copy, never the caller's object. Values/order unchanged here
    # because GOOD_ROWS carries exactly the required columns.
    assert out is not df
    pd.testing.assert_frame_equal(out, df)


def test_validate_rejects_empty_frame():
    df = pd.DataFrame(columns=["ID", "Name", "Score"])
    with pytest.raises(IngestError, match="at least one row"):
        validate_table(df, SCHEMA)


def test_validate_reports_missing_columns():
    df = pd.DataFrame([{"ID": 1, "Name": "alpha"}])  # no Score
    with pytest.raises(IngestError, match=r"Missing required column\(s\): \['Score'\]"):
        validate_table(df, SCHEMA)


def test_validate_drops_undeclared_columns():
    df = pd.DataFrame([{"ID": 1, "Name": "alpha", "Score": 5, "Extra": "ok"}])
    out = validate_table(df, SCHEMA)
    # #200: an undeclared column is dropped silently — not an error, but it must
    # not reach the caller (and through them, an engine) unvalidated.
    assert list(out.columns) == ["ID", "Name", "Score"]


def test_validate_range_error_is_addressed_and_friendly():
    df = pd.DataFrame(
        [
            {"ID": 1, "Name": "alpha", "Score": 5},
            {"ID": 2, "Name": "beta", "Score": 99},  # out of range
        ]
    )
    with pytest.raises(IngestError) as exc:
        validate_table(df, SCHEMA)
    msg = str(exc.value)
    assert "Row 3" in msg  # header is row 1; second data row is row 3
    assert "Score" in msg
    assert "less than or equal to 10" in msg  # Pydantic's own specific message
    assert "got 99" in msg  # offending value echoed back
    assert "data/widget_template.csv" in msg  # template hint appended


def test_validate_type_error_is_addressed():
    df = pd.DataFrame([{"ID": 1, "Name": "alpha", "Score": "five"}])
    with pytest.raises(IngestError) as exc:
        validate_table(df, SCHEMA)
    msg = str(exc.value)
    assert "Row 2" in msg
    assert "Score" in msg
    assert "got 'five'" in msg


def test_validate_blank_cell_normalised_not_surfaced_as_nan():
    # An empty Score cell reads back as NaN; it must be addressed clearly, never
    # echoed as the float "nan".
    df = pd.DataFrame([{"ID": 1, "Name": "alpha", "Score": float("nan")}])
    with pytest.raises(IngestError) as exc:
        validate_table(df, SCHEMA)
    msg = str(exc.value)
    assert "Row 2" in msg
    assert "Score" in msg
    assert "got None" in msg  # NaN normalised to None
    assert "nan" not in msg.lower()


def test_validate_blank_cell_not_coerced_to_nan_string_under_loose_model():
    # Regression: without NaN→None, a non-strict str field would accept the
    # blank cell as the literal text "nan" and pass validation silently.
    schema = TableSchema(name="Loose", row_model=LooseRow)
    df = pd.DataFrame([{"ID": 1, "Name": float("nan")}])
    with pytest.raises(IngestError) as exc:
        validate_table(df, schema)
    assert "Name" in str(exc.value)


def test_validate_long_offending_value_is_truncated():
    # A long offending value is echoed but truncated so the message stays readable.
    long_value = "x" * 100
    df = pd.DataFrame([{"ID": 1, "Name": "alpha", "Score": long_value}])
    with pytest.raises(IngestError) as exc:
        validate_table(df, SCHEMA)
    msg = str(exc.value)
    assert "..." in msg
    assert long_value not in msg  # not echoed in full


def test_validate_array_like_cell_does_not_crash_normalisation():
    # A cell holding a list makes pd.isna return an array; _na_to_none must treat
    # it as present rather than raising on the ambiguous truth value.
    df = pd.DataFrame([{"ID": 1, "Name": "alpha", "Score": [1, 2]}])
    with pytest.raises(IngestError) as exc:
        validate_table(df, SCHEMA)
    assert "Row 2" in str(exc.value)  # surfaced as a normal validation error


def test_validate_dataset_assert_rule_strips_pydantic_prefix():
    schema = TableSchema(name="Widget", row_model=WidgetRow, dataset_model=AssertingDataset)
    df = pd.DataFrame(GOOD_ROWS)  # 2 rows → violates "at most one"
    with pytest.raises(IngestError) as exc:
        validate_table(df, schema)
    msg = str(exc.value)
    assert "no more than one widget allowed" in msg
    assert "Assertion failed" not in msg  # internal prefix stripped


def test_validate_dataset_rule_duplicate_ids():
    df = pd.DataFrame(
        [
            {"ID": 1, "Name": "alpha", "Score": 5},
            {"ID": 1, "Name": "beta", "Score": 6},  # duplicate ID
        ]
    )
    with pytest.raises(IngestError) as exc:
        validate_table(df, SCHEMA)
    msg = str(exc.value)
    assert "Widget dataset is invalid" in msg
    assert "duplicate IDs found" in msg
    # The "Value error, " Pydantic prefix is stripped from the surfaced sentence.
    assert "Value error" not in msg


def test_validate_without_dataset_model_skips_cross_row_checks():
    schema = TableSchema(name="W", row_model=WidgetRow)  # no dataset_model
    df = pd.DataFrame(
        [
            {"ID": 1, "Name": "alpha", "Score": 5},
            {"ID": 1, "Name": "beta", "Score": 6},  # duplicate, but no rule to catch it
        ]
    )
    pd.testing.assert_frame_equal(validate_table(df, schema), df)


# --- load_table (read + validate) -------------------------------------------


def test_load_table_end_to_end_happy():
    df = load_table(_csv_bytes(GOOD_ROWS), SCHEMA)
    assert len(df) == 2


def test_load_table_surfaces_validation_error_not_stack_trace():
    bad = _csv_bytes([{"ID": 1, "Name": "alpha", "Score": 50}])
    with pytest.raises(IngestError, match="less than or equal to 10"):
        load_table(bad, SCHEMA)


def test_load_table_surfaces_bad_file_as_ingest_error():
    buf = io.BytesIO(b"\x00\x01 not a csv really")
    buf.name = "data.xlsx"
    with pytest.raises(IngestError):
        load_table(buf, SCHEMA)


# --- load_table_from_path -----------------------------------------------------


def test_load_table_from_path_happy(tmp_path):
    p = tmp_path / "widgets.csv"
    pd.DataFrame(GOOD_ROWS).to_csv(p, index=False)
    df = load_table_from_path(p, SCHEMA)
    assert len(df) == 2


def test_load_table_from_path_surfaces_validation_error(tmp_path):
    p = tmp_path / "widgets.csv"
    pd.DataFrame([{"ID": 1, "Name": "alpha", "Score": 50}]).to_csv(p, index=False)
    with pytest.raises(IngestError, match="less than or equal to 10"):
        load_table_from_path(p, SCHEMA)


def test_load_table_from_path_missing_is_friendly():
    with pytest.raises(IngestError, match="Could not read"):
        load_table_from_path("/no/such/widgets.csv", SCHEMA)


# --- R2 (MEDIUM) / str-and-PathLike narrowing --------------------------------


def test_r2_read_table_rejects_a_str_source_at_the_type_boundary():
    """R2 (#199, MEDIUM): read_table must reject a str source at runtime, not
    just in its type annotation. Regression guard: this is exactly the
    reviewer's defeat combination — a `filename=` supplied (so name
    resolution would otherwise succeed) and `max_bytes=None` (so the byte
    ceiling can't accidentally reject it via an unmeasurable-stream error).
    If the runtime `isinstance(source, (str, os.PathLike))` guard in
    read_table were removed, this reaches `pandas`/`urlopen` against a live
    URL instead of raising here."""
    with pytest.raises(IngestError, match="A file path is not accepted here"):
        read_table(  # type: ignore[arg-type]
            "http://169.254.169.254/latest/meta-data.csv",
            filename="x.csv",
            max_bytes=None,
        )


def test_r2_load_table_rejects_a_str_source_too():
    """Same regression, through the load_table wrapper (review fix #2)."""
    with pytest.raises(IngestError, match="A file path is not accepted here"):
        load_table(  # type: ignore[arg-type]
            "http://169.254.169.254/latest/meta-data.csv",
            SCHEMA,
            filename="x.csv",
            max_bytes=None,
        )


def test_r2_read_table_rejects_a_pathlike_source_too(tmp_path):
    """Regression guard: a real, existing file, with `max_bytes=None` (the
    combination that let pandas read the file straight through the old
    byte-ceiling-only rejection). Must be rejected as a path, not as
    unmeasurable — asserting the *specific* path-rejection message is what
    makes this fail if the runtime guard is deleted; the old assertion
    ("could not be measured") passed even with the guard entirely absent."""
    p = tmp_path / "secret.csv"
    pd.DataFrame(GOOD_ROWS).to_csv(p, index=False)
    with pytest.raises(IngestError, match="A file path is not accepted here"):
        read_table(p, max_bytes=None)  # type: ignore[arg-type]


def test_r2_url_string_reaches_no_network_via_read_table_from_path():
    """R2, the path-facing half: a URL string reaches only the local
    filesystem resolver (`open()`), never pandas' URL-resolving `read_csv`."""
    with pytest.raises(IngestError, match="Could not read"):
        read_table_from_path("https://example.com/widgets.csv")


# --- #200: validate_table is reductive — optional_columns + narrowed copy ------
# The finding: validation was assertive only (check required_columns, hand back
# the caller's whole frame), so any other column reached an engine unvalidated.


def test_optional_column_present_and_valid_survives_with_its_values():
    df = pd.DataFrame([{"ID": 1, "Name": "alpha", "Note": "ok", "Weight": 2.5}])
    out = validate_table(df, OPT_SCHEMA)
    assert list(out.columns) == ["ID", "Name", "Note", "Weight"]
    assert out["Note"].iloc[0] == "ok"
    assert out["Weight"].iloc[0] == 2.5


def test_optional_column_present_and_invalid_is_row_and_column_addressed():
    df = pd.DataFrame(
        [
            {"ID": 1, "Name": "alpha", "Note": "ok"},
            {"ID": 2, "Name": "beta", "Note": "far too long"},  # max_length=5
        ]
    )
    with pytest.raises(IngestError) as exc:
        validate_table(df, OPT_SCHEMA)
    msg = str(exc.value)
    assert "Row 3" in msg  # header is row 1, so the 2nd data row is row 3
    assert "column 'Note'" in msg


def test_optional_column_absent_is_not_an_error_and_not_in_the_output():
    df = pd.DataFrame([{"ID": 1, "Name": "alpha"}])
    out = validate_table(df, OPT_SCHEMA)
    # present_optional is empty here — the other branch of the projection.
    assert list(out.columns) == ["ID", "Name"]


def test_optional_column_present_but_blank_stays_nan_in_the_output():
    # The row model sees None (NaN normalised), but the frame is projected, never
    # rebuilt from model output, so the original NaN cell survives.
    df = pd.DataFrame([{"ID": 1, "Name": "alpha", "Weight": float("nan")}])
    out = validate_table(df, OPT_SCHEMA)
    assert list(out.columns) == ["ID", "Name", "Weight"]
    assert pd.isna(out["Weight"].iloc[0])


def test_returned_columns_follow_schema_order_and_dedupe_a_shared_name():
    # "Note" is declared in both tuples (legal: it has a default, so the
    # __post_init__ guard accepts it as optional), and the input column order is
    # deliberately scrambled — the output must follow the *schema's* order, once each.
    schema = TableSchema(
        name="Opt",
        row_model=OptRow,
        required_columns=("Name", "ID", "Note"),
        optional_columns=("Note", "Weight"),
    )
    df = pd.DataFrame([{"Weight": 1.0, "Note": "ok", "ID": 1, "Name": "alpha"}])
    assert list(validate_table(df, schema).columns) == ["Name", "ID", "Note", "Weight"]


def test_index_is_preserved_by_the_projection():
    df = pd.DataFrame(GOOD_ROWS, index=[7, 11])
    assert list(validate_table(df, SCHEMA).index) == [7, 11]


def test_dtypes_are_preserved_no_coercion_back_into_the_frame():
    df = pd.DataFrame([{"ID": 1, "Name": "alpha", "Weight": 2.5}])
    out = validate_table(df, OPT_SCHEMA)
    assert out.dtypes.to_dict() == df[["ID", "Name", "Weight"]].dtypes.to_dict()


def test_returned_frame_is_a_copy_mutating_it_does_not_touch_the_input():
    # Pins the caller-independence contract: msa_app/gage_rr_engine.py assigns into
    # the frame this returns, and that must never write through to the caller's.
    # This fails on `return df` (the pre-#200 behaviour); under the pinned pandas
    # (Copy-on-Write always on) it passes with or without the explicit `.copy()`,
    # which is kept so the guarantee does not rest on a pandas implementation detail.
    df = pd.DataFrame(GOOD_ROWS)
    out = validate_table(df, SCHEMA)
    out.loc[0, "Score"] = 99
    assert df.loc[0, "Score"] == 5


def test_many_junk_columns_are_all_dropped_under_the_column_cap():
    row = {"ID": 1, "Name": "alpha", "Score": 5}
    row.update({f"junk_{i}": i for i in range(900)})
    assert list(validate_table(pd.DataFrame([row]), SCHEMA).columns) == ["ID", "Name", "Score"]


def test_optional_column_that_is_not_a_row_model_field_is_a_developer_error():
    # ValueError, not IngestError: an import-time developer mistake, never shown
    # to a user.
    with pytest.raises(ValueError, match=r"optional_columns \['nope'\]") as exc:
        TableSchema(name="Opt", row_model=OptRow, optional_columns=("nope",))
    assert not isinstance(exc.value, IngestError)


def test_optional_column_that_is_a_required_row_model_field_is_a_developer_error():
    # "ID" has no default, so a file omitting it would fail every row with a
    # confusing "Field required" — reject the schema instead.
    with pytest.raises(ValueError, match=r"optional_columns \['ID'\]"):
        TableSchema(name="Opt", row_model=OptRow, optional_columns=("ID",))


def test_bad_optional_column_error_lists_every_offender_at_once():
    with pytest.raises(ValueError, match=r"optional_columns \['ID', 'nope'\]"):
        TableSchema(name="Opt", row_model=OptRow, optional_columns=("ID", "Note", "nope"))


def test_valid_optional_columns_construct_the_schema_without_raising():
    # The pass-through branch of the __post_init__ guard.
    assert OPT_SCHEMA.optional_columns == ("Note", "Weight")


# --- #200 Definition of Done: an unvalidated column cannot reach an engine ----


def test_dod_undeclared_column_cannot_reach_a_caller_through_load_table():
    rows = [{**r, "secret": "<script>", "operator": "A"} for r in GOOD_ROWS]
    out = load_table(_csv_bytes(rows), SCHEMA)
    assert list(out.columns) == ["ID", "Name", "Score"]
    assert "secret" not in out.columns


def test_dod_undeclared_column_cannot_reach_a_caller_through_load_table_from_path(tmp_path):
    p = tmp_path / "widgets.csv"
    rows = [{**r, "secret": "<script>", "operator": "A"} for r in GOOD_ROWS]
    pd.DataFrame(rows).to_csv(p, index=False)
    out = load_table_from_path(p, SCHEMA)
    assert list(out.columns) == ["ID", "Name", "Score"]
    assert "secret" not in out.columns


# --- #207: clean_pydantic_message, single-sourced for core + three app sites ---


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # the two prefixes Pydantic adds to model-validator messages
        ("Value error, usl must be greater than lsl", "usl must be greater than lsl"),
        ("Assertion failed, usl must be greater than lsl", "usl must be greater than lsl"),
        # already clean → untouched (every field-level error takes this path)
        ("usl must be greater than lsl", "usl must be greater than lsl"),
        ("Input should be a valid integer", "Input should be a valid integer"),
        ("", ""),
        # a mid-sentence occurrence is NOT a prefix and must survive intact
        ("the log said Value error, at 12:00", "the log said Value error, at 12:00"),
        ("reported Assertion failed, twice", "reported Assertion failed, twice"),
        # near-misses: no trailing ", " → not the prefix
        ("Value error but not the prefix", "Value error but not the prefix"),
    ],
)
def test_clean_pydantic_message(raw, expected):
    assert clean_pydantic_message(raw) == expected


def test_clean_pydantic_message_strips_only_one_leading_prefix():
    # Guards against over-stripping (a `while` loop or `str.replace`): exactly one
    # leading occurrence of each prefix goes, no more.
    assert clean_pydantic_message("Value error, Value error, doubled") == "Value error, doubled"


def test_clean_pydantic_message_is_idempotent_on_a_cleaned_message():
    once = clean_pydantic_message("Value error, ratings must be 1-10")
    assert once == "ratings must be 1-10"
    assert clean_pydantic_message(once) == once


RAISING_SCHEMA = TableSchema(name="Range", row_model=RaisingRow)
ASSERTING_SCHEMA = TableSchema(name="Range", row_model=AssertingRow)


@pytest.mark.parametrize(
    "schema", [RAISING_SCHEMA, ASSERTING_SCHEMA], ids=["raise", "assert"]
)
def test_validate_row_model_error_strips_pydantic_prefix(schema):
    # #207 behaviour change: the *row* formatter now cleans the message too. A
    # model-level rule has an empty `loc`, so there is no column clause, and the
    # sentence must be the validator's own — no "Value error, "/"Assertion failed, ".
    df = pd.DataFrame([{"ID": 1, "Name": "a", "Low": 5, "High": 2}])
    with pytest.raises(IngestError) as exc:
        validate_table(df, schema)
    msg = str(exc.value)
    # (pytest rewrites the `assert` model's message with its own explanation, so
    # match the head of the sentence rather than the whole clause.)
    assert msg.startswith("Row 2: High must be greater than Low")
    assert " (got {'ID': 1," in msg
    assert "Value error" not in msg
    assert "Assertion failed" not in msg
    assert "column" not in msg.split(" (got ")[0]


def test_validate_row_model_error_still_echoes_the_truncated_row():
    # #200 is NOT reverted by #207: the echo stays unconditional and truncated at
    # _MAX_ECHO_LEN on the row path; only the message prefix is stripped.
    long_name = "x" * 100
    df = pd.DataFrame([{"ID": 1, "Name": long_name, "Low": 5, "High": 2}])
    with pytest.raises(IngestError) as exc:
        validate_table(df, RAISING_SCHEMA)
    msg = str(exc.value)
    assert msg.startswith("Row 2: High must be greater than Low (got ")
    assert "...)" in msg  # truncated, not echoed whole
    assert long_name not in msg
    assert "Value error" not in msg
