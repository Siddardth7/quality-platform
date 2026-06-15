"""Quality Platform palette — pure data, no UI-framework imports.

The single source of truth for colors across every app surface (Streamlit chrome,
Plotly/Matplotlib charts, and PDF/Excel exports). Intentionally free of any
streamlit/plotly import so non-UI consumers (the FMEA CLI export/visualizer path)
can use the tokens without pulling in a UI framework. `apply_theme()` (which does
need streamlit) lives in the sibling ``style`` module.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Base palette — dark amber/violet (adopted from the SPC dashboard).
# ---------------------------------------------------------------------------
AMBER = "#f59e0b"
AMBER_DARK = "#d97706"
VIOLET = "#8b5cf6"
BG_PRIMARY = "#0e1117"
BG_SECONDARY = "#161b27"
BG_CARD = "#1e2535"
BORDER = "#2d3748"
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
SUCCESS = "#10b981"
DANGER = "#ef4444"

# ---------------------------------------------------------------------------
# Plotly base layout — shared dark chart styling.
# ---------------------------------------------------------------------------
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=BG_SECONDARY,
    font=dict(color=TEXT_PRIMARY, family="Inter, sans-serif"),
    xaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=TEXT_SECONDARY)),
    yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=TEXT_SECONDARY)),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SECONDARY)),
    title_font=dict(color=TEXT_PRIMARY, size=16),
    margin=dict(l=40, r=20, t=60, b=40),
)

# ---------------------------------------------------------------------------
# Risk-tier semantic tokens (RPN Red / Yellow / Green) — folded in from FMEA.
# Values preserved exactly so existing chart/PDF/Excel output is unchanged.
# ---------------------------------------------------------------------------

# Bold accent hex — chart fills (matplotlib visualizer + plotly charts).
TIER_HEX: dict[str, str] = {
    "Red":    "#e74c3c",
    "Yellow": "#f39c12",
    "Green":  "#27ae60",
}

# Integer severity rank for heatmap cell ordering (higher = more severe).
TIER_RANK: dict[str, int] = {
    "Green": 0,
    "Yellow": 1,
    "Red": 2,
}

# Pastel RGB (0–255) for fpdf2 PDF row fills (light background, readable text).
TIER_RGB: dict[str, tuple[int, int, int]] = {
    "Red":    (252, 228, 228),
    "Yellow": (255, 249, 230),
    "Green":  (232, 248, 239),
}

# Pastel hex (no leading #) for openpyxl Excel row fills.
TIER_FILL_HEX: dict[str, str] = {
    "Red":    "FCE4E4",
    "Yellow": "FFF9E6",
    "Green":  "E8F8EF",
}

# ---------------------------------------------------------------------------
# Shared display constant — Pareto x-axis label truncation, kept consistent
# across the matplotlib and plotly renderers.
# ---------------------------------------------------------------------------
FAILURE_MODE_TRUNC = 40
