from __future__ import annotations

import time

import streamlit as st

from spc_app.simulation.engine import PROCESS_CONFIGS, SimulationEngine
from spc_app.spc_engine.control_charts import compute_imr, compute_xbar_r
from spc_app.spc_engine.rule_detection import detect_nelson_violations, detect_we_violations
from spc_app.visualizer import build_control_chart



def get_engine(process_stream: str, subgroup_size: int) -> SimulationEngine:
    engine = st.session_state.get("simulation_engine")
    if (
        engine is None
        or engine.process_stream != process_stream
        or engine.subgroup_size != subgroup_size
    ):
        engine = SimulationEngine(process_stream=process_stream, subgroup_size=subgroup_size, rng_seed=42)
        st.session_state["simulation_engine"] = engine
    return engine


def detect_rule_violations(points, cl, sigma, rule_set):
    if sigma <= 0:
        return []
    if rule_set == "Nelson":
        return detect_nelson_violations(points, cl=cl, sigma=sigma)
    return detect_we_violations(points, cl=cl, sigma=sigma)


def current_chart(engine: SimulationEngine, rule_set: str):
    if not engine.history:
        return None, [], 0.0, 0.0

    if engine.subgroup_size == 1:
        points = [group[0] for group in engine.history][-50:]
        if len(points) < 2:
            return None, [], 0.0, 0.0
        result = compute_imr(points)
        violations = detect_rule_violations(points, result["xbar"], result["sigma_hat"], rule_set)
        figure = build_control_chart(
            points=points,
            cl=result["xbar"],
            ucl=result["ucl_x"],
            lcl=result["lcl_x"],
            violations=violations,
            title="Live Individuals Chart",
            y_axis_title="Measurement",
        )
        return figure, violations, result["xbar"], result["sigma_hat"]

    subgroup_means = [sum(group) / len(group) for group in engine.history][-50:]
    result = compute_xbar_r(engine.history[-50:])
    sigma = result["sigma_hat"] / (engine.subgroup_size ** 0.5)
    violations = detect_rule_violations(subgroup_means, result["xbarbar"], sigma, rule_set)
    figure = build_control_chart(
        points=subgroup_means,
        cl=result["xbarbar"],
        ucl=result["ucl_x"],
        lcl=result["lcl_x"],
        violations=violations,
        title="Live Xbar-R Chart",
        y_axis_title="Subgroup Mean",
    )
    return figure, violations, result["xbarbar"], result["sigma_hat"]


def render_simulation() -> None:
    st.title("Live Simulation")
    st.caption("Real-time SPC simulation with mean shift, spike, and drift injection.")

    with st.sidebar:
        st.header("Simulation Controls")
        process_stream = st.selectbox("Process Stream", options=list(PROCESS_CONFIGS.keys()))
        subgroup_size = st.slider("Subgroup Size", min_value=1, max_value=10, value=5)
        update_interval = st.slider("Update Interval (seconds)", min_value=0.5, max_value=3.0, value=1.0, step=0.5)
        rule_set = st.radio("Rule Set", options=["Western Electric", "Nelson"], horizontal=True)
        run_simulation = st.toggle("Run Simulation", value=False)
        reset_button = st.button("Reset Process", use_container_width=True)

    engine = get_engine(process_stream, subgroup_size)

    if reset_button:
        engine.reset()

    button_cols = st.columns(4)
    if button_cols[0].button("Mean Shift (+1.5 sigma)", use_container_width=True):
        engine.inject_mean_shift(magnitude_sigma=1.5, duration=10)
    if button_cols[1].button("Spike (+4 sigma)", use_container_width=True):
        engine.inject_spike(magnitude_sigma=4.0)
    if button_cols[2].button("Drift (+2 sigma / 15)", use_container_width=True):
        engine.inject_drift(max_sigma=2.0, duration=15)
    if button_cols[3].button("Clear Disturbance", use_container_width=True):
        engine.reset_disturbance()

    if run_simulation:
        engine.step()

    if engine.active_disturbance is None:
        st.info("Active disturbance: none")
    else:
        st.warning(
            f"Active disturbance: {engine.active_disturbance.kind} "
            f"({engine.active_disturbance.steps_remaining} steps remaining)"
        )

    figure, violations, centerline, sigma_hat = current_chart(engine, rule_set)

    metric_cols = st.columns(3)
    metric_cols[0].metric("Subgroups Generated", str(engine.steps_generated))
    metric_cols[1].metric("Centerline", f"{centerline:.4f}" if engine.history else "N/A")
    metric_cols[2].metric("Sigma Hat", f"{sigma_hat:.4f}" if engine.history else "N/A")

    if engine.history:
        st.metric("Violation Count (Window)", len(violations))
        st.plotly_chart(figure, use_container_width=True)
    else:
        st.info("Start the simulation to generate the first subgroup window.")

    if run_simulation:
        time.sleep(update_interval)
        st.rerun()
