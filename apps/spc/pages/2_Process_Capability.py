from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from spc_app.spc_engine.capability import compute_capability, normality_test
from spc_app.spc_engine.control_charts import compute_imr, compute_xbar_r, compute_xbar_s
from spc_app.spc_engine.utils import subgroup_rows
from spc_app.ui.theme import apply_theme
from spc_app.visualizer import build_capability_histogram, build_cpk_gauge

st.set_page_config(page_title="Process Capability", layout="wide")
apply_theme()

DEMO_PATH = Path(__file__).resolve().parents[1] / "data" / "demo_composites_aerospace.csv"
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


@st.cache_data
def load_demo_data() -> pd.DataFrame:
    if not DEMO_PATH.exists():
        from spc_app.spc_engine.data_generator import generate_demo_dataset
        DEMO_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate_demo_dataset().to_csv(DEMO_PATH, index=False)
    return pd.read_csv(DEMO_PATH)



def compute_sigma_hat(stream_name: str, frame: pd.DataFrame) -> float:
    if stream_name == "ply_thickness":
        return compute_xbar_r(subgroup_rows(frame))["sigma_hat"]
    if stream_name == "hole_diameter":
        return compute_xbar_s(subgroup_rows(frame))["sigma_hat"]
    return compute_imr(frame.sort_values("subgroup")["value"].tolist())["sigma_hat"]


def default_limit(series: pd.Series):
    cleaned = series.dropna()
    if cleaned.empty:
        return None
    return float(cleaned.iloc[0])


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
    frame = pd.read_csv(upload)
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

values = stream_frame["value"].to_numpy()
sigma_hat = compute_sigma_hat(stream_name, stream_frame)
capability = compute_capability(
    values,
    lsl=lsl if lsl_enabled else None,
    usl=usl if usl_enabled else None,
    sigma_hat=sigma_hat,
)
normality = normality_test(values)

left, right = st.columns([1, 2])
with left:
    st.plotly_chart(build_cpk_gauge(capability["cpk"]), use_container_width=True)

with right:
    metric_grid = st.columns(4)
    metric_grid[0].metric("Cp", "N/A" if capability["cp"] is None else f"{capability['cp']:.3f}")
    metric_grid[1].metric("Cpk", "N/A" if capability["cpk"] is None else f"{capability['cpk']:.3f}")
    metric_grid[2].metric("Pp", "N/A" if capability["pp"] is None else f"{capability['pp']:.3f}")
    metric_grid[3].metric("Ppk", "N/A" if capability["ppk"] is None else f"{capability['ppk']:.3f}")

    summary_grid = st.columns(3)
    summary_grid[0].metric("Mean", f"{capability['mean']:.4f}")
    summary_grid[1].metric("Sigma Hat", f"{capability['sigma_hat']:.4f}")
    summary_grid[2].metric("Sigma Overall", f"{capability['sigma_overall']:.4f}")

st.plotly_chart(
    build_capability_histogram(
        data=values,
        lsl=lsl if lsl_enabled else None,
        usl=usl if usl_enabled else None,
        mean=capability["mean"],
        sigma_overall=capability["sigma_overall"],
        title=f"{stream_label} Distribution",
    ),
    use_container_width=True,
)

if normality["is_normal"]:
    st.success(f"Shapiro-Wilk p-value = {normality['p_value']:.4f}. Distribution appears approximately normal.")
else:
    st.warning(f"Shapiro-Wilk p-value = {normality['p_value']:.4f}. Capability results may need non-normal review.")

st.subheader("Capability Interpretation")
st.dataframe(CAPABILITY_REFERENCE, use_container_width=True, hide_index=True)
