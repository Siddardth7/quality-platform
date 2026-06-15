from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from spc_app.spc_engine.control_charts import compute_imr, compute_p, compute_u, compute_xbar_r, compute_xbar_s
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
    return pd.read_csv(uploaded_file)



def detect_rule_violations(points: list[float], cl: float, sigma: float, rule_set: str):
    if sigma <= 0:
        return []
    if rule_set == "Nelson":
        return detect_nelson_violations(points, cl=cl, sigma=sigma)
    return detect_we_violations(points, cl=cl, sigma=sigma)


def summarize_metrics(chart_key: str, result: dict) -> list[tuple[str, str]]:
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

    frame = load_source_data(upload if source_mode == "Upload CSV" else None)
    config = CHART_OPTIONS[chart_key]
    stream_frame = frame[frame["stream"] == config["stream"]].copy()

    if stream_frame.empty:
        st.error("No rows available for the selected chart type.")
        st.stop()

    if config["compute"] == "xbar_r":
        subgroups = subgroup_rows(stream_frame)
        result = compute_xbar_r(subgroups)
        points = result["subgroup_means"]
        sigma = result["sigma_hat"] / len(subgroups[0]) ** 0.5
        figure = build_control_chart(
            points=points,
            cl=result["xbarbar"],
            ucl=result["ucl_x"],
            lcl=result["lcl_x"],
            violations=detect_rule_violations(points, result["xbarbar"], sigma, rule_set),
            title="Xbar-R Chart",
            y_axis_title="Subgroup Mean",
        )
    elif config["compute"] == "xbar_s":
        subgroups = subgroup_rows(stream_frame)
        result = compute_xbar_s(subgroups)
        points = result["subgroup_means"]
        sigma = result["sigma_hat"] / len(subgroups[0]) ** 0.5
        figure = build_control_chart(
            points=points,
            cl=result["xbarbar"],
            ucl=result["ucl_x"],
            lcl=result["lcl_x"],
            violations=detect_rule_violations(points, result["xbarbar"], sigma, rule_set),
            title="Xbar-S Chart",
            y_axis_title="Subgroup Mean",
        )
    elif config["compute"] == "imr":
        values = stream_frame.sort_values("subgroup")["value"].tolist()
        result = compute_imr(values)
        points = result["values"]
        figure = build_control_chart(
            points=points,
            cl=result["xbar"],
            ucl=result["ucl_x"],
            lcl=result["lcl_x"],
            violations=detect_rule_violations(points, result["xbar"], result["sigma_hat"], rule_set),
            title="Individuals Chart",
            y_axis_title="Measurement",
        )
    elif config["compute"] == "p":
        ordered = stream_frame.sort_values("subgroup")
        counts = ordered["value"].tolist()
        sample_sizes = ordered["sample_size"].tolist()
        result = compute_p(counts, sample_sizes)
        avg_n = sum(sample_sizes) / len(sample_sizes)
        sigma = (result["pbar"] * (1.0 - result["pbar"]) / avg_n) ** 0.5 if result["pbar"] < 1.0 else 0.0
        points = result["proportions"]
        figure = build_control_chart(
            points=points,
            cl=result["pbar"],
            ucl=result["ucl"],
            lcl=result["lcl"],
            violations=detect_rule_violations(points, result["pbar"], sigma, rule_set),
            title="p Chart",
            y_axis_title="Proportion Defective",
        )
    else:
        ordered = stream_frame.sort_values("subgroup")
        counts = ordered["value"].tolist()
        sample_sizes = ordered["sample_size"].tolist()
        result = compute_u(counts, sample_sizes)
        avg_n = sum(sample_sizes) / len(sample_sizes)
        sigma = (result["ubar"] / avg_n) ** 0.5 if result["ubar"] > 0 else 0.0
        points = result["u_values"]
        figure = build_control_chart(
            points=points,
            cl=result["ubar"],
            ucl=result["ucl"],
            lcl=result["lcl"],
            violations=detect_rule_violations(points, result["ubar"], sigma, rule_set),
            title="u Chart",
            y_axis_title="Defects per Unit",
        )

    metric_columns = st.columns(3)
    for column, (label, value) in zip(metric_columns, summarize_metrics(chart_key, result)):
        column.metric(label, value)

    st.plotly_chart(figure, use_container_width=True)
    st.subheader("Rule Reference")
    st.dataframe(RULE_REFERENCE, use_container_width=True, hide_index=True)
