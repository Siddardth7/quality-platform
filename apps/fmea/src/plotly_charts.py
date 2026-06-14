"""
plotly_charts.py
FMEA Risk Prioritization Tool — Plotly Visualization Layer (Streamlit)

Functions:
    pareto_chart_plotly(df, dark)   — Interactive Pareto chart of failure modes ranked by RPN
    risk_heatmap_plotly(df, dark)   — Interactive Severity × Occurrence heatmap

Both functions return a plotly.graph_objects.Figure ready for st.plotly_chart().
They accept the same analyzed DataFrame as visualizer.py (output of run_pipeline).

Author: Siddardth | M.S. Aerospace Engineering, UIUC
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.theme import FAILURE_MODE_TRUNC, TIER_HEX
from src.theme import TIER_RANK as _TIER_RANK_BASE

# ---------------------------------------------------------------------------
# Color palette — imported from src.theme (single source of truth)
# ---------------------------------------------------------------------------

TIER_COLORS = TIER_HEX

TIER_LABELS = {
    "Red":    "Red — Immediate action",
    "Yellow": "Yellow — Action recommended",
    "Green":  "Green — Monitor",
}

# ---------------------------------------------------------------------------
# Theme helpers
# ---------------------------------------------------------------------------

def _theme(dark: bool) -> dict:
    if dark:
        return dict(
            bg="#1a1f2e",
            paper="#0e1117",
            text="#c9d1d9",
            grid="#30363d",
            line="#58a6ff",
            ref_line="#8b949e",
        )
    return dict(
        bg="white",
        paper="white",
        text="#2c3e50",
        grid="#e8ecef",
        line="#2c3e50",
        ref_line="#7f8c8d",
    )


# ---------------------------------------------------------------------------
# pareto_chart_plotly
# ---------------------------------------------------------------------------

def pareto_chart_plotly(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """
    Generate an interactive Plotly Pareto chart for use in Streamlit.

    Combines a descending bar chart (colored by Risk_Tier) with a
    cumulative RPN % line and an 80% reference line.

    Parameters
    ----------
    df : pd.DataFrame
        Analyzed FMEA DataFrame — output of run_pipeline() or rank_by_rpn().
        Must contain columns: Failure_Mode, RPN, Risk_Tier.
    dark : bool
        If True, render with dark background theme.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    t = _theme(dark)

    df_sorted = df.sort_values("RPN", ascending=False).reset_index(drop=True)

    labels         = [str(fm)[:FAILURE_MODE_TRUNC] for fm in df_sorted["Failure_Mode"]]
    rpns           = df_sorted["RPN"].values.astype(float)
    tiers          = df_sorted["Risk_Tier"].values
    bar_colors     = [TIER_COLORS.get(t_name, "#95a5a6") for t_name in tiers]
    cumulative_pct = np.cumsum(rpns) / rpns.sum() * 100 if rpns.sum() > 0 else rpns * 0

    fig = go.Figure()

    # --- Single Bar trace with per-bar colors ---
    hover_texts = [
        f"<b>{labels[i]}</b><br>RPN: {int(rpns[i])}<br>Tier: {tiers[i]}"
        for i in range(len(labels))
    ]
    _TIER_LETTER = {"Red": "R", "Yellow": "Y", "Green": "G"}
    bar_text = [
        f"{int(r)} [{_TIER_LETTER.get(t_name, '?')}]"
        for r, t_name in zip(rpns, tiers)
    ]

    fig.add_trace(go.Bar(
        x=labels,
        y=rpns,
        marker_color=bar_colors,
        marker_line_width=0,
        yaxis="y1",
        text=bar_text,
        textposition="outside",
        textfont=dict(size=9, color=t["text"]),
        hovertext=hover_texts,
        hoverinfo="text",
        showlegend=False,
        name="RPN",
    ))

    # --- Invisible scatter traces for tier legend ---
    for tier_name, tier_color in TIER_COLORS.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=11, color=tier_color, symbol="square"),
            name=TIER_LABELS[tier_name],
            yaxis="y1",
        ))

    # --- Cumulative % line (right y-axis) ---
    fig.add_trace(go.Scatter(
        x=labels,
        y=cumulative_pct,
        mode="lines+markers",
        name="Cumulative RPN %",
        yaxis="y2",
        line=dict(color=t["line"], width=2.5),
        marker=dict(size=5, color=t["line"]),
        hovertemplate="<b>%{x}</b><br>Cumulative: %{y:.1f}%<extra></extra>",
    ))

    # --- 80% reference line as a Scatter on y2 ---
    if len(labels) > 0:
        fig.add_trace(go.Scatter(
            x=[labels[0], labels[-1]],
            y=[80, 80],
            mode="lines",
            yaxis="y2",
            line=dict(color=t["ref_line"], dash="dash", width=1.5),
            name="80% threshold",
            hoverinfo="skip",
        ))

    fig.update_layout(
        title=dict(
            text="FMEA Pareto Chart — Failure Modes Ranked by RPN",
            font=dict(size=16, color=t["text"]),
            x=0.0,
        ),
        xaxis=dict(
            title=dict(text="Failure Mode", font=dict(color=t["text"])),
            tickangle=-50,
            tickfont=dict(size=10, color=t["text"]),
            gridcolor=t["grid"],
            linecolor=t["grid"],
        ),
        yaxis=dict(
            title=dict(text="RPN", font=dict(color=t["text"])),
            tickfont=dict(color=t["text"]),
            gridcolor=t["grid"],
            linecolor=t["grid"],
        ),
        yaxis2=dict(
            title=dict(text="Cumulative RPN (%)", font=dict(color=t["text"])),
            overlaying="y",
            side="right",
            range=[0, 112],
            tickfont=dict(color=t["text"]),
            gridcolor="rgba(0,0,0,0)",
        ),
        barmode="relative",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=t["text"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=620,
        plot_bgcolor=t["bg"],
        paper_bgcolor=t["paper"],
        font=dict(color=t["text"]),
        margin=dict(l=60, r=80, t=80, b=160),
        hoverlabel=dict(bgcolor=t["bg"], font=dict(color=t["text"])),
    )

    return fig


# ---------------------------------------------------------------------------
# risk_heatmap_plotly
# ---------------------------------------------------------------------------

def risk_heatmap_plotly(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """
    Generate an interactive Plotly Severity × Occurrence risk heatmap.

    Each occupied cell shows the count of failure modes.
    Cell color reflects the highest Risk_Tier present (Red > Yellow > Green).

    Parameters
    ----------
    df : pd.DataFrame
        Analyzed FMEA DataFrame — output of run_pipeline() or rank_by_rpn().
        Must contain columns: Severity, Occurrence, Risk_Tier.
    dark : bool
        If True, render with dark background theme.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    t = _theme(dark)
    empty_color = "#2a2f3e" if dark else "#f0f0f0"

    # Shift theme's 0-based TIER_RANK by 1: 0 is reserved for empty cells in the colorscale
    TIER_RANK = {k: v + 1 for k, v in _TIER_RANK_BASE.items()}

    grid_count     = np.zeros((10, 10), dtype=int)
    grid_tier_rank = np.zeros((10, 10), dtype=int)

    for _, row in df.iterrows():
        s = int(row["Severity"])   - 1
        o = int(row["Occurrence"]) - 1
        grid_count[s, o] += 1
        tier_r = TIER_RANK.get(row["Risk_Tier"], 1)
        if tier_r > grid_tier_rank[s, o]:
            grid_tier_rank[s, o] = tier_r

    colorscale = [
        [0.00, empty_color],
        [0.01, empty_color],
        [0.34, TIER_HEX["Green"]],
        [0.34, TIER_HEX["Green"]],
        [0.67, TIER_HEX["Yellow"]],
        [0.67, TIER_HEX["Yellow"]],
        [1.00, TIER_HEX["Red"]],
    ]

    text_matrix = [
        [str(grid_count[i, j]) if grid_count[i, j] > 0 else ""
         for j in range(10)]
        for i in range(10)
    ]

    tier_name_map = {0: "No failures", 1: "Green", 2: "Yellow", 3: "Red"}
    hover_matrix = [
        [
            f"Severity: {i+1}<br>Occurrence: {j+1}<br>"
            f"Count: {grid_count[i,j]}<br>Tier: {tier_name_map[grid_tier_rank[i,j]]}"
            for j in range(10)
        ]
        for i in range(10)
    ]

    fig = go.Figure(data=go.Heatmap(
        z=grid_tier_rank,
        x=list(range(1, 11)),
        y=list(range(1, 11)),
        colorscale=colorscale,
        zmin=0,
        zmax=3,
        showscale=False,
        text=text_matrix,
        texttemplate="%{text}",
        textfont=dict(size=13, color="white"),
        hoverinfo="text",
        hovertext=hover_matrix,
        xgap=3,
        ygap=3,
    ))

    # Legend markers
    for tier_name, tier_color in TIER_COLORS.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=12, color=tier_color, symbol="square"),
            name=TIER_LABELS[tier_name],
            showlegend=True,
        ))

    fig.update_layout(
        title=dict(
            text="FMEA Risk Heatmap — Severity x Occurrence",
            font=dict(size=16, color=t["text"]),
            x=0.0,
        ),
        xaxis=dict(
            title=dict(text="Occurrence (O)", font=dict(color=t["text"])),
            tickmode="linear",
            tick0=1, dtick=1,
            constrain="domain",
            tickfont=dict(color=t["text"]),
            gridcolor=t["grid"],
        ),
        yaxis=dict(
            title=dict(text="Severity (S)", font=dict(color=t["text"])),
            tickmode="linear",
            tick0=1, dtick=1,
            scaleanchor="x",
            tickfont=dict(color=t["text"]),
            gridcolor=t["grid"],
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=t["text"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=580,
        plot_bgcolor=t["bg"],
        paper_bgcolor=t["paper"],
        font=dict(color=t["text"]),
        margin=dict(l=60, r=40, t=80, b=60),
        hoverlabel=dict(bgcolor=t["bg"], font=dict(color=t["text"])),
    )

    return fig
