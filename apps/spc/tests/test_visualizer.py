import plotly.graph_objects as go
import pytest

from spc_app.visualizer import (
    build_capability_histogram,
    build_control_chart,
    build_cpk_gauge,
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
