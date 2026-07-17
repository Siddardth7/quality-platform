"""Tests for the Control Plan page wiring (ingest seam), mirroring
``apps/msa/tests/test_pages_gage_study.py`` — exercise the page-level helpers
directly rather than running a full Streamlit render, so the ingest/branch wiring
is covered without a Streamlit runtime.
"""

from __future__ import annotations

import io

import pandas as pd
import pytest
from controlplan_app.pages import render_control_plan
from controlplan_app.pages.control_plan import (
    TEMPLATE_PATH,
    load_uploaded_control_plan,
)
from controlplan_app.schema import IngestError

GOOD_ROWS = [
    {
        "characteristic": "Bore Diameter",
        "measurement_method": "Bore gauge",
        "sample_size": 5,
        "frequency": "per shift",
        "reaction_plan": "Stop line; notify quality engineer.",
    }
]


def _csv(rows) -> io.BytesIO:
    buf = io.BytesIO(pd.DataFrame(rows).to_csv(index=False).encode())
    buf.name = "upload.csv"
    return buf


# --- mountability --------------------------------------------------------------


def test_render_control_plan_is_importable_and_callable():
    assert callable(render_control_plan)


def test_template_path_exists():
    assert TEMPLATE_PATH.is_file()


# --- ingest seam -----------------------------------------------------------------


def test_load_uploaded_control_plan_happy_path():
    out = load_uploaded_control_plan(_csv(GOOD_ROWS))
    assert len(out) == 1


def test_load_uploaded_control_plan_raises_ingest_error_on_malformed():
    bad = [{**GOOD_ROWS[0], "characteristic": "   "}]
    with pytest.raises(IngestError):
        load_uploaded_control_plan(_csv(bad))
