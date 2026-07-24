"""Tests for secom_app/doe_screening.py — observational DOE screening analysis (W11-1, #72).

Drives `screen_signals()`. Covers:

- Golden numbers on the real vendored SECOM data (labeled reference, DoD gate 3):
  n_candidates=463, n_significant=23, top-ranked signal sensor_059 with
  effect/p_value/q_value independently recomputed with raw numpy/scipy (NOT the
  module's own helpers, mirrors `test_yield_dppm.py:57-59`).
- A tiny hand-built 12-row fixture (6 pass rows, 6 fail rows) with 6 synthetic
  signals covering: a plain positive-effect signal, a reverse (negative-effect)
  signal, a signal below `MIN_GROUP_N` on the pass side, one below it on the
  fail side, a within-both-groups-constant (pooled SD = 0) signal, and a signal
  with interior NaNs proving present-values-only/never-imputed per group. Each
  signal's effect/p/q is checked against an independent 3-line scipy/numpy
  computation, not the module's own arithmetic.
- Ranking (|effect| desc, tie -> signal asc, NaN-effect rows sort last).
- FDR-excludes-NaN: the Benjamini-Hochberg input only sees defined p-values.
- The `q_value == alpha` exact-boundary case -> `significant` is `False` (strict `<`).
- `q_value >= p_value` (BH only inflates) and `significant == (q_value < alpha)`
  hold across the whole real-data table.
- Degenerate branches: no "keep" rows in a non-empty audit, and a completely
  empty audit frame -> both return the empty typed table.
- Method-fidelity: `scipy.stats.ttest_ind` and `false_discovery_control` are
  actually invoked (spied), not re-derived by hand.
- Honesty guard: module docstring names this observational/association, NOT a
  designed experiment, NOT causal.
- Integration: `select_signals()` -> `screen_signals()` wiring on real data.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from scipy import stats
from secom_app.doe_screening import (
    ALPHA,
    MIN_GROUP_N,
    SCREEN_COLUMNS,
    ScreeningResult,
    screen_signals,
)
from secom_app.ingest import FAIL, PASS, SecomDataset, load_secom
from secom_app.selection import select_signals

pytestmark = pytest.mark.filterwarnings("ignore::RuntimeWarning")


# --- Golden numbers on real data (DoD gate 3 scorecard) ----------------------


def test_screen_signals_golden_numbers_on_real_secom_data():
    dataset = load_secom()
    audit = select_signals(dataset.features)

    result = screen_signals(dataset, audit)

    assert result.n_candidates == 463
    assert result.n_significant == 23
    assert result.alpha == ALPHA
    assert result.method == "welch_t + cohens_d, BH-FDR"
    assert list(result.table.columns) == SCREEN_COLUMNS

    top = result.table.iloc[0]
    assert top["signal"] == "sensor_059"
    assert top["n_pass"] == 1456
    assert top["n_fail"] == 104
    assert top["mean_pass"] == pytest.approx(2.563464, abs=1e-4)
    assert top["mean_fail"] == pytest.approx(8.515123, abs=1e-4)
    assert top["effect"] == pytest.approx(0.6318883617175256)
    assert top["p_value"] == pytest.approx(2.627137969494079e-07)
    assert top["q_value"] == pytest.approx(6.061e-05, rel=1e-2)
    assert bool(top["significant"]) is True

    # Independent recomputation: raw numpy/scipy on sensor_059's present values,
    # split by label, NOT calling screen_signals's own helpers.
    pass_v = dataset.features.loc[dataset.labels == PASS, "sensor_059"].dropna()
    fail_v = dataset.features.loc[dataset.labels == FAIL, "sensor_059"].dropna()
    n_pass, n_fail = len(pass_v), len(fail_v)
    pooled = np.sqrt(
        ((n_pass - 1) * pass_v.var(ddof=1) + (n_fail - 1) * fail_v.var(ddof=1))
        / (n_pass + n_fail - 2)
    )
    independent_effect = (fail_v.mean() - pass_v.mean()) / pooled
    independent_p = stats.ttest_ind(fail_v, pass_v, equal_var=False).pvalue

    assert independent_effect == pytest.approx(0.6318883617175256)
    assert independent_p == pytest.approx(2.627137969494079e-07)
    assert top["effect"] == pytest.approx(independent_effect)
    assert top["p_value"] == pytest.approx(independent_p)


def test_q_value_always_gte_p_value_and_significant_matches_boundary_on_real_data():
    dataset = load_secom()
    audit = select_signals(dataset.features)

    result = screen_signals(dataset, audit)
    defined = result.table.dropna(subset=["p_value", "q_value"])

    assert len(defined) > 0
    assert (defined["q_value"] >= defined["p_value"] - 1e-12).all()
    assert (defined["significant"] == (defined["q_value"] < ALPHA)).all()


def test_integration_select_signals_feeds_screen_signals_on_real_data():
    dataset = load_secom()
    audit = select_signals(dataset.features)
    n_kept = int((audit["status"] == "keep").sum())

    result = screen_signals(dataset, audit)

    assert result.n_candidates == n_kept


# --- Tiny hand-built fixture ---------------------------------------------------
#
# 12 rows: rows 0-5 PASS, rows 6-11 FAIL. Six synthetic signals:
#   s_normal        -- plain positive effect (FAIL mean > PASS mean).
#   s_reverse       -- plain negative effect (FAIL mean < PASS mean).
#   s_low_n_pass    -- only 1 present value on the PASS side (< MIN_GROUP_N).
#   s_low_n_fail    -- only 1 present value on the FAIL side (< MIN_GROUP_N).
#   s_zero_pooled   -- constant within each group (pooled SD = 0).
#   s_nan_present   -- interior NaNs on both sides; present-values-only check.


def _build_tiny_fixture() -> tuple[SecomDataset, pd.DataFrame]:
    nan = float("nan")
    features = pd.DataFrame(
        {
            "s_normal": [1.0, 2.0, 3.0, nan, nan, nan, 5.0, 6.0, 7.0, nan, nan, nan],
            "s_reverse": [10.0, 11.0, 12.0, nan, nan, nan, 1.0, 2.0, 3.0, nan, nan, nan],
            "s_low_n_pass": [5.0, nan, nan, nan, nan, nan, 10.0, 11.0, 12.0, nan, nan, nan],
            "s_low_n_fail": [1.0, 2.0, 3.0, nan, nan, nan, 9.0, nan, nan, nan, nan, nan],
            "s_zero_pooled": [5.0, 5.0, 5.0, nan, nan, nan, 7.0, 7.0, 7.0, nan, nan, nan],
            "s_nan_present": [1.0, nan, 3.0, 5.0, nan, 7.0, 20.0, nan, 22.0, nan, 24.0, 26.0],
        }
    )
    labels = pd.Series([PASS] * 6 + [FAIL] * 6)
    timestamps = pd.Series(pd.to_datetime(["2020-01-01"] * 12))
    dataset = SecomDataset(features=features, labels=labels, timestamps=timestamps)
    audit = pd.DataFrame({"signal": features.columns, "status": "keep"})
    return dataset, audit


def _independent_cohens_d_and_welch_p(
    pass_v: pd.Series, fail_v: pd.Series
) -> tuple[float, float]:
    n_pass, n_fail = len(pass_v), len(fail_v)
    pooled = np.sqrt(
        ((n_pass - 1) * pass_v.var(ddof=1) + (n_fail - 1) * fail_v.var(ddof=1))
        / (n_pass + n_fail - 2)
    )
    effect = float((fail_v.mean() - pass_v.mean()) / pooled)
    p_value = float(stats.ttest_ind(fail_v, pass_v, equal_var=False).pvalue)
    return effect, p_value


def test_tiny_fixture_positive_and_negative_effect_direction_match_independent_scipy():
    dataset, audit = _build_tiny_fixture()

    result = screen_signals(dataset, audit)
    table = result.table.set_index("signal")

    expected_normal = _independent_cohens_d_and_welch_p(
        pd.Series([1.0, 2.0, 3.0]), pd.Series([5.0, 6.0, 7.0])
    )
    expected_reverse = _independent_cohens_d_and_welch_p(
        pd.Series([10.0, 11.0, 12.0]), pd.Series([1.0, 2.0, 3.0])
    )

    assert table.loc["s_normal", "effect"] == pytest.approx(expected_normal[0])
    assert table.loc["s_normal", "p_value"] == pytest.approx(expected_normal[1])
    assert table.loc["s_normal", "effect"] > 0  # FAIL mean > PASS mean

    assert table.loc["s_reverse", "effect"] == pytest.approx(expected_reverse[0])
    assert table.loc["s_reverse", "p_value"] == pytest.approx(expected_reverse[1])
    assert table.loc["s_reverse", "effect"] < 0  # FAIL mean < PASS mean


def test_tiny_fixture_present_values_only_never_imputed():
    dataset, audit = _build_tiny_fixture()

    result = screen_signals(dataset, audit)
    row = result.table.set_index("signal").loc["s_nan_present"]

    # Only the non-NaN present values participate, per group, independently.
    expected_pass = pd.Series([1.0, 3.0, 5.0, 7.0])
    expected_fail = pd.Series([20.0, 22.0, 24.0, 26.0])
    expected_effect, expected_p = _independent_cohens_d_and_welch_p(expected_pass, expected_fail)

    assert row["n_pass"] == 4
    assert row["n_fail"] == 4
    assert row["mean_pass"] == pytest.approx(expected_pass.mean())
    assert row["mean_fail"] == pytest.approx(expected_fail.mean())
    assert row["effect"] == pytest.approx(expected_effect)
    assert row["p_value"] == pytest.approx(expected_p)


def test_tiny_fixture_below_min_group_n_on_either_side_gives_nan_and_excludes_from_fdr():
    dataset, audit = _build_tiny_fixture()

    result = screen_signals(dataset, audit)
    table = result.table.set_index("signal")

    for signal in ("s_low_n_pass", "s_low_n_fail"):
        row = table.loc[signal]
        assert pd.isna(row["effect"])
        assert pd.isna(row["p_value"])
        assert pd.isna(row["q_value"])
        assert bool(row["significant"]) is False

    assert table.loc["s_low_n_pass", "n_pass"] < MIN_GROUP_N
    assert table.loc["s_low_n_fail", "n_fail"] < MIN_GROUP_N

    # FDR ran only over the defined p-values: s_normal is alone with s_reverse
    # and s_nan_present as the only fully-defined signals (s_zero_pooled is NaN
    # too) -- its q-value must equal the BH-adjustment computed over exactly
    # that defined subset, not diluted by the excluded rows.
    defined_p = result.table.dropna(subset=["p_value"])["p_value"].to_numpy()
    expected_q = stats.false_discovery_control(defined_p, method="bh")
    actual_q = result.table.dropna(subset=["p_value"])["q_value"].to_numpy()
    # order-independent check: same multiset of q-values, computed over exactly
    # the defined p-values (not diluted by the below-MIN_GROUP_N/NaN rows).
    assert sorted(actual_q) == pytest.approx(sorted(expected_q))


def test_tiny_fixture_zero_pooled_sd_within_group_constant_gives_nan_not_crash():
    dataset, audit = _build_tiny_fixture()

    result = screen_signals(dataset, audit)
    row = result.table.set_index("signal").loc["s_zero_pooled"]

    assert row["n_pass"] == 3
    assert row["n_fail"] == 3
    assert pd.isna(row["effect"])
    assert pd.isna(row["p_value"])
    assert pd.isna(row["q_value"])
    assert bool(row["significant"]) is False


def test_tiny_fixture_ranking_abs_effect_desc_tiebreak_signal_asc_nan_last():
    dataset, audit = _build_tiny_fixture()

    result = screen_signals(dataset, audit)
    signals_in_order = result.table["signal"].tolist()

    # Defined-effect signals rank first, by |effect| descending.
    defined_order = [s for s in signals_in_order if s in ("s_normal", "s_reverse", "s_nan_present")]
    abs_effects = (
        result.table.set_index("signal").loc[defined_order, "effect"].abs().tolist()
    )
    assert abs_effects == sorted(abs_effects, reverse=True)

    # NaN-effect rows sort last, tie-broken by signal name ascending.
    nan_tail = signals_in_order[-3:]
    assert nan_tail == ["s_low_n_fail", "s_low_n_pass", "s_zero_pooled"]


def test_tiny_fixture_custom_alpha_changes_significant_count():
    dataset, audit = _build_tiny_fixture()

    strict = screen_signals(dataset, audit, alpha=1e-12)
    lenient = screen_signals(dataset, audit, alpha=0.999)

    assert strict.alpha == 1e-12
    assert lenient.alpha == 0.999
    assert lenient.n_significant >= strict.n_significant


# --- The q == alpha exact-boundary case (strict `<`) --------------------------


def test_significant_boundary_q_equals_alpha_exactly_is_false():
    dataset, audit = _build_tiny_fixture()
    # Restrict to a single well-defined candidate so BH-FDR is forced onto one
    # p-value, then pin its q-value to exactly ALPHA to exercise the strict-<
    # boundary deterministically (the coder's explicitly-flagged edge case).
    single_audit = audit[audit["signal"] == "s_normal"]

    with patch(
        "secom_app.doe_screening.stats.false_discovery_control",
        return_value=np.array([ALPHA]),
    ) as mocked:
        result = screen_signals(dataset, single_audit, alpha=ALPHA)

    mocked.assert_called_once()
    row = result.table.iloc[0]
    assert row["q_value"] == pytest.approx(ALPHA)
    assert bool(row["significant"]) is False


# --- Degenerate branches ------------------------------------------------------


def test_no_kept_signals_in_nonempty_audit_returns_empty_typed_result():
    dataset, audit = _build_tiny_fixture()
    dropped_audit = audit.assign(status="drop")

    result = screen_signals(dataset, dropped_audit)

    assert result.n_candidates == 0
    assert result.n_significant == 0
    assert list(result.table.columns) == SCREEN_COLUMNS
    assert len(result.table) == 0
    assert result.alpha == ALPHA
    assert result.method == "welch_t + cohens_d, BH-FDR"


def test_completely_empty_audit_dataframe_returns_empty_typed_result():
    dataset, _audit = _build_tiny_fixture()
    empty_audit = pd.DataFrame(columns=["signal", "status"])

    result = screen_signals(dataset, empty_audit)

    assert result.n_candidates == 0
    assert result.n_significant == 0
    assert list(result.table.columns) == SCREEN_COLUMNS
    assert len(result.table) == 0


def test_all_candidates_degenerate_gives_empty_fdr_input_but_nonempty_table():
    # Only below-MIN_GROUP_N / zero-pooled-SD signals -> the `if p_values:`
    # BH-FDR branch is never entered, but rows still exist (all NaN/False).
    dataset, audit = _build_tiny_fixture()
    degenerate_audit = audit[
        audit["signal"].isin(["s_low_n_pass", "s_low_n_fail", "s_zero_pooled"])
    ]

    result = screen_signals(dataset, degenerate_audit)

    assert result.n_candidates == 3
    assert result.n_significant == 0
    assert result.table["p_value"].isna().all()
    assert result.table["q_value"].isna().all()
    assert (~result.table["significant"]).all()


# --- Method fidelity: reuses scipy, does not re-derive stats ------------------


def test_reuses_scipy_ttest_ind_and_false_discovery_control_not_reimplemented():
    dataset, audit = _build_tiny_fixture()

    with (
        patch(
            "secom_app.doe_screening.stats.ttest_ind", wraps=stats.ttest_ind
        ) as ttest_spy,
        patch(
            "secom_app.doe_screening.stats.false_discovery_control",
            wraps=stats.false_discovery_control,
        ) as fdr_spy,
    ):
        result = screen_signals(dataset, audit)

    assert ttest_spy.called
    assert fdr_spy.called
    assert result.n_candidates == 6


# --- Honesty framing (SME red line) ------------------------------------------


def test_module_and_function_docstrings_state_observational_not_causal_framing():
    import secom_app.doe_screening as module

    doc = (module.__doc__ or "").lower()
    assert "observational" in doc
    assert "not a designed experiment" in doc
    assert "no causal claim" in doc or "not causal" in doc

    func_doc = (screen_signals.__doc__ or "").lower()
    assert "not a designed experiment" in func_doc
    assert "not causal" in func_doc

    assert "screening" in module.__doc__.lower() or "association" in module.__doc__.lower()


def test_screening_result_dataclass_is_frozen():
    dataset, audit = _build_tiny_fixture()
    result = screen_signals(dataset, audit)

    with pytest.raises(AttributeError):
        result.n_candidates = 999  # type: ignore[misc]

    assert isinstance(result, ScreeningResult)
