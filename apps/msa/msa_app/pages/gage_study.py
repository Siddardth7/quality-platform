"""Gage R&R study page — validated ingest scaffold.

Uploads a crossed gage-study CSV (``part, appraiser, trial, measurement``) through
the shared validated-ingest boundary and previews the validated rows. Study-level
tolerance (USL/LSL) is captured here as number inputs and held in a typed
:class:`Tolerance` params object — it is not a CSV column and is not consumed by any
math in this scaffold. The Gage R&R computation (%GRR, ndc, AIAG verdict) lands in a
later issue; this page only proves the ingest + tolerance surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import streamlit as st

from msa_app.schema import IngestError, load_gage_study_csv

TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "data" / "gage_rr_template.csv"


@dataclass(frozen=True)
class Tolerance:
    """Study-level tolerance captured from the page inputs (not a CSV column).

    Either bound may be unset (``None``). The tolerance is not consumed by any
    computation in this scaffold; it is validated only for internal consistency.
    """

    usl: float | None = None
    lsl: float | None = None

    def problem(self) -> str | None:
        """Return a friendly note if both bounds are set but inconsistent, else None."""
        if self.usl is not None and self.lsl is not None and self.usl <= self.lsl:
            return "USL must be greater than LSL — tolerance ignored until corrected."
        return None


def load_uploaded_study(uploaded_file: str | BinaryIO) -> pd.DataFrame:
    """Route an upload through the shared validated-ingest boundary.

    A malformed CSV raises :class:`IngestError`, surfaced as a friendly message by
    :func:`render_gage_study`.
    """
    return load_gage_study_csv(uploaded_file)


def render_gage_study() -> None:
    st.title("Gage R&R")
    st.caption(
        "Measurement System Analysis — upload a crossed gage study "
        "(part x appraiser x trial) to validate it. Gage R&R computation lands in a later issue."
    )

    with st.sidebar:
        st.header("Study Setup")
        usl_on = st.checkbox("Set upper spec limit (USL)")
        usl = st.number_input("USL", value=0.0, disabled=not usl_on) if usl_on else None
        lsl_on = st.checkbox("Set lower spec limit (LSL)")
        lsl = st.number_input("LSL", value=0.0, disabled=not lsl_on) if lsl_on else None
        upload = st.file_uploader("Upload gage study CSV", type=["csv"])
        st.download_button(
            "Download CSV template",
            data=TEMPLATE_PATH.read_bytes(),
            file_name="gage_rr_template.csv",
            mime="text/csv",
        )

    tolerance = Tolerance(usl=usl, lsl=lsl)
    note = tolerance.problem()
    if note is not None:
        st.warning(note)

    if upload is None:
        st.info(
            "Upload a CSV with columns `part, appraiser, trial, measurement`, or "
            "download the template to see the expected shape."
        )
        return

    try:
        frame = load_uploaded_study(upload)
    except IngestError as exc:
        st.error(str(exc))
        st.stop()

    st.success(f"Validated {len(frame)} measurements.")
    st.dataframe(frame)
    st.info("Gage R&R computation (%GRR, ndc, AIAG verdict) lands in a later issue.")
