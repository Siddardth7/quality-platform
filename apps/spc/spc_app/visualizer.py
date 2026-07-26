"""Pure Plotly figure builders for the SPC dashboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, Sequence

import numpy as np
import plotly.graph_objects as go
from quality_core.theme import AMBER, DANGER, PLOTLY_LAYOUT, TEXT_SECONDARY, VIOLET
from scipy import stats

if TYPE_CHECKING:
    from spc_app.spc_engine.control_charts import CUSUMResult, EWMAResult


def build_control_chart(
    points: Sequence[float],
    cl: float,
    ucl: float | Sequence[float],
    lcl: float | Sequence[float],
    violations: Sequence[Mapping[str, int | str]] | None = None,
    title: str = "Control Chart",
    y_axis_title: str = "Value",
    x_axis_title: str = "Subgroup",
) -> go.Figure:
    x_values = list(range(1, len(points) + 1))
    point_values = list(points)
    ucl_values = _expand_limit(ucl, len(point_values))
    lcl_values = _expand_limit(lcl, len(point_values))
    cl_values = [cl] * len(point_values)

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=x_values,
            y=point_values,
            mode="lines+markers",
            name="Process",
            line={"color": AMBER, "width": 2},
            marker={"size": 8, "color": AMBER},
        )
    )
    figure.add_trace(_limit_trace(x_values, ucl_values, "UCL"))
    figure.add_trace(_limit_trace(x_values, lcl_values, "LCL"))
    figure.add_trace(
        go.Scatter(
            x=x_values,
            y=cl_values,
            mode="lines",
            name="CL",
            line={"color": VIOLET, "width": 2, "dash": "dot"},
            hoverinfo="skip",
        )
    )

    if violations:
        violation_x = []
        violation_y = []
        hover_text = []
        for violation in violations:
            index = int(violation["index"])
            violation_x.append(x_values[index])
            violation_y.append(point_values[index])
            hover_text.append(str(violation["rule"]))

        figure.add_trace(
            go.Scatter(
                x=violation_x,
                y=violation_y,
                mode="markers",
                name="Violations",
                marker={
                    "size": 13,
                    "color": "rgba(0,0,0,0)",
                    "line": {"color": DANGER, "width": 2},
                    "symbol": "circle-open",
                },
                hovertemplate="%{text}<extra></extra>",
                text=hover_text,
            )
        )

    figure.update_layout(
        title=title,
        xaxis_title=x_axis_title,
        yaxis_title=y_axis_title,
        legend={"orientation": "h", "y": 1.08, "x": 0,
                "bgcolor": "rgba(0,0,0,0)", "font": {"color": TEXT_SECONDARY}},
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("legend", "margin")},
        margin={"l": 40, "r": 20, "t": 60, "b": 40},
    )
    return figure


def build_ewma_chart(
    result: EWMAResult,
    title: str = "EWMA Control Chart",
    y_axis_title: str = "EWMA",
) -> go.Figure:
    violations: list[Mapping[str, int | str]] = [
        {"index": i, "rule": "EWMA limit exceeded"} for i in result["signals"]
    ]
    return build_control_chart(
        points=result["z"],
        cl=result["mu0"],
        ucl=result["ucl"],
        lcl=result["lcl"],
        violations=violations,
        title=title,
        y_axis_title=y_axis_title,
        x_axis_title="Observation",
    )


def build_cusum_chart(
    result: CUSUMResult,
    title: str = "CUSUM Control Chart",
    y_axis_title: str = "Cumulative Sum",
) -> go.Figure:
    x_values = list(range(1, len(result["values"]) + 1))
    c_plus = result["c_plus"]
    c_minus_negated = [-value for value in result["c_minus"]]
    h = result["h"]

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=x_values,
            y=c_plus,
            mode="lines+markers",
            name="C+",
            line={"color": AMBER, "width": 2},
            marker={"size": 8, "color": AMBER},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=x_values,
            y=c_minus_negated,
            mode="lines+markers",
            name="C-",
            line={"color": VIOLET, "width": 2},
            marker={"size": 8, "color": VIOLET},
        )
    )
    figure.add_trace(_limit_trace(x_values, [h] * len(x_values), "+h"))
    figure.add_trace(_limit_trace(x_values, [-h] * len(x_values), "−h"))

    if result["signals"]:
        signal_x = []
        signal_y = []
        for i in result["signals"]:
            signal_x.append(x_values[i])
            signal_y.append(c_plus[i] if c_plus[i] > h else -result["c_minus"][i])

        figure.add_trace(
            go.Scatter(
                x=signal_x,
                y=signal_y,
                mode="markers",
                name="Violations",
                marker={
                    "size": 13,
                    "color": "rgba(0,0,0,0)",
                    "line": {"color": DANGER, "width": 2},
                    "symbol": "circle-open",
                },
            )
        )

    figure.update_layout(
        title=title,
        xaxis_title="Observation",
        yaxis_title=y_axis_title,
        legend={"orientation": "h", "y": 1.08, "x": 0,
                "bgcolor": "rgba(0,0,0,0)", "font": {"color": TEXT_SECONDARY}},
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("legend", "margin")},
        margin={"l": 40, "r": 20, "t": 60, "b": 40},
    )
    return figure


def build_capability_histogram(
    data: Sequence[float] | np.ndarray,
    lsl: float | None,
    usl: float | None,
    mean: float,
    sigma_overall: float,
    title: str = "Capability Histogram",
    *,
    method: str = "normal",
    fitted_dist: str | None = None,
    lambda_used: float | None = None,
    shift: float = 0.0,
) -> go.Figure:
    """Raw-data histogram with a method-appropriate density overlay (SME Q3, W10-5 #145):

    - "normal" (default, unchanged): normal fit computed from `mean`/`sigma_overall`.
    - "percentile": overlay the min-AIC `fitted_dist` winner's `.pdf`, refit on the raw
      `data` (already raw-space — no back-transform needed).
    - "boxcox" / "yeojohnson": `mean`/`sigma_overall` are the TRANSFORMED-space normal
      fit (as `compute_capability_study` returns them); back-transform via
      change-of-variables `f_X(x) = phi((t(x)-mu_t)/sigma_t)/sigma_t * |t'(x)|`.
    """
    values = np.asarray(data, dtype=float)
    # The x-axis range always comes from the RAW data's own spread, independent of
    # `sigma_overall` (which is transformed-space for boxcox/yeojohnson) — otherwise
    # a transformed-space sigma would mis-scale the raw-space axis.
    raw_sigma = float(np.std(values, ddof=1))
    x_min = values.min() - (3 * raw_sigma)
    x_max = values.max() + (3 * raw_sigma)
    x_curve = np.linspace(x_min, x_max, 400)

    if method == "percentile" and fitted_dist is not None:
        dist = getattr(stats, fitted_dist)
        params = dist.fit(values)
        pdf = dist.pdf(x_curve, *params)
        curve_name = f"Fitted {fitted_dist}"
    elif method in ("boxcox", "yeojohnson") and lambda_used is not None:
        pdf = _backtransformed_pdf(x_curve, method, lambda_used, shift, mu_t=mean, sigma_t=sigma_overall)
        curve_name = f"Fitted Normal ({method}, λ={lambda_used:.3g})"
    else:
        pdf = (1.0 / (sigma_overall * np.sqrt(2.0 * np.pi))) * np.exp(
            -0.5 * ((x_curve - mean) / sigma_overall) ** 2
        )
        curve_name = "Normal Fit"

    figure = go.Figure()
    figure.add_trace(
        go.Histogram(
            x=values,
            nbinsx=min(20, max(8, len(values) // 2)),
            histnorm="probability density",
            name="Data",
            marker={"color": AMBER, "line": {"color": "white", "width": 1}},
            opacity=0.8,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=x_curve,
            y=pdf,
            mode="lines",
            name=curve_name,
            line={"color": VIOLET, "width": 3},
        )
    )

    if lsl is not None:
        figure.add_vline(x=lsl, line_color=DANGER, line_dash="dash", annotation_text="LSL")
    if usl is not None:
        figure.add_vline(x=usl, line_color=DANGER, line_dash="dash", annotation_text="USL")

    figure.update_layout(
        title=title,
        xaxis_title="Measurement",
        yaxis_title="Density",
        barmode="overlay",
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("margin",)},
        margin={"l": 40, "r": 20, "t": 60, "b": 40},
    )
    return figure


def build_cpk_gauge(cpk: float | None, title: str = "Cpk") -> go.Figure:
    if cpk is None:
        figure = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=0,
                title={"text": f"{title} — N/A"},
                gauge={
                    "axis": {"range": [0, 2.0]},
                    "bar": {"color": "#374151"},
                    "steps": [
                        {"range": [0.0, 1.0], "color": "#1a1f2e"},
                        {"range": [1.0, 1.33], "color": "#1a1f2e"},
                        {"range": [1.33, 2.0], "color": "#1a1f2e"},
                    ],
                },
            )
        )
        figure.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font={"color": "#f1f5f9"},
            margin={"l": 30, "r": 30, "t": 60, "b": 30},
        )
        return figure

    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=cpk,
            title={"text": title},
            gauge={
                "axis": {"range": [0, max(2.0, cpk + 0.3)]},
                "bar": {"color": "#f59e0b"},
                "steps": [
                    {"range": [0.0, 1.0], "color": "#3b0d0d"},
                    {"range": [1.0, 1.33], "color": "#3b2800"},
                    {"range": [1.33, max(2.0, cpk + 0.3)], "color": "#0d2b1e"},
                ],
                "threshold": {"line": {"color": "#ef4444", "width": 4}, "value": 1.33},
            },
        )
    )
    figure.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f1f5f9"},
        margin={"l": 30, "r": 30, "t": 60, "b": 30},
    )
    return figure


def _backtransformed_pdf(
    x: np.ndarray, method: str, lam: float, shift: float, *, mu_t: float, sigma_t: float
) -> np.ndarray:
    """Exact raw-space density for a Box-Cox/Yeo-Johnson-normal capability study
    (SME Q3 pinned formula, W10-5 #145): `f_X(x) = phi(z)/sigma_t * |t'(x)|`,
    `z = (t(x)-mu_t)/sigma_t`, where `t`/`t'` are the transform and its derivative.
    """
    t, t_prime = _transform_and_derivative(x, method, lam, shift)
    z = (t - mu_t) / sigma_t
    phi = np.exp(-0.5 * z**2) / np.sqrt(2.0 * np.pi)
    return (phi / sigma_t) * np.abs(t_prime)


def _transform_and_derivative(
    x: np.ndarray, method: str, lam: float, shift: float
) -> tuple[np.ndarray, np.ndarray]:
    if method == "boxcox":
        # Box-Cox is only defined for a positive argument; the axis padding beyond
        # the observed data can dip non-positive, so it's clamped to a small
        # epsilon there (ponytail: flattens the far tail slightly, negligible
        # over the actual data range where x+shift is always > 0 by construction).
        xs = np.clip(x + shift, 1e-12, None)
        if lam == 0.0:
            t = np.log(xs)
        else:
            t = (np.power(xs, lam) - 1.0) / lam
        t_prime = np.power(xs, lam - 1.0)
        return t, t_prime

    # Yeo-Johnson: piecewise on the sign of x (shift is always 0.0 for this method).
    xs = x + shift
    t = np.empty_like(xs)
    t_prime = np.empty_like(xs)
    pos = xs >= 0
    neg = ~pos

    if lam != 0.0:
        t[pos] = (np.power(xs[pos] + 1.0, lam) - 1.0) / lam
    else:
        t[pos] = np.log(xs[pos] + 1.0)
    t_prime[pos] = np.power(xs[pos] + 1.0, lam - 1.0)

    if lam != 2.0:
        t[neg] = -(np.power(-xs[neg] + 1.0, 2.0 - lam) - 1.0) / (2.0 - lam)
    else:
        t[neg] = -np.log(-xs[neg] + 1.0)
    t_prime[neg] = np.power(-xs[neg] + 1.0, 1.0 - lam)

    return t, t_prime


def _expand_limit(limit: float | Sequence[float], length: int) -> list[float]:
    if isinstance(limit, (int, float)):
        return [float(limit)] * length
    return [float(value) for value in limit]


def _limit_trace(x_values: list[int], y_values: list[float], name: str) -> go.Scatter:
    return go.Scatter(
        x=x_values,
        y=y_values,
        mode="lines",
        name=name,
        line={"color": DANGER, "width": 2, "dash": "dash"},
        hoverinfo="skip",
    )
