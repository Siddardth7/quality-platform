from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, cast

import pandas as pd
import streamlit as st

from spc_app.control_plan_config import (
    PLAN_STATE_KEY,
    chart_type_index,
    config_for,
    plan_characteristics,
)
from spc_app.exporter import (
    ControlChartReport,
    build_control_chart_report_excel,
    build_control_chart_report_pdf,
)
from spc_app.fmea_feedback import (
    FEEDBACK_STATE_KEY,
    SOURCE_INDEX_STATE_KEY,
    build_occurrence_feedback,
)
from spc_app.schema import IngestError, load_spc_csv
from spc_app.spc_engine.constants import (
    CUSUM_DEFAULT_H,
    CUSUM_DEFAULT_K,
    EWMA_DEFAULT_L,
    EWMA_DEFAULT_LAMBDA,
)
from spc_app.spc_engine.control_charts import (
    CUSUMResult,
    EWMAResult,
    compute_c,
    compute_cusum,
    compute_ewma,
    compute_imr,
    compute_p,
    compute_u,
    compute_xbar_r,
    compute_xbar_s,
)
from spc_app.spc_engine.phase import (
    ExcludedPoint,
    FrozenLimits,
    freeze_imr,
    freeze_xbar_r,
    freeze_xbar_s,
)
from spc_app.spc_engine.rule_detection import detect_violations
from spc_app.spc_engine.utils import subgroup_rows
from spc_app.visualizer import build_control_chart, build_cusum_chart, build_ewma_chart

DEMO_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_composites_aerospace.csv"
RULE_REFERENCE = pd.DataFrame(
    [
        # The two sets are independent, each with its own numbering — selecting
        # one never emits the other's labels. The run-length rule differs on
        # purpose: Western Electric uses 8 in a row, Nelson Test 2 uses 9.
        ("Western Electric", "Rule 1", "1 point beyond +/-3 sigma"),
        ("Western Electric", "Rule 2", "2 of 3 consecutive beyond +/-2 sigma on the same side"),
        ("Western Electric", "Rule 3", "4 of 5 consecutive beyond +/-1 sigma on the same side"),
        ("Western Electric", "Rule 4", "8 consecutive points on the same side of the centerline"),
        ("Nelson", "Rule 1", "1 point beyond +/-3 sigma"),
        ("Nelson", "Rule 2", "9 consecutive points on the same side of the centerline"),
        ("Nelson", "Rule 3", "6 consecutive points trending up or down"),
        ("Nelson", "Rule 4", "14 consecutive points alternating up and down"),
        ("Nelson", "Rule 5", "2 of 3 consecutive beyond +/-2 sigma on the same side"),
        ("Nelson", "Rule 6", "4 of 5 consecutive beyond +/-1 sigma on the same side"),
        ("Nelson", "Rule 7", "15 consecutive points within +/-1 sigma of the centerline"),
        ("Nelson", "Rule 8", "8 consecutive points outside +/-1 sigma on both sides"),
    ],
    columns=["Rule Set", "Rule", "Description"],
)
CHART_OPTIONS = {
    "Xbar-R": {"stream": "ply_thickness", "compute": "xbar_r"},
    "Xbar-S": {"stream": "hole_diameter", "compute": "xbar_s"},
    "I-MR": {"stream": "autoclave_temp", "compute": "imr"},
    "p": {"stream": "reject_proportion", "compute": "p"},
    "u": {"stream": "surface_defects", "compute": "u"},
    "c": {"stream": "panel_defects", "compute": "c"},
    "EWMA": {"stream": "autoclave_temp", "compute": "ewma"},
    "CUSUM": {"stream": "autoclave_temp", "compute": "cusum"},
}
#: Demo-only bind of a Control Plan characteristic straight to its own real,
#: OOC monitored stream (OQ3, W07-2 #89) — (chart_key, stream key). Extend this
#: map when more demo characteristics get their own stream; every other
#: characteristic still falls back to the manual chart-type/stream pick above.
_CHARACTERISTIC_STREAM_OVERRIDE: dict[str, tuple[str, str]] = {
    "Prepreg Ply — Ply misalignment (>±2°)": ("Xbar-R", "ply_misalignment"),
}

#: Chart types that support the Phase I (establish & freeze) / Phase II
#: (monitor against frozen limits) workflow (W10-1, #141) — variables charts
#: with a well-defined center-line/dispersion pair. EWMA/CUSUM are their own
#: monitoring schemes and are excluded.
PHASE_ELIGIBLE = {"Xbar-R", "Xbar-S", "I-MR"}
_LIVE_MODE = "Live (recompute)"
_PHASE_I_MODE = "Phase I: establish & freeze"
_PHASE_II_MODE = "Phase II: monitor against frozen limits"


@st.cache_data
def load_demo_data() -> pd.DataFrame:
    if not DEMO_PATH.exists():
        from spc_app.spc_engine.data_generator import generate_demo_dataset
        DEMO_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate_demo_dataset().to_csv(DEMO_PATH, index=False)
    return pd.read_csv(DEMO_PATH)


def load_source_data(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        return load_demo_data()
    # Uploads go through the shared validated-ingest boundary; a malformed CSV
    # raises IngestError, surfaced as a friendly message by render_control_charts.
    return load_spc_csv(uploaded_file)


def _frozen_state_key(chart_key: str) -> str:
    return f"spc_frozen::{chart_key}"


def detect_rule_violations(
    chart_type: str, points: list[float], cl: float, sigma: float, rule_set: str
) -> list[dict[str, int | str]]:
    # Thin pass-through to the gated engine chokepoint so every branch below
    # routes through the same run-rule gate (EWMA/CUSUM always get []).
    return detect_violations(chart_type, points, cl, sigma, rule_set)


def summarize_metrics(chart_key: str, result: Mapping[str, Any]) -> list[tuple[str, str]]:
    if chart_key == "Xbar-R":
        return [
            ("Xbarbar", f"{result['xbarbar']:.4f}"),
            ("Rbar", f"{result['rbar']:.4f}"),
            ("Sigma Hat", f"{result['sigma_hat']:.4f}"),
        ]
    if chart_key == "Xbar-S":
        return [
            ("Xbarbar", f"{result['xbarbar']:.4f}"),
            ("Sbar", f"{result['sbar']:.4f}"),
            ("Sigma Hat", f"{result['sigma_hat']:.4f}"),
        ]
    if chart_key == "I-MR":
        return [
            ("Xbar", f"{result['xbar']:.4f}"),
            ("MRbar", f"{result['mrbar']:.4f}"),
            ("Sigma Hat", f"{result['sigma_hat']:.4f}"),
        ]
    if chart_key == "p":
        return [
            ("pbar", f"{result['pbar']:.4f}"),
            ("Avg N", f"{sum(result['sample_sizes']) / len(result['sample_sizes']):.1f}"),
            ("Points", str(len(result['proportions']))),
        ]
    if chart_key == "c":
        return [
            ("cbar", f"{result['cbar']:.4f}"),
            ("UCL", f"{result['ucl']:.4f}"),
            ("Points", str(len(result['counts']))),
        ]
    if chart_key == "u":
        return [
            ("ubar", f"{result['ubar']:.4f}"),
            ("Avg N", f"{sum(result['sample_sizes']) / len(result['sample_sizes']):.2f}"),
            ("Points", str(len(result['u_values']))),
        ]
    if chart_key == "EWMA":
        return [
            ("Lambda", f"{result['lam']:.4f}"),
            ("L", f"{result['L']:.4f}"),
            ("Sigma", f"{result['sigma']:.4f}"),
        ]
    return [
        ("k", f"{result['k']:.4f}"),
        ("h", f"{result['h']:.4f}"),
        ("Signals", str(len(result["signals"]))),
    ]


def render_control_charts() -> None:
    st.title("Control Charts")
    st.caption("Variables and attributes control charts with Western Electric and Nelson rule overlays.")

    plan_df = st.session_state.get(PLAN_STATE_KEY)
    cp_config = None
    selected = "(manual)"

    with st.sidebar:
        st.header("Controls")
        chart_options = list(CHART_OPTIONS.keys())
        preselect_index = 0
        if plan_df is not None and not plan_df.empty:
            names = plan_characteristics(plan_df)
            selected = st.selectbox("Characteristic (from Control Plan)", options=["(manual)", *names])
            if selected != "(manual)":
                cp_config = config_for(plan_df, selected)
                override = _CHARACTERISTIC_STREAM_OVERRIDE.get(selected)
                preselect_index = chart_type_index(
                    override[0] if override is not None else cp_config.chart_key, chart_options
                )
        chart_key = st.selectbox("Chart Type", options=chart_options, index=preselect_index)
        if cp_config is not None:
            st.info(
                f"Auto-configured from Control Plan: **{cp_config.characteristic}**\n\n"
                f"- LSL / USL / Target: {cp_config.lsl} / {cp_config.usl} / {cp_config.target}\n"
                f"- Sample size: {cp_config.sample_size}\n"
                f"- Frequency: {cp_config.frequency}"
            )

        phase_mode = _LIVE_MODE
        if chart_key in PHASE_ELIGIBLE:
            phase_mode = st.radio(
                "Phase Mode", options=[_LIVE_MODE, _PHASE_I_MODE, _PHASE_II_MODE]
            )

        lam, ewma_l, cusum_k, cusum_h, cusum_fir = (
            EWMA_DEFAULT_LAMBDA, EWMA_DEFAULT_L, CUSUM_DEFAULT_K, CUSUM_DEFAULT_H, False,
        )
        if chart_key == "EWMA":
            lam = st.number_input("Lambda (λ)", value=EWMA_DEFAULT_LAMBDA, min_value=0.01, max_value=1.0, step=0.01)
            ewma_l = st.number_input("L (limit width)", value=EWMA_DEFAULT_L, min_value=0.1, step=0.01)
        elif chart_key == "CUSUM":
            cusum_k = st.number_input("k (reference value)", value=CUSUM_DEFAULT_K, min_value=0.01, step=0.01)
            cusum_h = st.number_input("h (decision interval)", value=CUSUM_DEFAULT_H, min_value=0.1, step=0.1)
            cusum_fir = st.checkbox("FIR (fast initial response)", value=False)

        rule_set = "Western Electric"
        if chart_key not in ("EWMA", "CUSUM"):
            rule_set = st.radio("Rule Set", options=["Western Electric", "Nelson"], horizontal=True)
        source_mode = st.radio("Data Source", options=["Demo", "Upload CSV"], horizontal=True)
        upload = None
        if source_mode == "Upload CSV":
            upload = st.file_uploader("Upload CSV", type=["csv"])

    try:
        frame = load_source_data(upload if source_mode == "Upload CSV" else None)
    except IngestError as exc:
        st.error(str(exc))
        st.stop()
    config = CHART_OPTIONS[chart_key]
    # A known demo characteristic overrides which physical stream is charted
    # (OQ3, #89) when its bound chart type is the one currently selected;
    # every other characteristic (and manual mode) uses CHART_OPTIONS as-is.
    override = _CHARACTERISTIC_STREAM_OVERRIDE.get(selected) if selected != "(manual)" else None
    stream_key = override[1] if override is not None and override[0] == chart_key else config["stream"]
    stream_frame = frame[frame["stream"] == stream_key].copy()

    if stream_frame.empty:
        st.error("No rows available for the selected chart type.")
        st.stop()

    excluded_points: list[ExcludedPoint] = []
    if chart_key in PHASE_ELIGIBLE and phase_mode == _PHASE_I_MODE:
        # ponytail: baseline = the currently selected stream data (no separate
        # baseline-upload UI); a single documented cause applies to every point
        # marked for exclusion, which matches RULE 11's non-empty-cause guard.
        n_points = len(subgroup_rows(stream_frame)) if config["compute"] != "imr" else len(stream_frame)
        exclude_idx = st.multiselect("Exclude baseline points (assignable cause)", options=list(range(n_points)))
        cause = st.text_input("Documented cause for excluded points", value="")
        if exclude_idx and cause.strip():
            excluded_points = [{"index": i, "cause": cause} for i in exclude_idx]
        elif exclude_idx:
            st.warning("Provide a documented cause to exclude points.")

    # `result` is a runtime dispatch over chart type; each branch assigns a
    # different precisely-typed compute result, so the shared variable is the
    # honest read-only union surface. Engine functions keep their exact TypedDicts.
    # Each branch also lifts the plotted points + limits + violations into shared
    # locals so the figure is built once and the same values flow into the report.
    result: Mapping[str, Any]
    points: list[float]
    cl: float
    ucl: float | list[float]  # p/u/EWMA charts have per-point (vector) limits
    lcl: float | list[float]
    violations: list[dict[str, int | str]]
    chart_title: str
    y_axis: str
    # CUSUM's C- lower arm (positive accumulator) is the only branch that
    # populates this — every other chart type exports with the default None.
    secondary_points: tuple[str, list[float]] | None = None
    frozen_key = _frozen_state_key(chart_key)
    # The schema validates column/type shape; it can't guarantee a stream has enough
    # subgroups, or the sample_size column a p/u chart needs. Guard the compute so
    # those surface as a friendly message rather than a Streamlit stack trace.
    try:
        if config["compute"] in ("xbar_r", "xbar_s", "imr") and phase_mode == _PHASE_II_MODE:
            frozen = st.session_state.get(frozen_key)
            if frozen is None:
                st.error("No frozen baseline for this chart yet — switch to 'Phase I: establish & freeze' first.")
                st.stop()
        else:
            frozen = None

        if config["compute"] == "xbar_r":
            subgroups = subgroup_rows(stream_frame)
            if phase_mode == _PHASE_I_MODE:
                frozen = freeze_xbar_r(subgroups, excluded=excluded_points)
                st.session_state[frozen_key] = frozen
            result = compute_xbar_r(subgroups, frozen=frozen)
            points = result["subgroup_means"]
            sigma = result["sigma_hat"] / len(subgroups[0]) ** 0.5
            cl, ucl, lcl = result["xbarbar"], result["ucl_x"], result["lcl_x"]
            violations = detect_rule_violations(chart_key, points, cl, sigma, rule_set)
            chart_title, y_axis = "Xbar-R Chart", "Subgroup Mean"
        elif config["compute"] == "xbar_s":
            subgroups = subgroup_rows(stream_frame)
            if phase_mode == _PHASE_I_MODE:
                frozen = freeze_xbar_s(subgroups, excluded=excluded_points)
                st.session_state[frozen_key] = frozen
            result = compute_xbar_s(subgroups, frozen=frozen)
            points = result["subgroup_means"]
            sigma = result["sigma_hat"] / len(subgroups[0]) ** 0.5
            cl, ucl, lcl = result["xbarbar"], result["ucl_x"], result["lcl_x"]
            violations = detect_rule_violations(chart_key, points, cl, sigma, rule_set)
            chart_title, y_axis = "Xbar-S Chart", "Subgroup Mean"
        elif config["compute"] == "imr":
            values = stream_frame.sort_values("subgroup")["value"].tolist()
            if phase_mode == _PHASE_I_MODE:
                frozen = freeze_imr(values, excluded=excluded_points)
                st.session_state[frozen_key] = frozen
            result = compute_imr(values, frozen=frozen)
            points = result["values"]
            cl, ucl, lcl = result["xbar"], result["ucl_x"], result["lcl_x"]
            violations = detect_rule_violations(chart_key, points, cl, result["sigma_hat"], rule_set)
            chart_title, y_axis = "Individuals Chart", "Measurement"
        elif config["compute"] == "p":
            ordered = stream_frame.sort_values("subgroup")
            counts = ordered["value"].tolist()
            sample_sizes = ordered["sample_size"].tolist()
            result = compute_p(counts, sample_sizes)
            avg_n = sum(sample_sizes) / len(sample_sizes)
            sigma = (result["pbar"] * (1.0 - result["pbar"]) / avg_n) ** 0.5 if result["pbar"] < 1.0 else 0.0
            points = result["proportions"]
            cl, ucl, lcl = result["pbar"], result["ucl"], result["lcl"]
            violations = detect_rule_violations(chart_key, points, cl, sigma, rule_set)
            chart_title, y_axis = "p Chart", "Proportion Defective"
        elif config["compute"] == "c":
            ordered = stream_frame.sort_values("subgroup")
            counts = ordered["value"].tolist()
            result = compute_c(counts)
            cbar = result["cbar"]
            # Poisson count data: sigma = sqrt(c-bar), matching compute_c's limits.
            sigma = cbar ** 0.5 if cbar > 0 else 0.0
            points = result["counts"]
            cl, ucl, lcl = cbar, result["ucl"], result["lcl"]
            violations = detect_rule_violations(chart_key, points, cl, sigma, rule_set)
            chart_title, y_axis = "c Chart", "Nonconformity Count"
        elif config["compute"] == "u":
            ordered = stream_frame.sort_values("subgroup")
            counts = ordered["value"].tolist()
            sample_sizes = ordered["sample_size"].tolist()
            result = compute_u(counts, sample_sizes)
            avg_n = sum(sample_sizes) / len(sample_sizes)
            sigma = (result["ubar"] / avg_n) ** 0.5 if result["ubar"] > 0 else 0.0
            points = result["u_values"]
            cl, ucl, lcl = result["ubar"], result["ucl"], result["lcl"]
            violations = detect_rule_violations(chart_key, points, cl, sigma, rule_set)
            chart_title, y_axis = "u Chart", "Defects per Unit"
        elif config["compute"] == "ewma":
            values = stream_frame.sort_values("subgroup")["value"].tolist()
            # ponytail: mu0/sigma are an independent Phase I estimate from this
            # stream's own I-MR fit (RULE 12) — never derived from the z-series.
            baseline = compute_imr(values)
            mu0, sigma0 = baseline["xbar"], baseline["sigma_hat"]
            result = compute_ewma(values, mu0, sigma0, lam=lam, L=ewma_l)
            points, cl, ucl, lcl = result["z"], result["mu0"], result["ucl"], result["lcl"]
            # Gate proof: WE/Nelson never run on EWMA (always []); the chart's own
            # limit-crossing signals (result["signals"]) drive the actual overlay.
            _ = detect_rule_violations(chart_key, points, cl, sigma0, rule_set)
            violations = [{"index": i, "rule": "EWMA limit exceeded"} for i in result["signals"]]
            if not result["pairing_adequate"]:
                st.warning(result["pairing_note"])
            chart_title, y_axis = "EWMA Chart", "EWMA (z)"
        else:
            values = stream_frame.sort_values("subgroup")["value"].tolist()
            baseline = compute_imr(values)
            mu0, sigma0 = baseline["xbar"], baseline["sigma_hat"]
            result = compute_cusum(values, mu0, sigma0, k=cusum_k, h=cusum_h, fir=cusum_fir)
            points, cl, ucl, lcl = result["c_plus"], 0.0, result["h"], 0.0
            _ = detect_rule_violations(chart_key, points, cl, sigma0, rule_set)
            violations = [
                {"index": i, "rule": "CUSUM decision interval exceeded"} for i in result["signals"]
            ]
            # SME Q2 (W10-5, #145): the C- lower arm exports as its own per-point
            # column (positive-accumulator convention, matching the engine/RULE 13),
            # not just a metrics summary.
            secondary_points = ("C-", result["c_minus"])
            chart_title, y_axis = "CUSUM Chart", "Cumulative Sum"

        if config["compute"] == "ewma":
            figure = build_ewma_chart(cast(EWMAResult, result))
        elif config["compute"] == "cusum":
            figure = build_cusum_chart(cast(CUSUMResult, result))
        else:
            figure = build_control_chart(
                points=points, cl=cl, ucl=ucl, lcl=lcl,
                violations=violations, title=chart_title, y_axis_title=y_axis,
            )
    except (ValueError, KeyError) as exc:
        st.error(
            "Could not build this chart from the data. Check that the selected chart "
            "type has enough subgroups and the columns it needs "
            f"(p/u charts require a positive 'sample_size'). ({exc})"
        )
        st.stop()

    metrics = summarize_metrics(chart_key, result)
    metric_columns = st.columns(3)
    for column, (label, value) in zip(metric_columns, metrics):
        column.metric(label, value)

    st.plotly_chart(figure, use_container_width=True)

    if chart_key in PHASE_ELIGIBLE and phase_mode != _LIVE_MODE:
        frozen_shown: FrozenLimits | None = st.session_state.get(frozen_key)
        if frozen_shown is not None:
            st.caption(
                f"Frozen at {frozen_shown['frozen_at']}  |  baseline range: "
                f"{frozen_shown['phase_i_range']}  |  excluded: {frozen_shown['excluded']}  |  "
                f"sigma method: {frozen_shown['sigma_method']}  |  "
                f"{frozen_shown['baseline_note'] or 'baseline adequate'}"
            )

    # --- SPC -> FMEA candidate feedback (OQ2/OQ4/OQ5, W07-2 #89) --------------
    # Fires only for a real Control Plan characteristic (never "(manual)") with
    # >=1 rule violation; clears any stale feedback from a prior chart/selection
    # otherwise, so a resolved/changed chart doesn't leave a stale candidate.
    if selected != "(manual)" and violations:
        source_lookup = st.session_state.get(SOURCE_INDEX_STATE_KEY)
        source = source_lookup.get(selected) if source_lookup else None
        feedback = build_occurrence_feedback(
            characteristic=selected,
            stream=stream_key,
            rule_set=rule_set,
            violations=violations,
            total_points=len(points),
            source=source,
        )
        st.session_state[FEEDBACK_STATE_KEY] = feedback
        st.info(
            "**SPC → FMEA feedback:** out-of-control signal detected — a candidate "
            "occurrence-rating review is now available on the FMEA page (not applied "
            "automatically)."
        )
    else:
        st.session_state.pop(FEEDBACK_STATE_KEY, None)

    report = ControlChartReport(
        chart_label=chart_title,
        stream=stream_key,
        rule_set=rule_set,
        points=points,
        cl=cl,
        ucl=ucl,
        lcl=lcl,
        violations=violations,
        metrics=metrics,
        secondary_points=secondary_points,
    )
    # SPC reports are pure tables/text (no embedded chart images), so they build in
    # ~milliseconds; generating eagerly per rerun is fine here, unlike FMEA's
    # matplotlib-heavy PDF which is cached in session state.
    st.subheader("Download Report")
    excel_col, pdf_col = st.columns(2)
    excel_col.download_button(
        "Excel (.xlsx)",
        data=build_control_chart_report_excel(report),
        file_name=f"spc_control_chart_{config['compute']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    pdf_col.download_button(
        "PDF (.pdf)",
        data=build_control_chart_report_pdf(report),
        file_name=f"spc_control_chart_{config['compute']}.pdf",
        mime="application/pdf",
    )

    st.subheader("Rule Reference")
    st.dataframe(RULE_REFERENCE, use_container_width=True, hide_index=True)
