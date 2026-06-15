from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from spc_app.spc_engine.capability import compute_capability, normality_test
from spc_app.spc_engine.control_charts import compute_imr, compute_xbar_r, compute_xbar_s
from spc_app.spc_engine.rule_detection import detect_we_violations
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
        subgroups = subgroup_rows(frame)
        xr = compute_xbar_r(subgroups)
        points: list[float] = xr["subgroup_means"]
        cl: float = xr["xbarbar"]
        sigma_hat: float = xr["sigma_hat"]
        # The plotted points are subgroup means, so their spread is sigma/sqrt(n).
        sigma_points: float = sigma_hat / (len(subgroups[0]) ** 0.5)
    elif stream_name == "hole_diameter":
        subgroups = subgroup_rows(frame)
        xs = compute_xbar_s(subgroups)
        points = xs["subgroup_means"]
        cl = xs["xbarbar"]
        sigma_hat = xs["sigma_hat"]
        sigma_points = sigma_hat / (len(subgroups[0]) ** 0.5)
    else:
        im = compute_imr(frame.sort_values("subgroup")["value"].tolist())
        points = im["values"]
        cl = im["xbar"]
        sigma_hat = im["sigma_hat"]
        sigma_points = sigma_hat

    signals = detect_we_violations(points, cl=cl, sigma=sigma_points) if sigma_points > 0 else []
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
    sigma_hat, oos_signals = assess_control_chart(stream_name, stream_frame)
    capability = compute_capability(
        values,
        lsl=lsl if lsl_enabled else None,
        usl=usl if usl_enabled else None,
        sigma_hat=sigma_hat,
    )
    normality = normality_test(values)

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
