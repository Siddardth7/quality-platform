from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import streamlit as st

from spc_app.exporter import (
    ControlChartReport,
    build_control_chart_report_excel,
    build_control_chart_report_pdf,
)
from spc_app.schema import IngestError, load_spc_csv
from spc_app.spc_engine.control_charts import (
    compute_c,
    compute_imr,
    compute_p,
    compute_u,
    compute_xbar_r,
    compute_xbar_s,
)
from spc_app.spc_engine.rule_detection import detect_nelson_violations, detect_we_violations
from spc_app.spc_engine.utils import subgroup_rows
from spc_app.visualizer import build_control_chart

DEMO_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_composites_aerospace.csv"
RULE_REFERENCE = pd.DataFrame(
    [
        ("Western Electric", "Rule 1", "1 point beyond +/-3 sigma"),
        ("Western Electric", "Rule 2", "2 of 3 consecutive beyond +/-2 sigma on the same side"),
        ("Western Electric", "Rule 3", "4 of 5 consecutive beyond +/-1 sigma on the same side"),
        ("Western Electric", "Rule 4", "8 consecutive points on the same side of the centerline"),
        ("Nelson", "Rule 5", "6 consecutive points trending up or down"),
        ("Nelson", "Rule 6", "14 consecutive points alternating up and down"),
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
}


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



def detect_rule_violations(points: list[float], cl: float, sigma: float, rule_set: str):
    if sigma <= 0:
        return []
    if rule_set == "Nelson":
        return detect_nelson_violations(points, cl=cl, sigma=sigma)
    return detect_we_violations(points, cl=cl, sigma=sigma)


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
    return [
        ("ubar", f"{result['ubar']:.4f}"),
        ("Avg N", f"{sum(result['sample_sizes']) / len(result['sample_sizes']):.2f}"),
        ("Points", str(len(result['u_values']))),
    ]


def render_control_charts() -> None:
    st.title("Control Charts")
    st.caption("Variables and attributes control charts with Western Electric and Nelson rule overlays.")

    with st.sidebar:
        st.header("Controls")
        chart_key = st.selectbox("Chart Type", options=list(CHART_OPTIONS.keys()))
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
    stream_frame = frame[frame["stream"] == config["stream"]].copy()

    if stream_frame.empty:
        st.error("No rows available for the selected chart type.")
        st.stop()

    # `result` is a runtime dispatch over chart type; each branch assigns a
    # different precisely-typed compute result, so the shared variable is the
    # honest read-only union surface. Engine functions keep their exact TypedDicts.
    # Each branch also lifts the plotted points + limits + violations into shared
    # locals so the figure is built once and the same values flow into the report.
    result: Mapping[str, Any]
    points: list[float]
    cl: float
    ucl: float | list[float]  # p/u charts have per-point (vector) limits
    lcl: float | list[float]
    violations: list[dict[str, int | str]]
    chart_title: str
    y_axis: str
    # The schema validates column/type shape; it can't guarantee a stream has enough
    # subgroups, or the sample_size column a p/u chart needs. Guard the compute so
    # those surface as a friendly message rather than a Streamlit stack trace.
    try:
        if config["compute"] == "xbar_r":
            subgroups = subgroup_rows(stream_frame)
            result = compute_xbar_r(subgroups)
            points = result["subgroup_means"]
            sigma = result["sigma_hat"] / len(subgroups[0]) ** 0.5
            cl, ucl, lcl = result["xbarbar"], result["ucl_x"], result["lcl_x"]
            violations = detect_rule_violations(points, cl, sigma, rule_set)
            chart_title, y_axis = "Xbar-R Chart", "Subgroup Mean"
        elif config["compute"] == "xbar_s":
            subgroups = subgroup_rows(stream_frame)
            result = compute_xbar_s(subgroups)
            points = result["subgroup_means"]
            sigma = result["sigma_hat"] / len(subgroups[0]) ** 0.5
            cl, ucl, lcl = result["xbarbar"], result["ucl_x"], result["lcl_x"]
            violations = detect_rule_violations(points, cl, sigma, rule_set)
            chart_title, y_axis = "Xbar-S Chart", "Subgroup Mean"
        elif config["compute"] == "imr":
            values = stream_frame.sort_values("subgroup")["value"].tolist()
            result = compute_imr(values)
            points = result["values"]
            cl, ucl, lcl = result["xbar"], result["ucl_x"], result["lcl_x"]
            violations = detect_rule_violations(points, cl, result["sigma_hat"], rule_set)
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
            violations = detect_rule_violations(points, cl, sigma, rule_set)
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
            violations = detect_rule_violations(points, cl, sigma, rule_set)
            chart_title, y_axis = "c Chart", "Nonconformity Count"
        else:
            ordered = stream_frame.sort_values("subgroup")
            counts = ordered["value"].tolist()
            sample_sizes = ordered["sample_size"].tolist()
            result = compute_u(counts, sample_sizes)
            avg_n = sum(sample_sizes) / len(sample_sizes)
            sigma = (result["ubar"] / avg_n) ** 0.5 if result["ubar"] > 0 else 0.0
            points = result["u_values"]
            cl, ucl, lcl = result["ubar"], result["ucl"], result["lcl"]
            violations = detect_rule_violations(points, cl, sigma, rule_set)
            chart_title, y_axis = "u Chart", "Defects per Unit"

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

    report = ControlChartReport(
        chart_label=chart_title,
        stream=config["stream"],
        rule_set=rule_set,
        points=points,
        cl=cl,
        ucl=ucl,
        lcl=lcl,
        violations=violations,
        metrics=metrics,
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
