"""
theme.py
FMEA Risk Prioritization Tool — Single source of truth for Risk Tier visual encodings.

All color constants in the codebase should import from here rather than
hardcoding values in individual modules.

Author: Siddardth | M.S. Aerospace Engineering, UIUC
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Hex colors — used by matplotlib (visualizer.py) and plotly (plotly_charts.py)
# Values: #e74c3c / #f39c12 / #27ae60 — chosen to match the established palette
# in visualizer.py and plotly_charts.py (bold accent colors, not pastels).
# ---------------------------------------------------------------------------

TIER_HEX: dict[str, str] = {
    "Red":    "#e74c3c",
    "Yellow": "#f39c12",
    "Green":  "#27ae60",
}

# ---------------------------------------------------------------------------
# Integer rank for heatmap cell ordering (higher = more severe tier).
# Used by visualizer.py risk_heatmap and plotly_charts.py risk_heatmap_plotly.
# ---------------------------------------------------------------------------

TIER_RANK: dict[str, int] = {
    "Green": 0,
    "Yellow": 1,
    "Red": 2,
}

# ---------------------------------------------------------------------------
# RGB tuples (0–255) for fpdf2 row fill colors in PDF export.
# These are intentionally pastel (light background) so text remains readable.
# ---------------------------------------------------------------------------

TIER_RGB: dict[str, tuple[int, int, int]] = {
    "Red":    (252, 228, 228),
    "Yellow": (255, 249, 230),
    "Green":  (232, 248, 239),
}

# ---------------------------------------------------------------------------
# openpyxl PatternFill hex strings (no leading #) for Excel export row fills.
# Pastel backgrounds — matches _TIER_FILL in exporter.py.
# ---------------------------------------------------------------------------

TIER_FILL_HEX: dict[str, str] = {
    "Red":    "FCE4E4",
    "Yellow": "FFF9E6",
    "Green":  "E8F8EF",
}
