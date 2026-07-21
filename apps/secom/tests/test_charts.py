"""Tests for secom_app/charts.py — SECOM signal -> SPC I-MR engine (W09-2, #66).

Drives control_chart_for_signal()/control_charts_for_selection() with small
synthetic frames (fast, deterministic) — never the 5 MB vendored file (mirrors
test_selection.py discipline). Covers:

- Happy-path I-MR (limits/sigma_hat match compute_imr, n_used, violations shape).
- Ruleset switch (Nelson >= WE; a Nelson-only rule appears under "nelson" only).
- Special-cause present (Rule 1 beyond +/-3 sigma) vs in-control (no violations).
- NaN preservation / order (n_used, dropna() order, no imputation).
- OQ5 gap-broken moving range: runs at start/end/middle gaps, consecutive NaNs,
  a run of length 1, and the empty-pooled-MR degenerate case.
- OQ2 autocorrelation flag: white-noise (false) vs strongly autocorrelated (true),
  plus the private helper's zero-variance guard.
- Errors: unknown signal, <2 present values, constant present series.
- Selection wiring: keep-only, drop skipped, empty audit -> {}.
- Red-line guard: no USL/LSL/Cp/Cpk keys anywhere in the result.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from secom_app.charts import (
    SignalControlChart,
    _lag1_autocorrelation,
    _pooled_moving_ranges,
    _present_runs,
    control_chart_for_signal,
    control_charts_for_selection,
)
from secom_app.selection import select_signals

from spc_app.spc_engine.control_charts import compute_imr

_IN_CONTROL = [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 10.0, 9.9, 10.1]
_WITH_SPIKE = [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 30.0, 10.0, 9.9, 10.1]


# --- Happy path -------------------------------------------------------------


def test_happy_path_matches_compute_imr_on_gap_free_series():
    df = pd.DataFrame({"s": _IN_CONTROL})

    result = control_chart_for_signal(df, "s")
    expected = compute_imr(_IN_CONTROL)

    assert result.signal == "s"
    assert result.n_used == len(_IN_CONTROL)
    assert result.imr["xbar"] == pytest.approx(expected["xbar"])
    assert result.imr["mrbar"] == pytest.approx(expected["mrbar"])
    assert result.imr["ucl_x"] == pytest.approx(expected["ucl_x"])
    assert result.imr["lcl_x"] == pytest.approx(expected["lcl_x"])
    assert result.imr["ucl_mr"] == pytest.approx(expected["ucl_mr"])
    assert result.imr["sigma_hat"] == pytest.approx(expected["sigma_hat"])
    assert result.violations == []
    for violation in result.violations:
        assert set(violation) == {"index", "rule"}


# --- Ruleset switch -----------------------------------------------------------


def test_ruleset_switch_nelson_only_rule_not_under_we():
    # Strictly alternating, small-amplitude series: trips Nelson 6/7 but no WE rule.
    values = [10.0]
    for i in range(20):
        values.append(values[-1] + (0.05 if i % 2 == 0 else -0.05))
    df = pd.DataFrame({"s": values})

    nelson = control_chart_for_signal(df, "s", ruleset="nelson")
    we = control_chart_for_signal(df, "s", ruleset="we")

    assert we.violations == []
    nelson_rules = {v["rule"] for v in nelson.violations}
    assert "Nelson Rule 6" in nelson_rules
    assert all(rule.startswith("Nelson") for rule in nelson_rules)


# --- Special-cause present vs in-control ------------------------------------


def test_special_cause_beyond_3_sigma_flags_rule_1():
    df = pd.DataFrame({"s": _WITH_SPIKE})

    result = control_chart_for_signal(df, "s")

    assert {"index": 8, "rule": "Western Electric Rule 1"} in result.violations


def test_in_control_series_yields_no_violations():
    df = pd.DataFrame({"s": _IN_CONTROL})

    result = control_chart_for_signal(df, "s")

    assert result.violations == []


# --- NaN preservation / order -----------------------------------------------


def test_nan_preservation_and_order_matches_dropna():
    values = [10.0, np.nan, 10.2, 9.8, np.nan, np.nan, 10.1, 9.9, 10.0]
    column = pd.Series(values)
    df = pd.DataFrame({"s": column})

    result = control_chart_for_signal(df, "s")

    expected_present = column.dropna().tolist()
    assert result.n_used == len(expected_present)
    assert result.imr["values"] == pytest.approx(expected_present)


# --- OQ5: gap-broken moving range -------------------------------------------


def test_present_runs_splits_at_start_middle_end_gaps_and_consecutive_nans():
    arr = np.array(
        [np.nan, np.nan, 1.0, 2.0, 3.0, np.nan, 5.0, np.nan, np.nan, 8.0, 9.0, np.nan]
    )

    runs = _present_runs(arr)

    assert [run.tolist() for run in runs] == [[1.0, 2.0, 3.0], [5.0], [8.0, 9.0]]


def test_present_runs_no_gaps_is_one_run():
    arr = np.array([1.0, 2.0, 3.0])

    runs = _present_runs(arr)

    assert len(runs) == 1
    assert runs[0].tolist() == [1.0, 2.0, 3.0]


def test_present_runs_all_nan_is_empty():
    arr = np.array([np.nan, np.nan])

    runs = _present_runs(arr)

    assert runs == []


def test_pooled_moving_ranges_run_of_length_one_contributes_nothing():
    runs = [np.array([1.0]), np.array([5.0, 7.0])]

    pooled = _pooled_moving_ranges(runs)

    assert pooled == pytest.approx([2.0])


def test_pooled_moving_ranges_all_singleton_runs_is_empty():
    runs = [np.array([1.0]), np.array([2.0]), np.array([3.0])]

    assert _pooled_moving_ranges(runs) == []


def test_moving_range_never_spans_a_gap_end_to_end():
    # A jump across the gap (3.0 -> 100.0) must not appear as a moving range;
    # only within-run diffs (1.0 and 1.0) may.
    values = [2.0, 3.0, np.nan, 100.0, 101.0]
    df = pd.DataFrame({"s": values})

    result = control_chart_for_signal(df, "s")

    assert result.imr["moving_ranges"] == pytest.approx([1.0, 1.0])
    assert 99.0 not in result.imr["moving_ranges"]


def test_all_singleton_runs_yields_zero_mrbar_and_raises_on_detection():
    # Every other value missing: every run has length 1, so pooled MR is empty
    # and sigma_hat collapses to 0 -> detect_* raises (mirrors the constant-
    # series degenerate case).
    values = [1.0, np.nan, 2.0, np.nan, 3.0, np.nan, 4.0]
    df = pd.DataFrame({"s": values})

    with pytest.raises(ValueError, match="sigma must be positive"):
        control_chart_for_signal(df, "s")


# --- Tester-added: OQ5 boundary matrix extras --------------------------------


def test_present_runs_run_of_length_two_at_the_very_end():
    arr = np.array([np.nan, np.nan, 1.0, 2.0, 3.0, np.nan, 7.0, 8.0])

    runs = _present_runs(arr)

    assert [run.tolist() for run in runs] == [[1.0, 2.0, 3.0], [7.0, 8.0]]


def test_control_chart_single_run_spans_whole_series_matches_compute_imr():
    # No gaps at all: OQ5 run-breaking must be a no-op vs a bare compute_imr call.
    df = pd.DataFrame({"s": _IN_CONTROL})

    result = control_chart_for_signal(df, "s")
    expected = compute_imr(_IN_CONTROL)

    assert result.imr["moving_ranges"] == pytest.approx(expected["moving_ranges"])
    assert len(result.imr["moving_ranges"]) == len(_IN_CONTROL) - 1


def test_pooled_limits_hand_computed_across_three_runs():
    # Independent hand computation (not reusing charts.py's own arithmetic):
    # runs [10,12] MR=[2], [20,24,28] MR=[4,4], [40,44] MR=[4].
    # pooled MR = [2,4,4,4] -> mrbar = 3.5; xbar = mean(10,12,20,24,28,40,44).
    values = [10.0, 12.0, np.nan, 20.0, 24.0, 28.0, np.nan, np.nan, 40.0, 44.0]
    df = pd.DataFrame({"s": values})

    result = control_chart_for_signal(df, "s")

    present = [10.0, 12.0, 20.0, 24.0, 28.0, 40.0, 44.0]
    expected_xbar = sum(present) / len(present)
    expected_mrbar = sum([2.0, 4.0, 4.0, 4.0]) / 4
    E2, D4, D2 = 2.660, 3.267, 1.128  # AIAG I-MR constants (independently re-quoted)

    assert result.imr["moving_ranges"] == pytest.approx([2.0, 4.0, 4.0, 4.0])
    assert result.imr["xbar"] == pytest.approx(expected_xbar)
    assert result.imr["mrbar"] == pytest.approx(expected_mrbar)
    assert result.imr["ucl_x"] == pytest.approx(expected_xbar + E2 * expected_mrbar)
    assert result.imr["lcl_x"] == pytest.approx(expected_xbar - E2 * expected_mrbar)
    assert result.imr["ucl_mr"] == pytest.approx(D4 * expected_mrbar)
    assert result.imr["lcl_mr"] == pytest.approx(0.0)
    assert result.imr["sigma_hat"] == pytest.approx(expected_mrbar / D2)


# --- OQ2: autocorrelation flag ----------------------------------------------


def test_autocorrelation_flag_false_for_white_noise():
    rng = np.random.default_rng(42)
    values = rng.normal(0, 1, 200).tolist()
    df = pd.DataFrame({"s": values})

    result = control_chart_for_signal(df, "s")

    assert result.autocorr_flag is False


def test_autocorrelation_flag_true_for_random_walk():
    rng = np.random.default_rng(7)
    values = np.cumsum(rng.normal(0, 1, 200)) + 50
    df = pd.DataFrame({"s": values.tolist()})

    result = control_chart_for_signal(df, "s")

    assert abs(result.lag1_autocorr) > 0.5
    assert result.autocorr_flag is True


def test_autocorrelation_flag_just_below_threshold_is_false():
    # n=50 -> threshold = 1.96/sqrt(50) ~= 0.27719. This series' lag-1
    # autocorrelation ~= 0.2505 (computed independently offline), just under
    # the bound -> flag must be False.
    values = [
        -3.93175737, -1.25695194, 5.52950291, 1.38604832, 4.47791783,
        3.31898757, -1.29994299, 3.58926008, 0.38153308, 0.56350326,
        2.43624009, -3.81057337, 7.19886026, -0.00258146, 6.84607094,
        3.61687647, 9.36983149, 0.86162158, 2.45061545, 5.23763228,
        -4.67469762, 7.59598773, 10.63798082, 9.194057, 7.92020934,
        4.54473787, 10.42556135, 9.80427172, 7.30066786, 5.96532939,
        4.71197668, 1.46482702, 11.43426144, -1.86887445, 5.4986643,
        7.82841078, 10.79802771, 14.58760342, 11.73846201, 6.83620233,
        11.09430704, 3.39013874, 14.29400564, 8.19301058, 6.34180738,
        6.6847361, 9.18608872, 8.07367993, 18.94239204, 7.19022994,
    ]
    df = pd.DataFrame({"s": values})
    threshold = 1.96 / math.sqrt(len(values))

    result = control_chart_for_signal(df, "s")

    assert abs(result.lag1_autocorr) < threshold
    assert result.autocorr_flag is False


def test_autocorrelation_flag_just_above_threshold_is_true():
    # Same construction, nudged slightly more autocorrelated: lag-1
    # autocorrelation ~= 0.2964 vs the same ~0.27719 bound -> flag True.
    values = [
        -3.85757327, -1.21436794, 5.46290852, 1.41650023, 4.46890051,
        3.35070479, -1.16220822, 3.65361366, 0.52527774, 0.72268245,
        2.57895254, -3.53112859, 7.28944781, 0.24275027, 6.98105074,
        3.83165238, 9.49492901, 1.16611929, 2.74400006, 5.49729959,
        -4.20913728, 7.84889362, 10.85235854, 9.45454649, 8.22360161,
        4.93068622, 10.71941869, 10.12871943, 7.69122129, 6.39994582,
        5.1891092, 2.02209444, 11.82229424, -1.21097116, 6.03642535,
        8.34108227, 11.27353662, 15.01047882, 12.23396273, 7.44306644,
        11.63969748, 4.09975876, 14.81676025, 8.84974623, 7.05233932,
        7.40766561, 9.88069082, 8.8081388, 19.49064879, 7.97909352,
    ]
    df = pd.DataFrame({"s": values})
    threshold = 1.96 / math.sqrt(len(values))

    result = control_chart_for_signal(df, "s")

    assert abs(result.lag1_autocorr) > threshold
    assert result.autocorr_flag is True


def test_lag1_autocorrelation_helper_zero_variance_guard():
    assert _lag1_autocorrelation([5.0, 5.0, 5.0]) == 0.0


def test_lag1_autocorrelation_helper_nonzero_case():
    value = _lag1_autocorrelation([1.0, 2.0, 1.0, 2.0, 1.0, 2.0])
    assert value == pytest.approx(-0.8333333333333334)


# --- Errors -------------------------------------------------------------------


def test_unknown_signal_raises_value_error():
    df = pd.DataFrame({"s": _IN_CONTROL})

    with pytest.raises(ValueError, match="not found in features"):
        control_chart_for_signal(df, "does_not_exist")


def test_fewer_than_two_present_values_raises_via_compute_imr():
    df = pd.DataFrame({"s": [1.0, np.nan, np.nan]})

    with pytest.raises(ValueError, match="at least two values"):
        control_chart_for_signal(df, "s")


def test_all_nan_column_raises_via_compute_imr():
    df = pd.DataFrame({"s": [np.nan, np.nan, np.nan]})

    with pytest.raises(ValueError, match="at least two values"):
        control_chart_for_signal(df, "s")


def test_constant_present_series_raises_sigma_error():
    df = pd.DataFrame({"s": [5.0] * 150})

    with pytest.raises(ValueError, match="sigma must be positive"):
        control_chart_for_signal(df, "s")


# --- Selection wiring -----------------------------------------------------------


def test_control_charts_for_selection_keeps_only_charts_kept_signals():
    rng = np.random.default_rng(0)
    features = pd.DataFrame(
        {
            "sensor_keep": rng.normal(10, 1, 150),
            "sensor_constant": [5.0] * 150,
            "sensor_too_missing": [1.0] * 10 + [np.nan] * 140,
        }
    )
    audit = select_signals(features)

    result = control_charts_for_selection(features, audit)

    assert set(result) == {"sensor_keep"}
    assert isinstance(result["sensor_keep"], SignalControlChart)


def test_control_charts_for_selection_adversarial_mixed_statuses():
    # Mix all four selection outcomes in one frame: too_missing, constant,
    # near_zero_variance, and two keep signals -> only the keep signals chart.
    rng = np.random.default_rng(1)
    nzv_column = [5.0] * 143 + [5.01, 5.02, 5.03, 5.04, 5.05, 5.06, 5.07]
    features = pd.DataFrame(
        {
            "sensor_keep_a": rng.normal(10, 1, 150),
            "sensor_keep_b": rng.normal(0, 5, 150),
            "sensor_constant": [3.0] * 150,
            "sensor_too_missing": [1.0] * 10 + [np.nan] * 140,
            "sensor_near_zero_var": nzv_column,
        }
    )
    audit = select_signals(features)
    assert set(audit.loc[audit["status"] == "drop", "reason"]) == {
        "too_missing",
        "constant",
        "near_zero_variance",
    }

    result = control_charts_for_selection(features, audit)

    assert set(result) == {"sensor_keep_a", "sensor_keep_b"}


def test_control_charts_for_selection_empty_audit_returns_empty_dict():
    features = pd.DataFrame({"s": _IN_CONTROL})
    audit = pd.DataFrame(columns=["signal", "status"])

    assert control_charts_for_selection(features, audit) == {}


def test_control_charts_for_selection_respects_ruleset():
    rng = np.random.default_rng(0)
    features = pd.DataFrame({"sensor_keep": rng.normal(10, 1, 150)})
    audit = select_signals(features)

    result = control_charts_for_selection(features, audit, ruleset="we")

    assert result["sensor_keep"].violations == control_chart_for_signal(
        features, "sensor_keep", ruleset="we"
    ).violations


# --- Red-line guard: no USL/LSL/Cp/Cpk surface -------------------------------


def test_no_capability_keys_reachable_from_result():
    df = pd.DataFrame({"s": _IN_CONTROL})
    result = control_chart_for_signal(df, "s")

    forbidden = {"usl", "lsl", "cp", "cpk", "pp", "ppk"}
    imr_keys = {key.lower() for key in result.imr}
    field_names = {field.lower() for field in result.__dataclass_fields__}

    assert forbidden.isdisjoint(imr_keys)
    assert forbidden.isdisjoint(field_names)
