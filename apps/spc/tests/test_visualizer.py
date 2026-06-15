import plotly.graph_objects as go
import pytest

from spc_app.visualizer import build_cpk_gauge


def test_build_cpk_gauge_valid_cpk_returns_figure():
    fig = build_cpk_gauge(1.45)
    assert isinstance(fig, go.Figure)


def test_build_cpk_gauge_none_does_not_raise():
    fig = build_cpk_gauge(None)
    assert isinstance(fig, go.Figure)


def test_build_cpk_gauge_none_has_one_indicator():
    fig = build_cpk_gauge(None)
    assert len(fig.data) == 1
