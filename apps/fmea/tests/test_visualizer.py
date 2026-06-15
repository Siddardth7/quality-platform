"""
test_visualizer.py
Unit tests for src/visualizer.py

Tests cover:
  - pareto_chart: returns a Figure, correct number of bars, saves to disk
  - risk_heatmap: returns a Figure, handles sparse data, saves to disk
  - Both functions raise KeyError on missing required columns

Run:
    pytest tests/test_visualizer.py -v
"""

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fmea_app.rpn_engine import run_pipeline
from fmea_app.visualizer import pareto_chart, risk_heatmap

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Minimal 5-row FMEA DataFrame run through the full pipeline."""
    data = {
        "ID":              [1,   2,   3,   4,   5],
        "Process_Step":    ["A", "B", "C", "D", "E"],
        "Component":       ["X", "X", "X", "X", "X"],
        "Function":        ["F", "F", "F", "F", "F"],
        "Failure_Mode":    ["FM-A", "FM-B", "FM-C", "FM-D", "FM-E"],
        "Effect":          ["E", "E", "E", "E", "E"],
        "Severity":        [9,   8,   7,   5,   3],
        "Cause":           ["C", "C", "C", "C", "C"],
        "Occurrence":      [4,   3,   2,   4,   2],
        "Current_Control": ["Ctrl"] * 5,
        "Detection":       [5,   4,   3,   2,   2],
    }
    return run_pipeline(pd.DataFrame(data))


@pytest.fixture(autouse=True)
def close_figures():
    """Close all matplotlib figures after each test to avoid resource warnings."""
    yield
    plt.close("all")


# ---------------------------------------------------------------------------
# pareto_chart tests
# ---------------------------------------------------------------------------

class TestParetoChart:
    def test_returns_figure(self, sample_df):
        fig = pareto_chart(sample_df)
        assert isinstance(fig, plt.Figure)

    def test_bar_count_equals_row_count(self, sample_df):
        fig = pareto_chart(sample_df)
        ax = fig.axes[0]
        bars = [p for p in ax.patches if hasattr(p, "get_width")]
        assert len(bars) == len(sample_df)

    def test_saves_png_to_disk(self, sample_df, tmp_path):
        out = tmp_path / "pareto.png"
        pareto_chart(sample_df, output_path=out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_raises_on_missing_rpn_column(self, sample_df):
        with pytest.raises(KeyError, match="RPN"):
            pareto_chart(sample_df.drop(columns=["RPN"]))

    def test_raises_on_missing_risk_tier_column(self, sample_df):
        with pytest.raises(KeyError, match="Risk_Tier"):
            pareto_chart(sample_df.drop(columns=["Risk_Tier"]))

    def test_raises_on_missing_failure_mode_column(self, sample_df):
        with pytest.raises(KeyError, match="Failure_Mode"):
            pareto_chart(sample_df.drop(columns=["Failure_Mode"]))

    def test_bars_descend_in_height(self, sample_df):
        """Pareto bars must be in descending RPN order."""
        fig = pareto_chart(sample_df)
        ax = fig.axes[0]
        heights = [p.get_height() for p in ax.patches if hasattr(p, "get_width")]
        assert heights == sorted(heights, reverse=True)

    def test_single_row_does_not_raise(self):
        """Edge case: one-row DataFrame should produce a valid chart."""
        data = {
            "ID": [1], "Process_Step": ["A"], "Component": ["X"],
            "Function": ["F"], "Failure_Mode": ["FM-1"], "Effect": ["E"],
            "Severity": [8], "Cause": ["C"], "Occurrence": [3],
            "Current_Control": ["Ctrl"], "Detection": [4],
        }
        df = run_pipeline(pd.DataFrame(data))
        fig = pareto_chart(df)
        assert isinstance(fig, plt.Figure)


# ---------------------------------------------------------------------------
# risk_heatmap tests
# ---------------------------------------------------------------------------

class TestRiskHeatmap:
    def test_returns_figure(self, sample_df):
        fig = risk_heatmap(sample_df)
        assert isinstance(fig, plt.Figure)

    def test_saves_png_to_disk(self, sample_df, tmp_path):
        out = tmp_path / "heatmap.png"
        risk_heatmap(sample_df, output_path=out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_raises_on_missing_severity_column(self, sample_df):
        with pytest.raises(KeyError, match="Severity"):
            risk_heatmap(sample_df.drop(columns=["Severity"]))

    def test_raises_on_missing_occurrence_column(self, sample_df):
        with pytest.raises(KeyError, match="Occurrence"):
            risk_heatmap(sample_df.drop(columns=["Occurrence"]))

    def test_raises_on_missing_risk_tier_column(self, sample_df):
        with pytest.raises(KeyError, match="Risk_Tier"):
            risk_heatmap(sample_df.drop(columns=["Risk_Tier"]))

    def test_axes_labels(self, sample_df):
        fig = risk_heatmap(sample_df)
        ax = fig.axes[0]
        assert "Occurrence" in ax.get_xlabel()
        assert "Severity" in ax.get_ylabel()

    def test_figure_has_title(self, sample_df):
        fig = risk_heatmap(sample_df)
        ax = fig.axes[0]
        assert "Heatmap" in ax.get_title() or "heatmap" in ax.get_title().lower()

    def test_all_red_tier_single_row(self):
        """A single high-severity row should produce a Red-tiered heatmap without error."""
        data = {
            "ID": [1], "Process_Step": ["A"], "Component": ["X"],
            "Function": ["F"], "Failure_Mode": ["FM-1"], "Effect": ["E"],
            "Severity": [9], "Cause": ["C"], "Occurrence": [5],
            "Current_Control": ["Ctrl"], "Detection": [5],
        }
        df = run_pipeline(pd.DataFrame(data))
        fig = risk_heatmap(df)
        assert isinstance(fig, plt.Figure)


def test_pareto_chart_caps_bars_at_topN_on_large_input(tmp_path):
    """F-038 regression: matplotlib pareto must not produce an unbounded-width
    figure on large datasets. At 1000 rows we expect at most TOP_N+1 bars
    (top-N individual + one 'Others' aggregate) and figsize width <= cap."""
    from fmea_app.rpn_engine import run_pipeline
    from fmea_app.visualizer import PARETO_FIGWIDTH_MAX, PARETO_TOP_N, pareto_chart

    n = 1000
    df = pd.DataFrame({
        "ID": range(1, n + 1),
        "Process_Step":    [f"Step_{i%20}" for i in range(n)],
        "Component":       [f"Comp_{i%50}" for i in range(n)],
        "Function":        [f"Function_{i%30}" for i in range(n)],
        "Failure_Mode":    [f"Failure_mode_{i}" for i in range(n)],
        "Effect":          [f"Effect_{i%40}" for i in range(n)],
        "Severity":        [(i % 10) + 1 for i in range(n)],
        "Cause":           [f"Cause_{i%60}" for i in range(n)],
        "Occurrence":      [((i * 7) % 10) + 1 for i in range(n)],
        "Current_Control": [f"Control_{i%25}" for i in range(n)],
        "Detection":       [((i * 3) % 10) + 1 for i in range(n)],
    })
    df = run_pipeline(df)

    fig = pareto_chart(df)
    ax = fig.axes[0]
    bars = [p for p in ax.patches]
    assert len(bars) <= PARETO_TOP_N + 1, (
        f"Expected <= {PARETO_TOP_N + 1} bars (top-N + Others), got {len(bars)}"
    )
    width, _ = fig.get_size_inches()
    assert width <= PARETO_FIGWIDTH_MAX, (
        f"figsize width {width} exceeds cap {PARETO_FIGWIDTH_MAX}"
    )


def test_visualizer_pareto_chart_handles_empty_df():
    """F-012 regression: pareto_chart must not crash on an empty DataFrame."""
    import matplotlib.pyplot as plt

    from fmea_app.visualizer import pareto_chart

    df = pd.DataFrame(columns=["Failure_Mode", "RPN", "Risk_Tier"])
    fig = pareto_chart(df)
    assert fig is not None
    plt.close(fig)
