"""
ui/filters.py
Sidebar filter rendering and DataFrame filtering for the FMEA Risk Analyzer.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from fmea_app.ap_engine import BASIS_AP, BASIS_RPN
from fmea_app.rating_scales import (
    RatingScaleSet,
    load_default_scales,
    load_scales_from_json,
)

_SCALE_AIAG = "AIAG FMEA-4 (default)"
_SCALE_CUSTOM = "Custom (upload JSON)"


def render_rating_scale_selector() -> RatingScaleSet:
    """Render the S/O/D rating-scale source picker. Returns the active scale set.

    Defaults to the bundled AIAG FMEA-4 scale. If the user picks Custom and
    uploads a valid JSON scale it is used; an invalid upload surfaces an error
    and the default is used so the rest of the app keeps working.
    """
    choice = st.sidebar.selectbox(
        "Rating scale",
        options=[_SCALE_AIAG, _SCALE_CUSTOM],
        key="rating_scale_choice",
        help="Reference 1–10 anchors for Severity / Occurrence / Detection. "
        "Custom lets you load a company-specific 1–10 rubric.",
    )

    if choice == _SCALE_CUSTOM:
        upload = st.sidebar.file_uploader(
            "Upload custom scale (JSON)",
            type=["json"],
            key="rating_scale_upload",
            help="JSON with severity/occurrence/detection objects, each mapping ratings 1–10 to text.",
        )
        if upload is not None:
            try:
                return load_scales_from_json(upload.getvalue())
            except ValueError as exc:
                st.sidebar.error(f"Custom scale rejected: {exc}")
        else:
            st.sidebar.caption("Upload a JSON scale, or the AIAG default is used.")

    return load_default_scales()


def render_basis_toggle() -> str:
    """Render the prioritization-basis selector. Returns "RPN" or "AP".

    RPN (Severity × Occurrence × Detection) is the classic AIAG FMEA-4 score;
    AP (Action Priority) is the AIAG/VDA 2019 High/Medium/Low replacement. The
    choice drives ranking, tiering, and the emphasized column app-wide.
    """
    return st.sidebar.radio(
        "Prioritization basis",
        options=[BASIS_RPN, BASIS_AP],
        horizontal=True,
        key="priority_basis",
        help=(
            "RPN = Severity × Occurrence × Detection (AIAG FMEA-4). "
            "AP = AIAG/VDA 2019 Action Priority (High/Medium/Low). "
            "Both columns stay visible; this sets which one ranks and tiers the view."
        ),
    )


def render_rpn_slider() -> int:
    _rpn_max = int(st.session_state.get("_dataset_rpn_max", 1000))
    _rpn_max = max(_rpn_max, 10)

    # F-020: session_state is source of truth once widget has a key; the value=
    # kwarg is ignored on reruns. Clamp the stored value before instantiating
    # the widget to prevent StreamlitAPIException when the dataset shrinks.
    current = int(st.session_state.get("rpn_slider", 0))
    st.session_state["rpn_slider"] = min(current, _rpn_max)

    return st.sidebar.slider(
        "Minimum RPN",
        min_value=0,
        max_value=_rpn_max,
        step=10,
        help="Show only failure modes with RPN ≥ this value (max reflects your dataset)",
        key="rpn_slider",
    )


def render_severity_toggle() -> bool:
    return st.sidebar.toggle(
        "Severity ≥ 9 only",
        value=False,
        help="Show only safety-critical failure modes",
        key="sev9_toggle",
    )


def render_process_filter(df: pd.DataFrame) -> list[str]:
    st.sidebar.divider()
    st.sidebar.subheader("📍  Process Steps")
    all_steps = sorted(df["Process_Step"].unique().tolist())
    selected = st.sidebar.multiselect(
        "Show steps",
        options=all_steps,
        default=all_steps,
        key="process_steps",
        help="Filter to specific manufacturing process steps",
    )
    if not selected:
        st.sidebar.caption("No steps selected — showing all.")
        return all_steps
    return selected


def apply_filters(
    df: pd.DataFrame,
    rpn_min: int,
    sev9_only: bool,
    process_steps: list[str],
) -> pd.DataFrame:
    filtered = df[df["RPN"] >= rpn_min]
    if sev9_only:
        filtered = filtered[filtered["Severity"] >= 9]
    if process_steps:
        filtered = filtered[filtered["Process_Step"].isin(process_steps)]
    return filtered
