"""Tests for the Control Charts page wiring (c-chart UI path)."""

from spc_app.pages.control_charts import CHART_OPTIONS, summarize_metrics
from spc_app.spc_engine.control_charts import compute_c

C_COUNTS = [4, 7, 5, 6]


def test_c_chart_is_a_selectable_option():
    assert "c" in CHART_OPTIONS
    assert CHART_OPTIONS["c"] == {"stream": "panel_defects", "compute": "c"}


def test_summarize_metrics_c_branch():
    result = compute_c(C_COUNTS)
    metrics = summarize_metrics("c", result)
    labels = [label for label, _ in metrics]
    assert labels == ["cbar", "UCL", "Points"]

    values = dict(metrics)
    assert values["cbar"] == f"{result['cbar']:.4f}"
    assert values["UCL"] == f"{result['ucl']:.4f}"
    assert values["Points"] == str(len(C_COUNTS))


def test_summarize_metrics_c_distinct_from_u_fallback():
    # "c" must not fall through to the u-chart fallback branch.
    result = compute_c(C_COUNTS)
    labels = [label for label, _ in summarize_metrics("c", result)]
    assert "ubar" not in labels
