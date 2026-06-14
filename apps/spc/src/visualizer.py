"""Pure Plotly figure builders for the SPC dashboard."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import plotly.graph_objects as go

from src.ui.theme import AMBER, VIOLET, DANGER, TEXT_SECONDARY, PLOTLY_LAYOUT


def build_control_chart(
    points: Sequence[float],
    cl: float,
    ucl: float | Sequence[float],
    lcl: float | Sequence[float],
    violations: Sequence[dict[str, object]] | None = None,
    title: str = "Control Chart",
    y_axis_title: str = "Value",
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
        xaxis_title="Subgroup",
        yaxis_title=y_axis_title,
        legend={"orientation": "h", "y": 1.08, "x": 0,
                "bgcolor": "rgba(0,0,0,0)", "font": {"color": TEXT_SECONDARY}},
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("legend", "margin")},
        margin={"l": 40, "r": 20, "t": 60, "b": 40},
    )
    return figure


def build_capability_histogram(
    data: Sequence[float],
    lsl: float | None,
    usl: float | None,
    mean: float,
    sigma_overall: float,
    title: str = "Capability Histogram",
) -> go.Figure:
    values = np.asarray(data, dtype=float)
    x_min = values.min() - (3 * sigma_overall)
    x_max = values.max() + (3 * sigma_overall)
    x_curve = np.linspace(x_min, x_max, 400)
    pdf = (1.0 / (sigma_overall * np.sqrt(2.0 * np.pi))) * np.exp(
        -0.5 * ((x_curve - mean) / sigma_overall) ** 2
    )

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
            name="Normal Fit",
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
