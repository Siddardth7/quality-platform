"""Tests for the Control Plan page's FMEA-ingest -> connector -> review/edit
seam, mirroring apps/msa/tests/test_pages_gage_study.py: exercise the
page-level helpers directly rather than running a full Streamlit render.

Rewritten for the W06-3 (#85) page rewrite — the old scaffold helpers
(`load_uploaded_control_plan`) no longer exist; this now covers
`load_uploaded_fmea` and `validate_edited_plan`.
"""

from __future__ import annotations

import io

import pandas as pd
import pydantic
import pytest
from controlplan_app.pages import render_control_plan
from controlplan_app.pages.control_plan import (
    DEMO_PATH,
    TEMPLATE_PATH,
    load_uploaded_fmea,
    validate_edited_plan,
)
from quality_core.io import IngestError

GOOD_FMEA_ROW = {
    "ID": 1,
    "Process_Step": "Layup",
    "Component": "Ply",
    "Function": "Provide stiffness",
    "Failure_Mode": "Misalignment",
    "Effect": "Reduced strength",
    "Severity": 8,
    "Cause": "Operator error",
    "Occurrence": 4,
    "Current_Control": "Visual inspection",
    "Detection": 5,
}


def _csv(rows: list[dict]) -> io.BytesIO:
    buf = io.BytesIO(pd.DataFrame(rows).to_csv(index=False).encode())
    buf.name = "upload.csv"
    return buf


GOOD_PLAN_ROW = {
    "characteristic": "Bore Diameter",
    "lsl": 9.9,
    "usl": 10.1,
    "target": 10.0,
    "measurement_method": "Bore gauge",
    "sample_size": 5,
    "frequency": "per shift",
    "recommended_chart": "Xbar-R",
    "reaction_plan": "Stop line; notify quality engineer.",
}


def _plan_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# --- mountability --------------------------------------------------------------


def test_render_control_plan_is_importable_and_callable():
    assert callable(render_control_plan)


def test_template_path_exists():
    assert TEMPLATE_PATH.is_file()


def test_demo_path_exists():
    assert DEMO_PATH.is_file()


# --- FMEA ingest seam ------------------------------------------------------------


def test_load_uploaded_fmea_happy_path():
    relational = load_uploaded_fmea(_csv([GOOD_FMEA_ROW]))
    assert len(relational.functions) >= 1


def test_load_uploaded_fmea_demo_path():
    relational = load_uploaded_fmea(str(DEMO_PATH))
    assert len(relational.functions) >= 1


def test_load_uploaded_fmea_raises_ingest_error_on_bad_upload():
    bad = [{**GOOD_FMEA_ROW, "Process_Step": "   "}]
    with pytest.raises(IngestError):
        load_uploaded_fmea(_csv(bad))


def test_load_uploaded_fmea_raises_ingest_error_on_out_of_range_severity():
    bad = [{**GOOD_FMEA_ROW, "Severity": 11}]
    with pytest.raises(IngestError):
        load_uploaded_fmea(_csv(bad))


def test_load_uploaded_fmea_raises_ingest_error_on_duplicate_id():
    dup = [GOOD_FMEA_ROW, {**GOOD_FMEA_ROW, "ID": 1}]
    with pytest.raises(IngestError):
        load_uploaded_fmea(_csv(dup))


# --- edited-plan re-validation (trust boundary) ---------------------------------


def test_validate_edited_plan_accepts_valid_rows():
    validated = validate_edited_plan(_plan_df([GOOD_PLAN_ROW]))
    assert len(validated.rows) == 1


def test_validate_edited_plan_rejects_blank_required_cell():
    bad = {**GOOD_PLAN_ROW, "characteristic": "   "}
    with pytest.raises(pydantic.ValidationError):
        validate_edited_plan(_plan_df([bad]))


def test_validate_edited_plan_rejects_sample_size_below_one():
    bad = {**GOOD_PLAN_ROW, "sample_size": 0}
    with pytest.raises(pydantic.ValidationError):
        validate_edited_plan(_plan_df([bad]))


def test_validate_edited_plan_rejects_usl_not_above_lsl():
    bad = {**GOOD_PLAN_ROW, "lsl": 10.1, "usl": 10.1}
    with pytest.raises(pydantic.ValidationError):
        validate_edited_plan(_plan_df([bad]))


def test_validate_edited_plan_rejects_target_out_of_band():
    bad = {**GOOD_PLAN_ROW, "target": 20.0}
    with pytest.raises(pydantic.ValidationError):
        validate_edited_plan(_plan_df([bad]))


def test_validate_edited_plan_rejects_invalid_recommended_chart():
    bad = {**GOOD_PLAN_ROW, "recommended_chart": "np"}
    with pytest.raises(pydantic.ValidationError):
        validate_edited_plan(_plan_df([bad]))


def test_validate_edited_plan_rejects_duplicate_characteristic():
    with pytest.raises(pydantic.ValidationError):
        validate_edited_plan(_plan_df([GOOD_PLAN_ROW, GOOD_PLAN_ROW]))


def test_validate_edited_plan_accepts_null_optional_fields():
    """lsl/usl/target/recommended_chart are nullable — NaN from an editor cell
    (pd.isna) must resolve to None, not be rejected."""
    row = {**GOOD_PLAN_ROW, "lsl": None, "usl": None, "target": None, "recommended_chart": None}
    validated = validate_edited_plan(_plan_df([row]))
    assert validated.rows[0].lsl is None
