"""
tests/test_validate.py
Tests for quality_core/io/validate.py — the shared validated-ingest boundary (W04-2).

The module is app-agnostic, so these tests drive it with a toy `Widget` schema
(a numeric range field + a unique-key dataset rule) rather than any real FMEA/SPC
model. Wiring the real apps onto this boundary is W04-4 (SPC) and W04-6 (FMEA).
"""

from __future__ import annotations

import io
from typing import Annotated

import pandas as pd
import pydantic
import pytest
from quality_core.io.validate import (
    DEFAULT_MAX_UPLOAD_BYTES,
    IngestError,
    TableSchema,
    load_table,
    read_table,
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


def test_read_table_from_path(tmp_path):
    p = tmp_path / "widgets.csv"
    pd.DataFrame(GOOD_ROWS).to_csv(p, index=False)
    df = read_table(p)
    assert len(df) == 2


def test_read_table_from_str_path(tmp_path):
    p = tmp_path / "widgets.csv"
    pd.DataFrame(GOOD_ROWS).to_csv(p, index=False)
    df = read_table(str(p))  # plain string path → name resolved via os.fspath
    assert len(df) == 2


def test_read_table_missing_path_is_friendly():
    # A nonexistent path: size lookup fails gracefully, then the read is normalised.
    with pytest.raises(IngestError, match="Could not read"):
        read_table("/no/such/widgets.csv")


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
    # more fundamental problem first.
    buf = io.BytesIO(b"junk")
    buf.name = "archive.zip"
    buf.size = DEFAULT_MAX_UPLOAD_BYTES + 1
    with pytest.raises(IngestError, match="Unsupported file type"):
        read_table(buf)


def test_read_table_enforces_size_limit():
    buf = _csv_bytes(GOOD_ROWS)
    buf.size = DEFAULT_MAX_UPLOAD_BYTES + 1  # Streamlit-style size attribute
    with pytest.raises(IngestError, match="exceeds the 20 MB limit"):
        read_table(buf)


def test_read_table_size_limit_can_be_disabled():
    buf = _csv_bytes(GOOD_ROWS)
    buf.size = DEFAULT_MAX_UPLOAD_BYTES + 1
    assert len(read_table(buf, max_bytes=None)) == 2


def test_read_table_corrupt_excel_is_friendly():
    buf = io.BytesIO(b"this is not really an excel file")
    buf.name = "broken.xlsx"
    with pytest.raises(IngestError, match="Could not read"):
        read_table(buf)


# --- validate_table ----------------------------------------------------------


def test_validate_happy_path_returns_frame_unchanged():
    df = pd.DataFrame(GOOD_ROWS)
    out = validate_table(df, SCHEMA)
    assert out is df


def test_validate_rejects_empty_frame():
    df = pd.DataFrame(columns=["ID", "Name", "Score"])
    with pytest.raises(IngestError, match="at least one row"):
        validate_table(df, SCHEMA)


def test_validate_reports_missing_columns():
    df = pd.DataFrame([{"ID": 1, "Name": "alpha"}])  # no Score
    with pytest.raises(IngestError, match=r"Missing required column\(s\): \['Score'\]"):
        validate_table(df, SCHEMA)


def test_validate_ignores_extra_columns():
    df = pd.DataFrame([{"ID": 1, "Name": "alpha", "Score": 5, "Extra": "ok"}])
    assert validate_table(df, SCHEMA) is df


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
    assert validate_table(df, schema) is df


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
