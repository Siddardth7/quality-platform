"""Gage R&R study page — validated ingest + computation (W08-2).

Uploads a crossed gage-study CSV (``part, appraiser, trial, measurement``) through
the shared validated-ingest boundary, captures study-level tolerance (USL/LSL) as
page inputs, and computes the Gage R&R metrics using the Average-and-Range method
(AIAG MSA, 4th Edition). Displays Repeatability (EV), Reproducibility (AV), %GRR,
ndc, and the AIAG verdict (Accept/Marginal/Reject).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import streamlit as st

from msa_app.gage_rr_engine import compute_gage_rr
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
        "(part × appraiser × trial) to validate and analyze it per AIAG MSA standards."
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
        return

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
    st.dataframe(frame, use_container_width=True)

    # Compute tolerance (only if both USL and LSL are set)
    tolerance_value = None
    if usl is not None and lsl is not None:
        tolerance_value = usl - lsl

    # Run Gage R&R computation
    try:
        results = compute_gage_rr(frame, tolerance=tolerance_value)
    except ValueError as exc:
        st.error(f"Gage R&R computation failed: {exc}")
        st.stop()

    # Display results
    st.header("Gage R&R Results")

    # Metrics columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("EV (Repeatability)", f"{results['ev']:.6f}")
    with col2:
        st.metric("AV (Reproducibility)", f"{results['av']:.6f}")
    with col3:
        st.metric("GR&R", f"{results['grr']:.6f}")
    with col4:
        st.metric("TV (Total Variation)", f"{results['tv']:.6f}")

    # %GRR and verdict
    col1, col2 = st.columns(2)
    with col1:
        st.metric("%GRR vs Study", f"{results['pgrr_study']:.2f}%")
        st.metric("PV (Part Variation)", f"{results['pv']:.6f}")
        if results['pgrr_tolerance'] is not None:
            st.metric("%GRR vs Tolerance", f"{results['pgrr_tolerance']:.2f}%")
    with col2:
        st.metric("Distinct Categories (ndc)", results['ndc'])
        verdict = results['verdict']
        verdict_color = {
            "Accept": "🟢",
            "Marginal": "🟡",
            "Reject": "🔴",
        }.get(verdict, "⚪")
        st.metric("AIAG Verdict", f"{verdict_color} {verdict}")

    # Study design summary
    st.subheader("Study Design")
    design_col1, design_col2, design_col3, design_col4 = st.columns(4)
    with design_col1:
        st.metric("Parts", results['n_parts'])
    with design_col2:
        st.metric("Appraisers", results['n_appraisers'])
    with design_col3:
        st.metric("Trials per Cell", results['n_trials'])
    with design_col4:
        is_balanced_str = "✓ Balanced" if results['is_balanced'] else "⚠ Unbalanced"
        st.metric("Data", is_balanced_str)

    # Interpretation guide
    st.subheader("AIAG Acceptance Criteria")
    criteria_text = """
    **Accept:** ndc ≥ 5 AND %GRR < 10%
    - Measurement system is adequate for the intended use.

    **Marginal:** 2 ≤ ndc < 5 OR 10% ≤ %GRR ≤ 30%
    - Acceptable for some uses; consider improvement plans.

    **Reject:** ndc < 2 OR %GRR > 30%
    - Measurement system is inadequate and must be improved.
    """
    st.info(criteria_text)

