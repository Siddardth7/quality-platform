"""Tests for secom_app/capability.py — SECOM Cp/Cpk on caller-supplied limits (W09-3, #67).

Drives capability_for_signal() with small synthetic frames (fast, deterministic) —
never the 5 MB vendored file (mirrors test_charts.py discipline). Covers:

- Reference-accuracy scorecard: hand-computed Cp/Cpk/Pp/Ppk (AIAG formula, independent
  arithmetic) against a known series + limits.
- Faithful-reuse: result.capability equals a direct compute_capability(...) call fed
  the same chart.imr values/sigma_hat (proves no re-derived math in capability.py).
- Stability gate: unstable (_WITH_SPIKE) -> stable=False + stability_warning set, indices
  still populated; in-control (_IN_CONTROL) -> stable=True + stability_warning is None.
- Ruleset switch reaching a different `stable` value on the same series.
- One-sided limits (lsl only / usl only) -> cp/pp None, cpk/ppk finite.
- Both-None and lsl>=usl (equal and inverted) -> ValueError.
- Propagated errors: unknown signal, <2 present values, constant series.
- NaN/gap series: capability computed on the dropna'd present values only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from secom_app.capability import SignalCapability, capability_for_signal
from secom_app.charts import control_chart_for_signal

from spc_app.spc_engine.capability import compute_capability

_IN_CONTROL = [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 10.0, 9.9, 10.1]
_WITH_SPIKE = [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 30.0, 10.0, 9.9, 10.1]


# --- Reference-accuracy scorecard (independent hand computation) ------------


def test_reference_accuracy_hand_computed_two_sided():
    # Independent arithmetic, not reusing capability.py's own computation path:
    # runs [10,12] MR=[2], [20,24,28] MR=[4,4] -> pooled MR=[2,4,4] -> mrbar=10/3.
    values = [10.0, 12.0, np.nan, 20.0, 24.0, 28.0]
    df = pd.DataFrame({"s": values})
    lsl, usl = 0.0, 40.0

    result = capability_for_signal(df, "s", lsl=lsl, usl=usl)

    present = [10.0, 12.0, 20.0, 24.0, 28.0]
    mean = sum(present) / len(present)
    mrbar = (2.0 + 4.0 + 4.0) / 3.0
    D2 = 1.128  # AIAG I-MR d2 constant, independently re-quoted (test_charts.py:219 pattern)
    sigma_hat = mrbar / D2
    sigma_overall = float(np.std(present, ddof=1))

    expected_cp = (usl - lsl) / (6.0 * sigma_hat)
    expected_cpk = min((usl - mean) / (3.0 * sigma_hat), (mean - lsl) / (3.0 * sigma_hat))
    expected_pp = (usl - lsl) / (6.0 * sigma_overall)
    expected_ppk = min(
        (usl - mean) / (3.0 * sigma_overall), (mean - lsl) / (3.0 * sigma_overall)
    )

    assert result.capability["mean"] == pytest.approx(mean)
    assert result.capability["sigma_hat"] == pytest.approx(sigma_hat)
    assert result.capability["sigma_overall"] == pytest.approx(sigma_overall)
    assert result.capability["cp"] == pytest.approx(expected_cp)
    assert result.capability["cpk"] == pytest.approx(expected_cpk)
    assert result.capability["pp"] == pytest.approx(expected_pp)
    assert result.capability["ppk"] == pytest.approx(expected_ppk)


# --- Faithful reuse: no re-derived math --------------------------------------


def test_faithful_reuse_matches_direct_compute_capability_call():
    df = pd.DataFrame({"s": _IN_CONTROL})
    lsl, usl = 9.0, 11.0

    result = capability_for_signal(df, "s", lsl=lsl, usl=usl)

    chart = control_chart_for_signal(df, "s")
    expected = compute_capability(
        chart.imr["values"], lsl=lsl, usl=usl, sigma_hat=chart.imr["sigma_hat"]
    )

    assert result.capability == expected


# --- Stability gate -----------------------------------------------------------


def test_unstable_series_stable_false_warning_set_indices_still_present():
    df = pd.DataFrame({"s": _WITH_SPIKE})

    result = capability_for_signal(df, "s", lsl=0.0, usl=40.0)

    assert result.stable is False
    assert result.stability_warning is not None
    assert "not in statistical control" in result.stability_warning
    assert result.capability["cp"] is not None
    assert result.capability["cpk"] is not None


def test_in_control_series_stable_true_warning_none():
    df = pd.DataFrame({"s": _IN_CONTROL})

    result = capability_for_signal(df, "s", lsl=9.0, usl=11.0)

    assert result.stable is True
    assert result.stability_warning is None


def test_ruleset_switch_reaches_different_stable_value():
    # Same alternating small-amplitude series as test_charts.py's ruleset-switch
    # test: trips Nelson 6/7 but no WE rule -> stable differs by ruleset.
    values = [10.0]
    for i in range(20):
        values.append(values[-1] + (0.05 if i % 2 == 0 else -0.05))
    df = pd.DataFrame({"s": values})

    nelson = capability_for_signal(df, "s", lsl=9.0, usl=11.0, ruleset="nelson")
    we = capability_for_signal(df, "s", lsl=9.0, usl=11.0, ruleset="we")

    assert nelson.stable is False
    assert we.stable is True


# --- One-sided limits ---------------------------------------------------------


def test_lsl_only_cp_pp_none_cpk_ppk_finite():
    df = pd.DataFrame({"s": _IN_CONTROL})

    result = capability_for_signal(df, "s", lsl=9.0, usl=None)

    assert result.lsl == 9.0
    assert result.usl is None
    assert result.capability["cp"] is None
    assert result.capability["pp"] is None
    assert isinstance(result.capability["cpk"], float)
    assert isinstance(result.capability["ppk"], float)


def test_usl_only_cp_pp_none_cpk_ppk_finite():
    df = pd.DataFrame({"s": _IN_CONTROL})

    result = capability_for_signal(df, "s", lsl=None, usl=11.0)

    assert result.usl == 11.0
    assert result.lsl is None
    assert result.capability["cp"] is None
    assert result.capability["pp"] is None
    assert isinstance(result.capability["cpk"], float)
    assert isinstance(result.capability["ppk"], float)


# --- Limit validation errors ---------------------------------------------------


def test_both_limits_none_raises_value_error():
    df = pd.DataFrame({"s": _IN_CONTROL})

    with pytest.raises(ValueError, match="At least one of lsl/usl"):
        capability_for_signal(df, "s", lsl=None, usl=None)


def test_lsl_equal_usl_raises_value_error():
    df = pd.DataFrame({"s": _IN_CONTROL})

    with pytest.raises(ValueError, match="must be less than"):
        capability_for_signal(df, "s", lsl=10.0, usl=10.0)


def test_lsl_greater_than_usl_raises_value_error():
    df = pd.DataFrame({"s": _IN_CONTROL})

    with pytest.raises(ValueError, match="must be less than"):
        capability_for_signal(df, "s", lsl=12.0, usl=8.0)


# --- Propagated errors from control_chart_for_signal ---------------------------


def test_unknown_signal_propagates_unchanged():
    df = pd.DataFrame({"s": _IN_CONTROL})

    with pytest.raises(ValueError, match="not found in features"):
        capability_for_signal(df, "does_not_exist", lsl=9.0, usl=11.0)


def test_fewer_than_two_present_values_propagates_unchanged():
    df = pd.DataFrame({"s": [1.0, np.nan, np.nan]})

    with pytest.raises(ValueError, match="at least two values"):
        capability_for_signal(df, "s", lsl=0.0, usl=2.0)


def test_constant_series_propagates_sigma_error_unchanged():
    df = pd.DataFrame({"s": [5.0] * 150})

    with pytest.raises(ValueError, match="sigma must be positive"):
        capability_for_signal(df, "s", lsl=0.0, usl=10.0)


# --- NaN/gap series: capability on dropna'd present values only ---------------


def test_nan_gap_series_capability_matches_present_values_only():
    values = [10.0, np.nan, 10.2, 9.8, np.nan, np.nan, 10.1, 9.9, 10.0]
    column = pd.Series(values)
    df = pd.DataFrame({"s": column})

    result = capability_for_signal(df, "s", lsl=9.0, usl=11.0)

    present = column.dropna().tolist()
    assert result.capability["mean"] == pytest.approx(sum(present) / len(present))
    assert result.chart.n_used == len(present)


# --- Result shape / dataclass fields ------------------------------------------


def test_result_is_signal_capability_with_expected_fields():
    df = pd.DataFrame({"s": _IN_CONTROL})

    result = capability_for_signal(df, "s", lsl=9.0, usl=11.0)

    assert isinstance(result, SignalCapability)
    assert result.signal == "s"
