"""
visualizer.py
FMEA Risk Prioritization Tool — Visualization Layer

Functions:
    pareto_chart(df, output_path)  — Pareto chart of failure modes ranked by RPN
    risk_heatmap(df, output_path)  — Severity × Occurrence heatmap colored by Risk Tier

Both functions accept an already-analyzed DataFrame (output of run_pipeline) and
optionally save the figure to disk. If output_path is None the figure is returned
without saving.

Engineering reference: AIAG FMEA-4 (4th Edition)
See docs/ASSUMPTIONS_LOG.md for threshold decisions.

Author: Siddardth | M.S. Aerospace Engineering, UIUC
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")          # non-interactive backend — safe for CLI and tests
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.theme import FAILURE_MODE_TRUNC, TIER_HEX
from src.theme import TIER_RANK as _TIER_RANK_MAP

# ---------------------------------------------------------------------------
# Color palette — imported from src.theme (single source of truth)
# ---------------------------------------------------------------------------

TIER_COLORS = TIER_HEX

# Pareto chart safety + presentation caps
PARETO_TOP_N = 30                # show this many highest-RPN bars individually
PARETO_FIGWIDTH_MAX = 24.0       # inches; hard cap so savefig cannot blow up memory

# ---------------------------------------------------------------------------
# pareto_chart
# ---------------------------------------------------------------------------

def pareto_chart(
    df: pd.DataFrame,
    output_path: Optional[str | Path] = None,
) -> plt.Figure:
    """
    Generate a Pareto chart of failure modes ranked by RPN.

    The chart combines:
      - A descending bar chart where each bar is colored by Risk_Tier
        (Red / Yellow / Green per AIAG FMEA-4 thresholds)
      - A cumulative RPN % line (right-hand y-axis) with an 80 % reference line

    Parameters
    ----------
    df : pd.DataFrame
        Analyzed FMEA DataFrame — output of run_pipeline() or rank_by_rpn().
        Must contain columns: Failure_Mode, RPN, Risk_Tier.

    output_path : str or Path, optional
        If provided, the figure is saved as a PNG at this path and the figure
        is closed. If None, the figure is returned open for display or testing.

    Returns
    -------
    matplotlib.figure.Figure
        The generated Pareto chart figure.

    Raises
    ------
    KeyError
        If required columns (Failure_Mode, RPN, Risk_Tier) are missing.
    """
    _check_columns(df, ["Failure_Mode", "RPN", "Risk_Tier"])

    df_sorted = df.sort_values("RPN", ascending=False).reset_index(drop=True)
    total_rpn = float(df_sorted["RPN"].sum())

    # --- Top-N + Others aggregation (F-038) ---
    if len(df_sorted) > PARETO_TOP_N:
        top = df_sorted.head(PARETO_TOP_N)
        others = df_sorted.iloc[PARETO_TOP_N:]
        others_row = pd.DataFrame([{
            "Failure_Mode": f"Others (N={len(others)})",
            "RPN":          int(others["RPN"].sum()),
            "Risk_Tier":    "Green",  # aggregate bar is informational only
        }])
        df_sorted = pd.concat([top, others_row], ignore_index=True)

    labels = [str(fm)[:FAILURE_MODE_TRUNC] for fm in df_sorted["Failure_Mode"]]
    rpns   = df_sorted["RPN"].values
    tiers  = df_sorted["Risk_Tier"].values
    colors = [TIER_COLORS.get(t, "#95a5a6") for t in tiers]

    cumulative_pct = (
        np.cumsum(rpns) / total_rpn * 100 if total_rpn > 0 else np.zeros_like(rpns, dtype=float)
    )

    # --- Width-capped figure (F-038) ---
    desired_w = max(12.0, len(labels) * 0.55)
    fig_w = min(desired_w, PARETO_FIGWIDTH_MAX)
    fig, ax1 = plt.subplots(figsize=(fig_w, 7))

    # --- Bar chart (left axis) ---
    bars = ax1.bar(range(len(labels)), rpns, color=colors, edgecolor="white", linewidth=0.5)
    ax1.set_ylabel("RPN", fontsize=11, fontweight="bold")
    ax1.set_ylim(0, max(rpns) * 1.18 if len(rpns) else 1)
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax1.tick_params(axis="y", labelsize=9)

    for bar, rpn in zip(bars, rpns):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max(rpns) if len(rpns) else 1) * 0.01,
            str(int(rpn)),
            ha="center", va="bottom", fontsize=7, fontweight="bold",
        )

    # --- Cumulative % line (right axis) ---
    ax2 = ax1.twinx()
    ax2.plot(
        range(len(labels)), cumulative_pct,
        color="#2c3e50", marker="o", markersize=4,
        linewidth=1.8, label="Cumulative RPN %",
    )
    ax2.axhline(80, color="#7f8c8d", linestyle="--", linewidth=1.0, label="80 % line")
    ax2.set_ylabel("Cumulative RPN (%)", fontsize=11, fontweight="bold")
    ax2.set_ylim(0, 110)
    ax2.tick_params(axis="y", labelsize=9)

    legend_patches = [
        mpatches.Patch(color=TIER_COLORS["Red"],    label="Red — Immediate action"),
        mpatches.Patch(color=TIER_COLORS["Yellow"], label="Yellow — Action recommended"),
        mpatches.Patch(color=TIER_COLORS["Green"],  label="Green — Monitor"),
    ]
    ax1.legend(
        handles=legend_patches,
        loc="upper right", fontsize=9,
        framealpha=0.9, edgecolor="#bdc3c7",
    )

    ax1.set_title(
        "FMEA Pareto Chart — Failure Modes Ranked by RPN",
        fontsize=13, fontweight="bold", pad=14,
    )
    ax1.set_xlabel("Failure Mode", fontsize=11, fontweight="bold", labelpad=8)
    fig.tight_layout()

    if output_path is not None:
        fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
        plt.close(fig)

    return fig


# ---------------------------------------------------------------------------
# risk_heatmap
# ---------------------------------------------------------------------------

def risk_heatmap(
    df: pd.DataFrame,
    output_path: Optional[str | Path] = None,
) -> plt.Figure:
    """
    Generate a Severity × Occurrence risk heatmap.

    Each cell (S, O) shows the count of failure modes with that combination.
    Cells are colored by the dominant Risk_Tier in that cell:
      Red > Yellow > Green (most severe tier wins).

    A Detection score legend is not shown — this is a 2-D risk matrix
    consistent with standard FMEA risk matrix practice.

    Parameters
    ----------
    df : pd.DataFrame
        Analyzed FMEA DataFrame — output of run_pipeline() or rank_by_rpn().
        Must contain columns: Severity, Occurrence, Risk_Tier.

    output_path : str or Path, optional
        If provided, the figure is saved as a PNG at this path and the figure
        is closed. If None, the figure is returned open for display or testing.

    Returns
    -------
    matplotlib.figure.Figure
        The generated heatmap figure.

    Raises
    ------
    KeyError
        If required columns (Severity, Occurrence, Risk_Tier) are missing.
    """
    _check_columns(df, ["Severity", "Occurrence", "Risk_Tier"])

    # Build a 10×10 grid: rows = Severity 1–10, cols = Occurrence 1–10
    grid_count     = np.zeros((10, 10), dtype=int)
    grid_tier_rank = np.full((10, 10), -1, dtype=int)

    for _, row in df.iterrows():
        s = int(row["Severity"]) - 1      # 0-indexed
        o = int(row["Occurrence"]) - 1
        grid_count[s, o] += 1
        tier_r = _TIER_RANK_MAP.get(row["Risk_Tier"], -1)
        if tier_r > grid_tier_rank[s, o]:
            grid_tier_rank[s, o] = tier_r

    # Build RGBA image — vectorized via np.take on a lookup table (F-035)
    # Rank indices: -1 → 0 (sentinel), 0 → 1 (Green), 1 → 2 (Yellow), 2 → 3 (Red)
    _RGBA_LUT = np.array([
        [0.96, 0.96, 0.96, 1.00],   # index 0: empty cell (rank -1) — light grey
        [0.39, 0.68, 0.38, 0.75],   # index 1: Green  (rank 0)
        [0.95, 0.61, 0.07, 0.80],   # index 2: Yellow (rank 1)
        [0.91, 0.30, 0.24, 0.85],   # index 3: Red    (rank 2)
    ])  # shape (4, 4)
    lut_indices = grid_tier_rank + 1          # shift -1…2 → 0…3
    rgba_grid = _RGBA_LUT[lut_indices]        # shape (10, 10, 4) — no Python loop

    fig, ax = plt.subplots(figsize=(10, 9))
    ax.imshow(
        rgba_grid,
        origin="lower",
        extent=(0.5, 10.5, 0.5, 10.5),
        aspect="auto",
        interpolation="nearest",
    )

    # Annotate cells with count
    for i in range(10):
        for j in range(10):
            count = grid_count[i, j]
            if count > 0:
                ax.text(
                    j + 1, i + 1, str(count),
                    ha="center", va="center",
                    fontsize=10, fontweight="bold", color="white",
                )

    ax.set_xticks(range(1, 11))
    ax.set_yticks(range(1, 11))
    ax.set_xticklabels([str(i) for i in range(1, 11)], fontsize=9)
    ax.set_yticklabels([str(i) for i in range(1, 11)], fontsize=9)
    ax.set_xlabel("Occurrence (O)", fontsize=12, fontweight="bold", labelpad=8)
    ax.set_ylabel("Severity (S)", fontsize=12, fontweight="bold", labelpad=8)
    ax.set_title(
        "FMEA Risk Heatmap — Severity × Occurrence\n"
        "(cell count = number of failure modes; color = highest Risk Tier in cell)",
        fontsize=12, fontweight="bold", pad=14,
    )

    # Grid lines
    ax.set_xticks([x + 0.5 for x in range(1, 10)], minor=True)
    ax.set_yticks([y + 0.5 for y in range(1, 10)], minor=True)
    ax.grid(which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", length=0)

    # Legend
    legend_patches = [
        mpatches.Patch(color=TIER_COLORS["Red"],    label="Red — Immediate action"),
        mpatches.Patch(color=TIER_COLORS["Yellow"], label="Yellow — Action recommended"),
        mpatches.Patch(color=TIER_COLORS["Green"],  label="Green — Monitor"),
        mpatches.Patch(facecolor="#f5f5f5", edgecolor="#bdc3c7", label="No failure modes"),
    ]
    ax.legend(
        handles=legend_patches,
        loc="upper left", fontsize=9,
        framealpha=0.92, edgecolor="#bdc3c7",
    )

    fig.tight_layout()

    if output_path is not None:
        fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
        plt.close(fig)

    return fig


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(
            f"visualizer: missing column(s) {missing}. "
            "Pass the output of run_pipeline() or rank_by_rpn()."
        )
