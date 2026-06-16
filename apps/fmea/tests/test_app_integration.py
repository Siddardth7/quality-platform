"""
App-level integration tests using Streamlit's AppTest harness.
These tests exercise the full app surface: upload, filters, exports, and error handling.
"""
import io
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP_PY = str(Path(__file__).parent.parent / "app.py")


def test_demo_dataset_loads():
    """Demo dataset button loads successfully and renders metrics."""
    at = AppTest.from_file(APP_PY).run()
    at.session_state["use_demo"] = True
    at = at.run()
    assert len(at.error) == 0


def test_demo_renders_without_exception():
    """Full demo path runs without raising an exception."""
    at = AppTest.from_file(APP_PY).run()
    at.session_state["use_demo"] = True
    at = at.run(timeout=30)
    assert not at.exception


def test_landing_renders_rating_scale_without_exception():
    """W03-4: the landing page (no data) renders the rating-scale reference."""
    at = AppTest.from_file(APP_PY).run()
    assert not at.exception


def test_ap_basis_renders_without_exception():
    """W03-3: switching the prioritization basis to AP renders cleanly and
    leaves the AP-ranked result in the pipeline cache."""
    at = AppTest.from_file(APP_PY).run()
    at.session_state["use_demo"] = True
    at.session_state["priority_basis"] = "AP"
    at = at.run(timeout=30)
    assert not at.exception
    assert "AP" in at.session_state["_pipeline_result"].columns


def test_malformed_float_score_shows_error():
    """Uploading a file with float S/O/D scores shows an error, does not crash."""
    from fmea_app.rpn_engine import validate_input
    df = pd.DataFrame([{
        "ID": 1, "Process_Step": "Stamping", "Component": "Panel",
        "Function": "Structural support", "Failure_Mode": "Crack",
        "Effect": "Part failure", "Severity": 8.5,
        "Cause": "Over-stress", "Occurrence": 3,
        "Current_Control": "Visual inspection", "Detection": 4,
    }])
    with pytest.raises(ValueError, match="integer"):
        validate_input(df)


def test_null_process_step_rejected_at_boundary():
    """Null Process_Step is caught at validation, not at filter time."""
    from fmea_app.rpn_engine import validate_input
    df = pd.DataFrame([{
        "ID": 1, "Process_Step": None, "Component": "Panel",
        "Function": "Structural support", "Failure_Mode": "Crack",
        "Effect": "Part failure", "Severity": 8,
        "Cause": "Over-stress", "Occurrence": 3,
        "Current_Control": "Visual inspection", "Detection": 4,
    }])
    with pytest.raises(ValueError, match="Process_Step"):
        validate_input(df)


def test_formula_prefixed_strings_not_stored_as_formulas():
    """Formula-injection strings are escaped in Excel export."""
    import openpyxl

    from fmea_app.exporter import export_excel
    from fmea_app.rpn_engine import run_pipeline
    df = pd.DataFrame([{
        "ID": 1, "Process_Step": "Stamping", "Component": "Panel",
        "Function": "Structural support", "Failure_Mode": "=2+2",
        "Effect": "+bad", "Severity": 8,
        "Cause": "Over-stress", "Occurrence": 3,
        "Current_Control": "Visual inspection", "Detection": 4,
    }])
    result_df = run_pipeline(df)
    raw = export_excel(result_df)
    wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=False)
    ws = wb.active
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            assert cell.data_type != "f", f"Formula found in cell {cell.coordinate}"


def test_oversized_upload_rejected_with_friendly_error():
    """F-029 regression: an uploaded file above MAX_UPLOAD_BYTES must be
    rejected with a ValueError carrying a user-friendly message."""
    import pytest

    from app import MAX_UPLOAD_BYTES, _load_uploaded

    class _FakeUpload:
        def __init__(self, size, name="huge.csv"):
            self.size = size
            self.name = name

    with pytest.raises(ValueError, match="exceeds"):
        _load_uploaded(_FakeUpload(size=MAX_UPLOAD_BYTES + 1))
