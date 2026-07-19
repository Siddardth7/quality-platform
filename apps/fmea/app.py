"""
app.py
FMEA Risk Prioritization Tool — Streamlit Web Application (orchestrator)

Author: Siddardth | M.S. Aerospace Engineering, UIUC
Engineering reference: AIAG FMEA-4 + AIAG/VDA FMEA Handbook (5th Ed., 2019)
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st
from quality_core.io import read_table

from fmea_app import __version__
from fmea_app.ap_engine import BASIS_AP, calculate_ap, rank_by_ap
from fmea_app.rpn_engine import (
    dataframe_to_relational,
    rank_by_rpn,
    run_pipeline,
    validate_input,
)
from ui import df_content_hash
from ui.charts import get_or_build_charts
from ui.components import (
    render_critical_panel,
    render_header,
    render_heatmap,
    render_insights,
    render_landing,
    render_metric_badges,
    render_pareto,
    render_rating_scales,
    render_table,
    render_validation_summary,
)
from ui.exports import render_export_buttons
from ui.filters import (
    apply_filters,
    render_basis_toggle,
    render_process_filter,
    render_rating_scale_selector,
    render_rpn_slider,
    render_severity_toggle,
)
from ui.relational import render_action_tracker, render_hierarchy
from ui.styles import apply_css

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEMO_CSV     = Path(__file__).parent / "data" / "composite_panel_fmea_demo.csv"
TEMPLATE_CSV = Path(__file__).parent / "data" / "fmea_input_template.csv"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB — see AUDIT_REPORT.md F-029


def _escape_source_label(name: str) -> str:
    """F-028: filenames flow into unsafe_allow_html markdown; escape first."""
    return html.escape(name, quote=True)


def _load_uploaded(file) -> pd.DataFrame:  # type: ignore[no-untyped-def]
    # Reuse the shared read boundary: CSV/Excel dispatch, the 20 MB size guard, and
    # friendly IngestError (a ValueError) messages now live once in quality_core.io.
    return read_table(file, max_bytes=MAX_UPLOAD_BYTES)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar():  # type: ignore[no-untyped-def]
    """Render sidebar controls.

    Returns (raw_df, rpn_min, sev9_only, dark, basis, scale_set).
    """
    st.sidebar.markdown(
        "<div style='padding:0.4rem 0 0.2rem; font-size:1.25rem; font-weight:700; "
        "letter-spacing:-0.3px;'>🛡️ FMEA Risk Analyzer</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.caption(f"Process FMEA · AIAG FMEA-4 · AIAG/VDA 2019 · v{__version__}")
    st.sidebar.divider()

    dark = st.sidebar.toggle(
        "🌙  Dark Mode",
        value=st.session_state.get("dark_mode", False),
        key="dark_mode",
    )

    st.sidebar.divider()
    st.sidebar.subheader("📂  Data Source")

    uploaded = st.sidebar.file_uploader(
        "Upload FMEA file",
        type=["csv", "xlsx"],
        key="fmea_uploader",     # F-019: explicit key so demo-button can clear it
        help=(
            "CSV or Excel with 11 columns: ID, Process_Step, Component, "
            "Function, Failure_Mode, Effect, Severity, Cause, "
            "Occurrence, Current_Control, Detection  |  S/O/D must be integers 1–10"
        ),
    )
    use_demo = st.sidebar.button(
        "▶  Use Demo Dataset",
        help="Load 30-row composite panel aerospace FMEA",
        use_container_width=True,
    )

    if use_demo:
        st.session_state["use_demo"] = True
        uploaded = None  # F-019: shadow the uploader so elif below cannot flip demo off
    elif uploaded is not None:
        st.session_state["use_demo"] = False

    raw_df       = None
    source_label = None
    source_ok    = False

    if uploaded and not st.session_state.get("use_demo"):
        try:
            raw_df       = _load_uploaded(uploaded)
            source_label = uploaded.name
            source_ok    = True
        except Exception as exc:
            st.sidebar.error(f"Failed to load: {exc}")
    elif st.session_state.get("use_demo"):
        raw_df       = pd.read_csv(DEMO_CSV)
        source_label = "Demo: composite panel FMEA (30 rows)"
        source_ok    = True

    if source_label:
        dot  = "🟢" if source_ok else "🔴"
        safe = _escape_source_label(source_label)
        label = safe[:42] + "…" if len(safe) > 44 else safe
        st.sidebar.markdown(
            f"<div style='font-size:0.82rem; padding:6px 10px; border-radius:6px; "
            f"background:rgba(39,174,96,0.08); border:1px solid rgba(39,174,96,0.25); "
            f"color:#1e7e45; margin-top:4px;'>"
            f"{dot} <b>{label}</b></div>",
            unsafe_allow_html=True,
        )

    st.sidebar.divider()
    st.sidebar.subheader("🎯  Prioritization")
    basis = render_basis_toggle()

    st.sidebar.divider()
    st.sidebar.subheader("📐  Rating Scale")
    scale_set = render_rating_scale_selector()

    st.sidebar.divider()
    st.sidebar.subheader("🔧  Filters")

    rpn_min   = render_rpn_slider()
    sev9_only = render_severity_toggle()

    return raw_df, rpn_min, sev9_only, dark, basis, scale_set


# ---------------------------------------------------------------------------
# SPC -> FMEA candidate feedback panel (W07-2, #89)
# ---------------------------------------------------------------------------

# ponytail: state-key string duplicated (not imported) from
# spc_app.fmea_feedback.FEEDBACK_STATE_KEY — mirrors how
# controlplan_app/pages/control_plan_config.py duplicates PLAN_STATE_KEY, so
# standalone FMEA never needs spc_app on sys.path (OQ4).
_SPC_FEEDBACK_STATE_KEY = "_spc_fmea_feedback"


def _render_spc_feedback_panel() -> None:
    """Read-only candidate panel: an SPC out-of-control signal on a monitored
    characteristic surfaces its source cause, current occurrence, OOC evidence,
    and a candidate occurrence suggestion — never applied automatically. Reads
    the feedback as a plain dict (no ``spc_app`` import), so this is a no-op
    (and standalone FMEA is unaffected) whenever the key is absent.
    """
    feedback = st.session_state.get(_SPC_FEEDBACK_STATE_KEY)
    if not isinstance(feedback, dict):
        return

    with st.expander("📈  SPC → FMEA feedback (candidate — not applied)", expanded=True):
        st.info(str(feedback.get("capa_prompt", "")))
        st.caption(
            f"Characteristic: {feedback.get('characteristic')} · "
            f"Stream: {feedback.get('stream')} · Rule set: {feedback.get('rule_set')}"
        )
        cols = st.columns(3)
        cols[0].metric("Current Occurrence", feedback.get("current_occurrence") or "unknown")
        cols[1].metric("Candidate Occurrence", feedback.get("suggested_occurrence") or "—")
        cols[2].metric("Violating Points", feedback.get("violating_points", "—"))
        rules = feedback.get("rules") or []
        source_cause = feedback.get("source_cause_description") or (
            "(unlinked — characteristic not found in the Control Plan source index)"
        )
        st.caption(
            f"Rules triggered: {', '.join(rules) if rules else '—'} · "
            f"Source cause: {source_cause}"
        )


# ---------------------------------------------------------------------------
# Mountable page body
# ---------------------------------------------------------------------------

def render_fmea() -> None:
    """Draw the full FMEA page into the *current* Streamlit container.

    This is the mountable render callable consumed by the unified platform shell
    (``app.py`` at the repo root). It owns no ``set_page_config`` — the host sets
    that once. The thin standalone wrapper ``main()`` below supplies page config
    for ``streamlit run app.py``.
    """
    raw_df, rpn_min, sev9_only, dark, basis, scale_set = render_sidebar()

    apply_css(dark)
    render_header()
    _render_spc_feedback_panel()

    if raw_df is None:
        st.sidebar.divider()
        st.sidebar.caption(
            "Engineering ref: AIAG FMEA-4 (4th Ed.) + "
            "AIAG/VDA FMEA Handbook (5th Ed., 2019)"
        )
        render_landing(TEMPLATE_CSV)
        st.divider()
        render_rating_scales(scale_set)
        return

    # ── Validate ─────────────────────────────────────────────────────────
    try:
        validate_input(raw_df)
    except ValueError as exc:
        st.error(f"**Input validation failed:** {exc}")
        st.stop()

    # ── Pipeline (memoized — only reruns when raw data changes) ──────────
    raw_hash = df_content_hash(raw_df)
    if st.session_state.get("_pipeline_cache_key") != raw_hash:
        try:
            df_analyzed = calculate_ap(run_pipeline(raw_df))
            st.session_state["_pipeline_cache_key"] = raw_hash
            st.session_state["_pipeline_result"] = df_analyzed
            st.session_state["_dataset_rpn_max"] = int(df_analyzed["RPN"].max())
            # Flat upload auto-converts to the relational view (W05-5) via the
            # shared adapter, so both entry paths share one model.
            st.session_state["_relational_model"] = dataframe_to_relational(raw_df)
        except (ValueError, KeyError) as exc:
            st.error(f"**Pipeline error:** {exc}")
            st.stop()
    else:
        df_analyzed = st.session_state["_pipeline_result"]
    relational_model = st.session_state["_relational_model"]

    render_validation_summary(df_analyzed)

    # ── Process step filter (sidebar, needs data first) ───────────────────
    process_steps = render_process_filter(df_analyzed)

    # Sidebar footer
    st.sidebar.divider()
    st.sidebar.caption(
        "Engineering ref: AIAG FMEA-4 (4th Ed.) + "
        "AIAG/VDA FMEA Handbook (5th Ed., 2019)"
    )

    # ── Apply filters ─────────────────────────────────────────────────────
    df_filtered = apply_filters(df_analyzed, rpn_min, sev9_only, process_steps)

    # ── Rank by the selected basis ────────────────────────────────────────
    # run_pipeline leaves the data RPN-ranked; re-rank by AP when the user
    # selects that basis so the table, critical panel, and exports all reflect
    # the chosen prioritization.
    if basis == BASIS_AP and "AP" in df_filtered.columns:
        df_filtered = rank_by_ap(df_filtered)
    else:
        df_filtered = rank_by_rpn(df_filtered)

    # ── Build / cache charts ──────────────────────────────────────────────
    pareto_fig, heatmap_fig = get_or_build_charts(
        df_filtered, rpn_min, sev9_only, process_steps, dark
    )

    # ── Dashboard ─────────────────────────────────────────────────────────
    render_metric_badges(df_filtered, basis)
    render_insights(df_filtered)
    st.divider()

    (
        tab_table, tab_pareto, tab_heatmap, tab_critical,
        tab_relational, tab_actions, tab_scale,
    ) = st.tabs([
        "📋  Risk Table",
        "📊  Pareto Chart",
        "🗺️  Risk Heatmap",
        "⚠️  Critical Items",
        "🧬  Relational",
        "🎯  Actions",
        "📐  Rating Scale",
    ])

    with tab_table:
        render_table(df_filtered, dark, basis)

    with tab_pareto:
        render_pareto(pareto_fig)

    with tab_heatmap:
        render_heatmap(heatmap_fig)

    with tab_critical:
        render_critical_panel(df_filtered, basis)

    with tab_relational:
        render_hierarchy(relational_model)

    with tab_actions:
        render_action_tracker(relational_model)

    with tab_scale:
        render_rating_scales(scale_set)

    st.divider()
    render_export_buttons(df_filtered, rpn_min, sev9_only, process_steps)


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Standalone entry: own the page chrome, then render the FMEA body."""
    st.set_page_config(
        page_title="FMEA Risk Analyzer",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    render_fmea()


if __name__ == "__main__":
    main()
