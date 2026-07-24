"""Tests for secom_app/selection.py — signal-selection audit screen (W09-1).

Drives select_signals() and its private helpers with:
- Boundary tests for MIN_NON_MISSING (100 non-missing kept, 99 dropped).
- NZV boundary tests (freq_ratio == 19 / percent_unique == 0.10, both sides,
  and each condition alone).
- Zero-variance (constant / all-NaN) dropped unconditionally.
- Reason precedence: the first failing rule wins.
- Audit-table shape/columns/domains and custom SelectionCriteria honoring.
- _freq_ratio / _percent_unique edge cases (0 or 1 distinct present values).

Uses small synthetic frames throughout (fast, deterministic) — never the 5 MB
vendored file.
"""

from __future__ import annotations

import pandas as pd
import pytest
from secom_app.selection import (
    MIN_NON_MISSING,
    NZV_FREQ_RATIO,
    NZV_PERCENT_UNIQUE,
    SelectionCriteria,
    _freq_ratio,
    _percent_unique,
    select_signals,
)

_AUDIT_COLUMNS = [
    "signal",
    "n_present",
    "missing_frac",
    "n_distinct",
    "variance",
    "freq_ratio",
    "percent_unique",
    "status",
    "reason",
]


def _row(df: pd.DataFrame, signal: str) -> pd.Series:
    matches = df[df["signal"] == signal]
    assert len(matches) == 1, f"expected exactly one row for {signal!r}"
    return matches.iloc[0]


# --- Constants sanity (SME-locked values) --------------------------------------


def test_constants_match_sme_resolution():
    assert MIN_NON_MISSING == 100
    assert NZV_FREQ_RATIO == 19.0
    assert NZV_PERCENT_UNIQUE == 0.10
    assert SelectionCriteria() == SelectionCriteria(
        min_non_missing=100, nzv_freq_ratio=19.0, nzv_percent_unique=0.10
    )


# --- MIN_NON_MISSING boundary --------------------------------------------------


def test_min_non_missing_boundary_100_kept_99_dropped():
    n_rows = 150
    # sensor_100: exactly 100 present (varied values, no NZV) -> keep.
    col_100 = [float(i) for i in range(100)] + [None] * 50
    # sensor_99: exactly 99 present -> drop, too_missing.
    col_99 = [float(i) for i in range(99)] + [None] * 51
    features = pd.DataFrame({"sensor_100": col_100, "sensor_99": col_99})
    assert len(features) == n_rows

    report = select_signals(features)

    r100 = _row(report, "sensor_100")
    assert r100["n_present"] == 100
    assert r100["status"] == "keep"
    assert r100["reason"] == "ok"

    r99 = _row(report, "sensor_99")
    assert r99["n_present"] == 99
    assert r99["status"] == "drop"
    assert r99["reason"] == "too_missing"


# --- NZV boundary ---------------------------------------------------------------


def test_nzv_both_conditions_at_exact_boundary_dropped():
    """freq_ratio == 19.0 AND percent_unique == 0.10 exactly -> drop."""
    present = [0.0] * 19 + [1.0]  # 20 values, 2 distinct: counts 19 / 1.
    features = pd.DataFrame({"sensor_000": present})
    criteria = SelectionCriteria(min_non_missing=2)

    report = select_signals(features, criteria)

    row = _row(report, "sensor_000")
    assert row["freq_ratio"] == pytest.approx(19.0)
    assert row["percent_unique"] == pytest.approx(0.10)
    assert row["status"] == "drop"
    assert row["reason"] == "near_zero_variance"


def test_nzv_freq_ratio_below_threshold_kept_even_at_percent_unique_boundary():
    """percent_unique == 0.10 but freq_ratio < 19 -> AND fails -> keep."""
    present = [0.0] * 17 + [1.0] * 3  # 20 values, 2 distinct: counts 17 / 3.
    features = pd.DataFrame({"sensor_000": present})
    criteria = SelectionCriteria(min_non_missing=2)

    report = select_signals(features, criteria)

    row = _row(report, "sensor_000")
    assert row["freq_ratio"] == pytest.approx(17 / 3)
    assert row["freq_ratio"] < NZV_FREQ_RATIO
    assert row["percent_unique"] == pytest.approx(0.10)
    assert row["status"] == "keep"
    assert row["reason"] == "ok"


def test_nzv_percent_unique_above_threshold_kept_even_at_freq_ratio_boundary():
    """freq_ratio well over 19 but percent_unique > 0.10 -> AND fails -> keep."""
    common = [0.0] * 950
    singletons = [float(i) for i in range(1, 106)]  # 105 distinct singleton values
    present = common + singletons  # n_present=1055, n_distinct=106
    features = pd.DataFrame({"sensor_000": present})
    criteria = SelectionCriteria(min_non_missing=2)

    report = select_signals(features, criteria)

    row = _row(report, "sensor_000")
    assert row["freq_ratio"] >= NZV_FREQ_RATIO
    assert row["percent_unique"] > NZV_PERCENT_UNIQUE
    assert row["status"] == "keep"
    assert row["reason"] == "ok"


def test_nzv_dropped_when_well_past_both_thresholds():
    present = [0.0] * 195 + [1.0] * 5  # 200 values, 2 distinct: ratio=39, unique=0.01
    features = pd.DataFrame({"sensor_000": present})
    criteria = SelectionCriteria(min_non_missing=2)

    report = select_signals(features, criteria)

    row = _row(report, "sensor_000")
    assert row["status"] == "drop"
    assert row["reason"] == "near_zero_variance"


def test_custom_criteria_are_honored():
    """A signal that would fail default NZV thresholds passes stricter ones."""
    present = [0.0] * 15 + [1.0] * 5  # ratio=3.0, percent_unique=0.10
    features = pd.DataFrame({"sensor_000": present})

    lenient = SelectionCriteria(
        min_non_missing=2, nzv_freq_ratio=2.0, nzv_percent_unique=0.20
    )
    report = select_signals(features, lenient)

    row = _row(report, "sensor_000")
    assert row["status"] == "drop"
    assert row["reason"] == "near_zero_variance"


# --- Zero-variance (constant) dropped unconditionally --------------------------


def test_constant_column_dropped_even_with_lenient_criteria():
    """sigma=0 is definitional — dropped regardless of NZV/missingness leniency."""
    present = [5.0] * 150  # single distinct value, well past MIN_NON_MISSING
    features = pd.DataFrame({"sensor_000": present})
    # Deliberately lenient enough that NZV/missingness would never fire on their own.
    lenient = SelectionCriteria(
        min_non_missing=1, nzv_freq_ratio=10_000.0, nzv_percent_unique=0.0
    )

    report = select_signals(features, lenient)

    row = _row(report, "sensor_000")
    assert row["variance"] == 0.0
    assert row["status"] == "drop"
    assert row["reason"] == "constant"


def test_all_nan_column_dropped_as_constant_with_lenient_missingness_floor():
    features = pd.DataFrame({"sensor_000": [None, None, None]})
    lenient = SelectionCriteria(min_non_missing=0)

    report = select_signals(features, lenient)

    row = _row(report, "sensor_000")
    assert row["n_present"] == 0
    assert row["variance"] == 0.0
    assert row["status"] == "drop"
    assert row["reason"] == "constant"


def test_single_present_value_column_variance_zero_branch():
    """n_present == 1: variance short-circuits to 0.0 without calling .var()."""
    features = pd.DataFrame({"sensor_000": [7.0] + [None] * 9})
    lenient = SelectionCriteria(min_non_missing=1)

    report = select_signals(features, lenient)

    row = _row(report, "sensor_000")
    assert row["n_present"] == 1
    assert row["variance"] == 0.0
    assert row["status"] == "drop"
    assert row["reason"] == "constant"


# --- Reason precedence -----------------------------------------------------------


def test_reason_precedence_too_missing_beats_constant():
    """A column that is both too-missing AND constant reports too_missing first."""
    present = [5.0] * 40  # all-equal, well under the default 100-floor.
    features = pd.DataFrame({"sensor_000": present + [None] * 10})

    report = select_signals(features)  # default criteria: min_non_missing=100

    row = _row(report, "sensor_000")
    assert row["n_present"] == 40
    assert row["variance"] == 0.0  # would also be "constant" if rule 1 didn't fire
    assert row["status"] == "drop"
    assert row["reason"] == "too_missing"


# --- Clean varied column --------------------------------------------------------


def test_clean_varied_column_kept_ok():
    present = [float(i) for i in range(150)]
    features = pd.DataFrame({"sensor_000": present})

    report = select_signals(features)

    row = _row(report, "sensor_000")
    assert row["status"] == "keep"
    assert row["reason"] == "ok"


# --- Audit table shape/columns/domains ------------------------------------------


def test_audit_table_shape_and_columns():
    features = pd.DataFrame(
        {
            "sensor_a": [float(i) for i in range(150)],
            "sensor_b": [5.0] * 150,
            "sensor_c": [None] * 150,
        }
    )

    report = select_signals(features)

    assert list(report.columns) == _AUDIT_COLUMNS
    assert len(report) == features.shape[1]
    assert set(report["status"]) <= {"keep", "drop"}
    assert set(report["reason"]) <= {"too_missing", "constant", "near_zero_variance", "ok"}


def test_zero_row_features_hits_missing_frac_zero_branch():
    """n_rows == 0: missing_frac short-circuits to 0.0 (the `if n_rows else` guard)."""
    features = pd.DataFrame({"sensor_000": pd.Series([], dtype=float)})

    report = select_signals(features)

    row = _row(report, "sensor_000")
    assert row["n_present"] == 0
    assert row["missing_frac"] == 0.0
    assert row["status"] == "drop"
    assert row["reason"] == "too_missing"


# --- _freq_ratio / _percent_unique edge cases (module-private helpers) ---------


def test_freq_ratio_empty_series_is_inf():
    assert _freq_ratio(pd.Series([], dtype=float)) == float("inf")


def test_freq_ratio_single_distinct_value_is_inf():
    assert _freq_ratio(pd.Series([5.0, 5.0, 5.0])) == float("inf")


def test_freq_ratio_two_distinct_values_computed():
    assert _freq_ratio(pd.Series([5.0, 5.0, 3.0])) == pytest.approx(2.0)


def test_percent_unique_empty_series_is_zero():
    assert _percent_unique(pd.Series([], dtype=float)) == 0.0


def test_percent_unique_all_same_value():
    assert _percent_unique(pd.Series([5.0, 5.0, 5.0])) == pytest.approx(1 / 3)


def test_percent_unique_all_distinct_values():
    assert _percent_unique(pd.Series([1.0, 2.0, 3.0])) == pytest.approx(1.0)
