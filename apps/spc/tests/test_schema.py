"""Tests for spc_app/schema.py — validated SPC upload ingest (W04-4).

Drives the page-facing load_spc_csv (read + validate via the shared
quality_core.io boundary) with in-memory CSVs, asserting valid uploads pass and
malformed ones raise a friendly, row-addressed IngestError. The demo dataset —
the documented template — must itself validate.
"""

from __future__ import annotations

import io

import pandas as pd
import pytest

from spc_app.schema import SPC_SCHEMA, IngestError, load_spc_csv
from spc_app.spc_engine.data_generator import generate_demo_dataset

GOOD_ROWS = [
    {"stream": "ply_thickness", "subgroup": 1, "value": 0.2503, "sample_size": 5,
     "lsl": 0.245, "usl": 0.255},
    {"stream": "ply_thickness", "subgroup": 1, "value": 0.2498, "sample_size": 5,
     "lsl": 0.245, "usl": 0.255},
    {"stream": "ply_thickness", "subgroup": 2, "value": 0.2511, "sample_size": 5,
     "lsl": 0.245, "usl": 0.255},
]


def _csv(rows, name: str = "upload.csv") -> io.BytesIO:
    buf = io.BytesIO(pd.DataFrame(rows).to_csv(index=False).encode())
    buf.name = name  # mimic a Streamlit UploadedFile
    return buf


def _csv_from_frame(frame: pd.DataFrame, name: str = "upload.csv") -> io.BytesIO:
    buf = io.BytesIO(frame.to_csv(index=False).encode())
    buf.name = name
    return buf


# --- schema wiring -----------------------------------------------------------


def test_required_columns_are_the_universal_three():
    # sample_size is NOT required — it is only meaningful for p/u charts, so demanding
    # it would reject valid continuous-measurement / capability uploads.
    assert SPC_SCHEMA.required_columns == ("stream", "subgroup", "value")


def test_ingest_error_is_value_error():
    assert issubclass(IngestError, ValueError)


# --- happy paths -------------------------------------------------------------


def test_valid_upload_passes_and_returns_frame():
    out = load_spc_csv(_csv(GOOD_ROWS))
    assert list(out["stream"].unique()) == ["ply_thickness"]
    assert len(out) == 3


def test_demo_dataset_validates_as_a_template():
    # The bundled demo (every stream: variable + p/u/c attribute) is the documented
    # upload template, so it must pass the schema unchanged.
    out = load_spc_csv(_csv_from_frame(generate_demo_dataset()))
    assert set(out["chart_type"].unique()) >= {"xbar_r", "imr", "p", "u", "c"}


def test_optional_limits_may_be_blank():
    rows = [{"stream": "panel_defects", "subgroup": i, "value": 6, "sample_size": 1}
            for i in range(1, 4)]  # no lsl/usl columns at all
    assert len(load_spc_csv(_csv(rows))) == 3


def test_extra_columns_are_ignored():
    rows = [{**r, "parameter": "Ply", "chart_type": "xbar_r", "note": "x"} for r in GOOD_ROWS]
    assert len(load_spc_csv(_csv(rows))) == 3


# --- malformed paths ---------------------------------------------------------


def test_missing_required_column_is_friendly():
    rows = [{"stream": "p", "subgroup": 1, "sample_size": 5} for _ in range(2)]  # no value
    with pytest.raises(IngestError, match=r"Missing required column\(s\): \['value'\]"):
        load_spc_csv(_csv(rows))


def test_sample_size_is_optional():
    # A continuous-measurement upload (no sample_size column) must pass — Xbar/I-MR/
    # capability never read sample_size.
    rows = [{"stream": "ply", "subgroup": i, "value": 0.25 + i * 0.001} for i in range(1, 4)]
    assert len(load_spc_csv(_csv(rows))) == 3


def test_infinite_value_rejected():
    rows = [{"stream": "ply", "subgroup": 1, "value": float("inf"), "sample_size": 5}]
    with pytest.raises(IngestError) as exc:
        load_spc_csv(_csv(rows))
    assert "value" in str(exc.value)


def test_non_numeric_value_is_row_addressed():
    rows = [
        {"stream": "ply", "subgroup": 1, "value": 0.25, "sample_size": 5},
        {"stream": "ply", "subgroup": 2, "value": "oops", "sample_size": 5},
    ]
    with pytest.raises(IngestError) as exc:
        load_spc_csv(_csv(rows))
    msg = str(exc.value)
    assert "Row 3" in msg  # header is row 1
    assert "value" in msg


def test_blank_value_is_addressed_not_nan():
    rows = [{"stream": "ply", "subgroup": 1, "value": float("nan"), "sample_size": 5}]
    with pytest.raises(IngestError) as exc:
        load_spc_csv(_csv(rows))
    msg = str(exc.value)
    assert "value" in msg
    assert "nan" not in msg.lower()  # NaN normalised to None, not echoed as "nan"


def test_subgroup_below_one_rejected():
    rows = [{"stream": "ply", "subgroup": 0, "value": 0.25, "sample_size": 5}]
    with pytest.raises(IngestError, match="subgroup"):
        load_spc_csv(_csv(rows))


def test_blank_stream_rejected():
    rows = [{"stream": "  ", "subgroup": 1, "value": 0.25, "sample_size": 5}]
    with pytest.raises(IngestError, match="stream"):
        load_spc_csv(_csv(rows))


def test_empty_upload_is_friendly():
    empty = pd.DataFrame(columns=["stream", "subgroup", "value", "sample_size"])
    with pytest.raises(IngestError, match="at least one"):
        load_spc_csv(_csv_from_frame(empty))
