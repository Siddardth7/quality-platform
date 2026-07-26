import plotly.graph_objects as go
import pytest

from spc_app.spc_engine.control_charts import compute_cusum, compute_ewma
from spc_app.visualizer import (
    build_capability_histogram,
    build_control_chart,
    build_cpk_gauge,
    build_cusum_chart,
    build_ewma_chart,
)

POINTS = [10.0, 11.0, 9.0, 12.0, 10.5, 9.5]


def test_build_control_chart_scalar_limits_returns_four_traces():
    fig = build_control_chart(POINTS, cl=10.0, ucl=13.0, lcl=7.0)
    assert isinstance(fig, go.Figure)
    # process, UCL, LCL, CL
    assert len(fig.data) == 4


def test_build_control_chart_accepts_sequence_limits():
    ucl = [13.0] * len(POINTS)
    lcl = [7.0] * len(POINTS)
    fig = build_control_chart(POINTS, cl=10.0, ucl=ucl, lcl=lcl)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 4


def test_build_control_chart_with_violations_adds_a_trace():
    violations = [{"index": 3, "rule": "Western Electric Rule 1"}]
    fig = build_control_chart(POINTS, cl=10.0, ucl=13.0, lcl=7.0, violations=violations)
    # process, UCL, LCL, CL, violations
    assert len(fig.data) == 5


def test_build_capability_histogram_with_spec_limits_returns_figure():
    fig = build_capability_histogram(POINTS, lsl=8.0, usl=12.0, mean=10.0, sigma_overall=1.0)
    assert isinstance(fig, go.Figure)
    # histogram + normal-fit curve
    assert len(fig.data) == 2


def test_build_capability_histogram_without_spec_limits_returns_figure():
    fig = build_capability_histogram(POINTS, lsl=None, usl=None, mean=10.0, sigma_overall=1.0)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2


def test_build_cpk_gauge_valid_cpk_returns_figure():
    fig = build_cpk_gauge(1.45)
    assert isinstance(fig, go.Figure)


def test_build_cpk_gauge_none_does_not_raise():
    fig = build_cpk_gauge(None)
    assert isinstance(fig, go.Figure)


def test_build_cpk_gauge_none_has_one_indicator():
    fig = build_cpk_gauge(None)
    assert len(fig.data) == 1


def test_build_ewma_chart_signal_free_returns_four_traces():
    result = compute_ewma([10.0] * 10, mu0=10.0, sigma=1.0)
    fig = build_ewma_chart(result)
    assert isinstance(fig, go.Figure)
    # z, UCL, LCL, CL
    assert len(fig.data) == 4


def test_build_ewma_chart_with_signals_adds_a_trace():
    values = ([10.0] * 5) + ([13.0] * 10)
    result = compute_ewma(values, mu0=10.0, sigma=1.0, lam=0.2, L=3.0)
    assert result["signals"] != []
    fig = build_ewma_chart(result)
    # z, UCL, LCL, CL, violations
    assert len(fig.data) == 5


def test_build_ewma_chart_x_axis_title_is_observation():
    result = compute_ewma([10.0] * 5, mu0=10.0, sigma=1.0)
    fig = build_ewma_chart(result)
    assert fig.layout.xaxis.title.text == "Observation"


# ---------------------------------------------------------------------------
# 15-18: build_cusum_chart trace count / label contract
# ---------------------------------------------------------------------------


def test_build_cusum_chart_signal_free_returns_four_traces():
    result = compute_cusum([10.0] * 10, mu0=10.0, sigma=1.0)
    fig = build_cusum_chart(result)
    assert isinstance(fig, go.Figure)
    # C+, -C-, +h, -h
    assert len(fig.data) == 4


def test_build_cusum_chart_with_upper_arm_signal_adds_a_trace():
    values = ([10.0] * 5) + ([11.0] * 15)
    result = compute_cusum(values, mu0=10.0, sigma=1.0, k=0.5, h=5.0)
    assert result["signals"] != []
    fig = build_cusum_chart(result)
    # C+, -C-, +h, -h, violations
    assert len(fig.data) == 5


def test_build_cusum_chart_with_lower_arm_signal_adds_a_trace():
    values = ([10.0] * 5) + ([9.0] * 15)
    result = compute_cusum(values, mu0=10.0, sigma=1.0, k=0.5, h=5.0)
    assert result["signals"] != []
    fig = build_cusum_chart(result)
    # C+, -C-, +h, -h, violations
    assert len(fig.data) == 5


def test_build_cusum_chart_x_axis_title_is_observation():
    result = compute_cusum([10.0] * 5, mu0=10.0, sigma=1.0)
    fig = build_cusum_chart(result)
    assert fig.layout.xaxis.title.text == "Observation"
