from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd
import streamlit as st

from spc_app.exporter import (
    CapabilityReport,
    build_capability_report_excel,
    build_capability_report_pdf,
)
from spc_app.schema import IngestError, load_spc_csv
from spc_app.spc_engine.capability import compute_capability_study, normality_test
from spc_app.spc_engine.control_charts import compute_imr, compute_xbar_r, compute_xbar_s
from spc_app.spc_engine.rule_detection import detect_violations
from spc_app.spc_engine.utils import subgroup_rows
from spc_app.visualizer import build_capability_histogram, build_cpk_gauge

DEMO_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_composites_aerospace.csv"
STREAM_OPTIONS = {
    "Ply Thickness": "ply_thickness",
    "Autoclave Cure Temperature": "autoclave_temp",
    "Hole Diameter": "hole_diameter",
}
CAPABILITY_REFERENCE = pd.DataFrame(
    [
        ("< 1.00", "Not capable", "Process spread or centering is outside common aerospace expectations."),
        ("1.00 - 1.32", "Marginal", "Monitor closely and reduce variation before release-critical use."),
        (">= 1.33", "Capable", "Common minimum target for stable manufacturing capability."),
    ],
    columns=["Cpk", "Interpretation", "Meaning"],
)
FORCE_METHOD_OPTIONS: dict[str, Literal["auto", "normal", "boxcox", "percentile"]] = {
    "Auto (Shapiro-Wilk driven)": "auto",
    "Force normal-theory": "normal",
    "Force Box-Cox / Yeo-Johnson": "boxcox",
    "Force fitted-distribution percentile": "percentile",
}


@st.cache_data
def load_demo_data() -> pd.DataFrame:
    if not DEMO_PATH.exists():
        from spc_app.spc_engine.data_generator import generate_demo_dataset
        DEMO_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate_demo_dataset().to_csv(DEMO_PATH, index=False)
    return pd.read_csv(DEMO_PATH)


def assess_control_chart(
    stream_name: str,
    frame: pd.DataFrame,
) -> tuple[float, list[dict[str, int | str]]]:
    """Compute within-subgroup sigma_hat and detect Western Electric
    out-of-control signals on the stream's control chart.

    Capability indices are only meaningful on a stable process, so the
    Capability page uses the signal list to gate (warn on) Cpk reporting.
    Returns (sigma_hat, signals); an empty list means in statistical control.
    """
    if stream_name == "ply_thickness":
        chart_type = "Xbar-R"
        subgroups = subgroup_rows(frame)
        xr = compute_xbar_r(subgroups)
        points: list[float] = xr["subgroup_means"]
        cl: float = xr["xbarbar"]
        sigma_hat: float = xr["sigma_hat"]
        # The plotted points are subgroup means, so their spread is sigma/sqrt(n).
        sigma_points: float = sigma_hat / (len(subgroups[0]) ** 0.5)
    elif stream_name == "hole_diameter":
        chart_type = "Xbar-S"
        subgroups = subgroup_rows(frame)
        xs = compute_xbar_s(subgroups)
        points = xs["subgroup_means"]
        cl = xs["xbarbar"]
        sigma_hat = xs["sigma_hat"]
        sigma_points = sigma_hat / (len(subgroups[0]) ** 0.5)
    else:
        chart_type = "I-MR"
        im = compute_imr(frame.sort_values("subgroup")["value"].tolist())
        points = im["values"]
        cl = im["xbar"]
        sigma_hat = im["sigma_hat"]
        sigma_points = sigma_hat

    # Routed through the gated chokepoint (rule_detection.detect_violations) rather
    # than calling detect_we_violations directly — same behaviour for a Shewhart
    # chart_type (WE runs, sigma<=0 -> []), but every caller now shares one gate.
    signals = detect_violations(chart_type, points, cl=cl, sigma=sigma_points, rule_set="Western Electric")
    return sigma_hat, signals


def default_limit(series: pd.Series):
    cleaned = series.dropna()
    if cleaned.empty:
        return None
    return float(cleaned.iloc[0])


def render_capability() -> None:
    st.title("Process Capability")
    st.caption("Capability indices, distribution fit, and normality feedback for variable-data demo streams.")

    with st.sidebar:
        st.header("Controls")
        source_mode = st.radio("Data Source", options=["Demo", "Upload CSV"], horizontal=True)
        upload = None
        if source_mode == "Upload CSV":
            upload = st.file_uploader("Upload CSV", type=["csv"])

    if source_mode == "Demo" or upload is None:
        frame = load_demo_data()
        stream_options = STREAM_OPTIONS
    else:
        # Uploads run through the shared validated-ingest boundary; a malformed
        # CSV surfaces a friendly message instead of a downstream crash.
        try:
            frame = load_spc_csv(upload)
        except IngestError as exc:
            st.error(str(exc))
            st.stop()
        stream_options = {s: s for s in sorted(frame["stream"].unique().tolist())}

    with st.sidebar:
        stream_label = st.selectbox("Process Stream", options=list(stream_options.keys()))
        stream_name = stream_options[stream_label]
        stream_frame = frame[frame["stream"] == stream_name].copy().sort_values("subgroup")

        if stream_frame.empty:
            st.error("No rows found for the selected stream.")
            st.stop()
        if "value" not in stream_frame.columns:
            st.error("Uploaded CSV must contain a 'value' column.")
            st.stop()

        default_lsl = default_limit(stream_frame["lsl"]) if "lsl" in stream_frame.columns else None
        default_usl = default_limit(stream_frame["usl"]) if "usl" in stream_frame.columns else None
        lsl_enabled = default_lsl is not None
        usl_enabled = default_usl is not None
        lsl = st.number_input("LSL", value=default_lsl if lsl_enabled else 0.0, disabled=not lsl_enabled)
        usl = st.number_input("USL", value=default_usl if usl_enabled else 0.0, disabled=not usl_enabled)

        force_method_label = st.radio("Capability Method", options=list(FORCE_METHOD_OPTIONS.keys()))
        force_method = FORCE_METHOD_OPTIONS[force_method_label]

    values = stream_frame["value"].to_numpy()
    # Capability/normality need a minimum number of points and a positive spread; a
    # thin or degenerate stream raises ValueError. Surface it as a friendly message
    # rather than a Streamlit stack trace.
    try:
        _, oos_signals = assess_control_chart(stream_name, stream_frame)
        study = compute_capability_study(
            values,
            lsl=lsl if lsl_enabled else None,
            usl=usl if usl_enabled else None,
            force_method=force_method,
        )
        normality = normality_test(values)
    except (ValueError, KeyError) as exc:
        st.error(
            "Could not compute capability from this data. The selected stream needs "
            f"enough in-control measurements to estimate spread. ({exc})"
        )
        st.stop()

    # Stability gate: capability indices are only meaningful on a process in
    # statistical control. Warn prominently before reporting Cp/Cpk on a process
    # that shows Western Electric out-of-control signals.
    if oos_signals:
        st.error(
            f"⚠️ Process is **not in statistical control** — "
            f"{len(oos_signals)} Western Electric signal(s) detected on the control chart. "
            "Capability indices (Cp / Cpk / Pp / Ppk) are **not valid** until the process is "
            "stabilized. Treat the values below as indicative only, not a capability claim."
        )

    left, right = st.columns([1, 2])
    with left:
        st.plotly_chart(build_cpk_gauge(study["cpk"]), use_container_width=True)

    with right:
        st.caption(f"Method: **{study['method']}**" + (
            f"  |  λ = {study['lambda_used']:.4g}"
            if study["method"] in ("boxcox", "yeojohnson") and study["lambda_used"] is not None
            else f"  |  fitted distribution: {study['fitted_dist']}"
            if study["method"] == "percentile"
            else ""
        ))
        metric_grid = st.columns(2)
        metric_grid[0].metric(
            "Cp", "N/A" if study["cp"] is None else f"{study['cp']:.3f}",
            help=f"95% CI: {study['cp_ci']}" if study["cp_ci"] else None,
        )
        metric_grid[1].metric(
            "Cpk", "N/A" if study["cpk"] is None else f"{study['cpk']:.3f}",
            help=f"95% CI: {study['cpk_ci']}" if study["cpk_ci"] else None,
        )

        summary_grid = st.columns(4)
        summary_grid[0].metric("Pp", "N/A" if study["pp"] is None else f"{study['pp']:.3f}")
        summary_grid[1].metric("Ppk", "N/A" if study["ppk"] is None else f"{study['ppk']:.3f}")
        summary_grid[2].metric("Mean", f"{study['mean']:.4f}")
        summary_grid[3].metric("Sigma Overall", f"{study['sigma_overall']:.4f}")

        st.caption(study["note"])

    st.plotly_chart(
        build_capability_histogram(
            data=values,
            lsl=lsl if lsl_enabled else None,
            usl=usl if usl_enabled else None,
            mean=study["mean"],
            sigma_overall=study["sigma_overall"],
            title=f"{stream_label} Distribution",
            method=study["method"],
            fitted_dist=study["fitted_dist"],
            lambda_used=study["lambda_used"],
            shift=study["shift"],
        ),
        use_container_width=True,
    )

    if normality["is_normal"]:
        st.success(f"Shapiro-Wilk p-value = {normality['p_value']:.4f}. Distribution appears approximately normal.")
    else:
        st.warning(f"Shapiro-Wilk p-value = {normality['p_value']:.4f}. Capability results may need non-normal review.")

    report = CapabilityReport(
        stream_label=stream_label,
        values=values.tolist(),
        capability=study,
        lsl=lsl if lsl_enabled else None,
        usl=usl if usl_enabled else None,
        normality=normality,
        oos_signal_count=len(oos_signals),
    )
    # Pure table/text reports (no chart images) build in ~milliseconds, so eager
    # per-rerun generation is fine here (cf. FMEA's cached matplotlib PDF path).
    st.subheader("Download Report")
    excel_col, pdf_col = st.columns(2)
    excel_col.download_button(
        "Excel (.xlsx)",
        data=build_capability_report_excel(report),
        file_name=f"spc_capability_{stream_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    pdf_col.download_button(
        "PDF (.pdf)",
        data=build_capability_report_pdf(report),
        file_name=f"spc_capability_{stream_name}.pdf",
        mime="application/pdf",
    )

    st.subheader("Capability Interpretation")
    st.dataframe(CAPABILITY_REFERENCE, use_container_width=True, hide_index=True)
