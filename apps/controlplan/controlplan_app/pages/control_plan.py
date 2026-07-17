"""Control Plan page — validated ingest scaffold.

Uploads a Control Plan CSV (``characteristic, lsl, usl, target,
measurement_method, sample_size, frequency, recommended_chart, reaction_plan``)
through the shared validated-ingest boundary and previews the validated rows.
FMEA → Control Plan mapping/derivation (W06-2) and the authoring/editing UI
(W06-3) land in later issues; this page only proves the ingest surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd
import streamlit as st

from controlplan_app.schema import IngestError, load_control_plan_csv

TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "data" / "control_plan_template.csv"


def load_uploaded_control_plan(uploaded_file: str | BinaryIO) -> pd.DataFrame:
    """Route an upload through the shared validated-ingest boundary.

    A malformed CSV raises :class:`IngestError`, surfaced as a friendly message by
    :func:`render_control_plan`.
    """
    return load_control_plan_csv(uploaded_file)


def render_control_plan() -> None:
    st.title("Control Plan")
    st.caption(
        "Upload a Control Plan CSV to validate it. FMEA-derived characteristics "
        "and an authoring UI land in later issues."
    )

    with st.sidebar:
        st.header("Upload")
        upload = st.file_uploader("Upload Control Plan CSV", type=["csv"])
        st.download_button(
            "Download CSV template",
            data=TEMPLATE_PATH.read_bytes(),
            file_name="control_plan_template.csv",
            mime="text/csv",
        )

    if upload is None:
        st.info(
            "Upload a CSV with columns `characteristic, lsl, usl, target, "
            "measurement_method, sample_size, frequency, recommended_chart, "
            "reaction_plan`, or download the template to see the expected shape."
        )
        return

    try:
        frame = load_uploaded_control_plan(upload)
    except IngestError as exc:
        st.error(str(exc))
        st.stop()

    st.success(f"Validated {len(frame)} rows, including any tolerance/chart columns present.")
    st.dataframe(frame)
    st.info(
        "FMEA → Control Plan mapping (W06-2) and the authoring UI (W06-3) land "
        "in later issues."
    )
