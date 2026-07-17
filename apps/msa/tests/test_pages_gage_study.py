"""Tests for the Gage R&R page wiring (ingest seam + tolerance params object).

Follows the SPC page-test pattern (apps/spc/tests/test_pages_control_charts.py):
exercise the page-level helpers directly rather than running a full Streamlit
render, so the ingest/branch wiring is covered without a Streamlit runtime.
"""

from __future__ import annotations

import io

import pandas as pd
import pytest
from msa_app.pages import render_gage_study
from msa_app.pages.gage_study import (
    TEMPLATE_PATH,
    Tolerance,
    load_uploaded_study,
)
from msa_app.schema import IngestError

GOOD_ROWS = [
    {"part": "P01", "appraiser": "A", "trial": 1, "measurement": 10.054},
    {"part": "P01", "appraiser": "A", "trial": 2, "measurement": 10.048},
]


def _csv(rows) -> io.BytesIO:
    buf = io.BytesIO(pd.DataFrame(rows).to_csv(index=False).encode())
    buf.name = "upload.csv"
    return buf


# --- mountability ------------------------------------------------------------


def test_render_gage_study_is_importable_and_callable():
    assert callable(render_gage_study)


def test_template_path_exists():
    assert TEMPLATE_PATH.is_file()


# --- ingest seam -------------------------------------------------------------


def test_load_uploaded_study_happy_path():
    out = load_uploaded_study(_csv(GOOD_ROWS))
    assert len(out) == 2


def test_load_uploaded_study_raises_ingest_error_on_malformed():
    bad = [{"part": "  ", "appraiser": "A", "trial": 1, "measurement": 10.0}]
    with pytest.raises(IngestError):
        load_uploaded_study(_csv(bad))


# --- Tolerance params object -------------------------------------------------


def test_tolerance_ok_when_usl_above_lsl():
    assert Tolerance(usl=10.0, lsl=1.0).problem() is None


def test_tolerance_ok_when_bounds_unset():
    assert Tolerance().problem() is None
    assert Tolerance(usl=5.0).problem() is None
    assert Tolerance(lsl=5.0).problem() is None


def test_tolerance_problem_when_usl_not_above_lsl():
    note = Tolerance(usl=1.0, lsl=1.0).problem()
    assert note is not None
    assert "USL must be greater than LSL" in note
    assert Tolerance(usl=1.0, lsl=5.0).problem() is not None
