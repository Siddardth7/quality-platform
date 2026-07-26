import numpy as np
import plotly.graph_objects as go
import pytest

from spc_app.spc_engine.capability import compute_capability_study
from spc_app.spc_engine.control_charts import compute_cusum, compute_ewma
from spc_app.visualizer import (
    _backtransformed_pdf,
    _transform_and_derivative,
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


# ---------------------------------------------------------------------------
# W10-5 (#145): build_capability_histogram fitted-distribution overlay branches.
# ---------------------------------------------------------------------------


def _overlay_curve(fig: go.Figure) -> tuple[np.ndarray, np.ndarray]:
    curve = fig.data[1]  # trace 0 is the histogram, trace 1 is the overlay curve
    return np.asarray(curve.x, dtype=float), np.asarray(curve.y, dtype=float)


def _count_local_maxima(y: np.ndarray) -> int:
    d = np.diff(y)
    signs = np.sign(d)
    signs = signs[signs != 0]
    return int(np.sum((signs[:-1] > 0) & (signs[1:] < 0)))


def test_build_capability_histogram_normal_method_overlay_unchanged():
    fig = build_capability_histogram(
        POINTS, lsl=8.0, usl=12.0, mean=10.0, sigma_overall=1.0, method="normal"
    )
    assert len(fig.data) == 2
    x, pdf = _overlay_curve(fig)
    area = np.trapezoid(pdf, x)
    assert area == pytest.approx(1.0, abs=0.02)
    assert _count_local_maxima(pdf) == 1


def test_build_capability_histogram_percentile_overlay_uses_fitted_dist_pdf():
    data = np.random.default_rng(5).gamma(shape=3.0, scale=1.0, size=200)
    fig = build_capability_histogram(
        data,
        lsl=None,
        usl=None,
        mean=float(data.mean()),
        sigma_overall=float(data.std(ddof=1)),
        method="percentile",
        fitted_dist="gamma",
    )
    assert len(fig.data) == 2
    x, pdf = _overlay_curve(fig)
    assert np.all(pdf >= 0)
    area = np.trapezoid(pdf, x)
    assert area == pytest.approx(1.0, abs=0.02)
    assert _count_local_maxima(pdf) == 1
    assert "Fitted gamma" in fig.data[1].name


def test_build_capability_histogram_boxcox_overlay_backtransforms_correctly():
    data = np.random.default_rng(1).lognormal(mean=0.0, sigma=0.6, size=200)
    study = compute_capability_study(data, lsl=0.1, usl=None, alpha=0.05)
    assert study["method"] == "boxcox"

    fig = build_capability_histogram(
        data,
        lsl=0.1,
        usl=None,
        mean=study["mean"],
        sigma_overall=study["sigma_overall"],
        method=study["method"],
        lambda_used=study["lambda_used"],
        shift=study["shift"],
    )
    assert len(fig.data) == 2
    x, pdf = _overlay_curve(fig)
    assert np.all(pdf >= -1e-12)
    area = np.trapezoid(pdf, x)
    assert area == pytest.approx(1.0, abs=0.05)
    assert _count_local_maxima(pdf) == 1
    assert "boxcox" in fig.data[1].name


def test_build_capability_histogram_yeojohnson_overlay_backtransforms_correctly():
    data = np.random.default_rng(109).gamma(shape=3.0, scale=1.0, size=60) - 5.0
    study = compute_capability_study(data, lsl=-8.0, usl=0.0, alpha=0.05)
    assert study["method"] == "yeojohnson"

    fig = build_capability_histogram(
        data,
        lsl=-8.0,
        usl=0.0,
        mean=study["mean"],
        sigma_overall=study["sigma_overall"],
        method=study["method"],
        lambda_used=study["lambda_used"],
        shift=study["shift"],
    )
    assert len(fig.data) == 2
    x, pdf = _overlay_curve(fig)
    assert np.all(pdf >= -1e-12)
    area = np.trapezoid(pdf, x)
    assert area == pytest.approx(1.0, abs=0.05)
    assert _count_local_maxima(pdf) == 1
    assert "yeojohnson" in fig.data[1].name


def test_backtransformed_pdf_and_transform_helpers_agree_on_boxcox():
    x = np.linspace(0.5, 5.0, 50)
    t, t_prime = _transform_and_derivative(x, "boxcox", lam=0.5, shift=0.0)
    pdf = _backtransformed_pdf(x, "boxcox", lam=0.5, shift=0.0, mu_t=1.0, sigma_t=0.5)
    assert t.shape == x.shape
    assert t_prime.shape == x.shape
    assert np.all(pdf >= 0)


def test_transform_and_derivative_yeojohnson_piecewise_on_sign():
    x = np.array([-2.0, -0.5, 0.0, 0.5, 2.0])
    t, t_prime = _transform_and_derivative(x, "yeojohnson", lam=0.5, shift=0.0)
    assert t.shape == x.shape
    # Monotonic increasing transform (t' > 0 everywhere).
    assert np.all(t_prime > 0)


def test_transform_and_derivative_yeojohnson_lambda_zero_uses_log_branch_for_positive_side():
    x = np.array([-1.0, 0.5, 2.0])
    t, t_prime = _transform_and_derivative(x, "yeojohnson", lam=0.0, shift=0.0)
    np.testing.assert_allclose(t[1:], np.log(x[1:] + 1.0))


def test_transform_and_derivative_yeojohnson_lambda_two_uses_log_branch_for_negative_side():
    x = np.array([-2.0, -0.5, 1.0])
    t, t_prime = _transform_and_derivative(x, "yeojohnson", lam=2.0, shift=0.0)
    np.testing.assert_allclose(t[:2], -np.log(-x[:2] + 1.0))
