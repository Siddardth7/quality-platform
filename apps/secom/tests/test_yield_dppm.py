"""Tests for secom_app/yield_dppm.py — yield/DPPM + association Pareto (W09-5, #69).

Drives `yield_summary()` and `failing_signal_pareto()`. Covers:

- Golden numbers on the real vendored SECOM data (labeled reference, DoD gate 3):
  n_total=1567, n_pass=1463, n_fail=104, yield_pct~=93.363, dppm~=66368.86.
- Tiny hand-built label series (4 pass / 1 fail -> yield 80%, dppm 200000) so the
  arithmetic is checkable by hand, plus the PASS=-1/FAIL=+1 sign convention.
- `yield_summary` edge branches: empty series raises, out-of-domain label raises,
  all-pass (dppm 0.0, yield 100.0), all-fail (dppm 1e6, yield 0.0).
- `failing_signal_pareto` on a small synthetic frame built directly (never the 5 MB
  vendored file for this part, mirrors test_charts.py/test_capability.py discipline):
  * OQ1a — counting unit is violation *events* on failed wafers, not distinct failed
    wafers (one signal contributes 3 events from only 2 distinct failed wafers).
  * The interior-NaN violation-index -> wafer-row mapping trap: a signal with an
    interior NaN must attribute its violation to the correct wafer row via the
    present-value index, not raw positional indexing (asserted against an explicit
    from-scratch naive/buggy mapping that gets it wrong).
  * OQ1b — a kept signal with 0 fail-associated violations is dropped entirely (both
    when it has no violations anywhere, and separately as the "zero fail-associated
    total across all kept signals" degenerate guard).
  * Ranking (count desc), tie-break (signal name asc), pct, cumulative_pct (monotone
    non-decreasing, ends at 100.0).
  * A dropped (non-"keep") signal is never charted or counted.
- Degenerate branches: no kept signals in the audit -> empty typed DataFrame.
- One real-data integration test proving the W09-2 (`control_charts_for_selection`)
  reuse wires up end to end (non-empty result, cumulative ends at 100.0).
- Docstring/metadata names the Pareto as association/screening, not root-cause.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from secom_app.ingest import FAIL, PASS, SecomDataset, load_secom
from secom_app.selection import SelectionCriteria, select_signals
from secom_app.yield_dppm import YieldSummary, failing_signal_pareto, yield_summary

_PARETO_COLUMNS = ["signal", "n_fail_violations", "pct", "cumulative_pct"]


# --- Golden numbers on real data (DoD gate 3 scorecard) ----------------------


def test_yield_summary_golden_numbers_on_real_secom_data():
    dataset = load_secom()

    result = yield_summary(dataset.labels)

    assert result.n_total == 1567
    assert result.n_pass == 1463
    assert result.n_fail == 104
    assert result.yield_fraction == pytest.approx(1463 / 1567)
    assert result.yield_pct == pytest.approx(93.363, abs=1e-3)
    assert result.dppm == pytest.approx(66368.86, abs=1e-2)
    # Independent hand arithmetic, not reusing the module's own formula:
    assert result.yield_pct == pytest.approx(100.0 * 1463 / 1567)
    assert result.dppm == pytest.approx((104 / 1567) * 1_000_000.0)


# --- Tiny hand-built series + sign convention --------------------------------


def test_yield_summary_tiny_hand_built_four_pass_one_fail():
    # 4 pass / 1 fail -> yield 4/5 = 80%, dppm = (1/5)*1e6 = 200000, hand-checkable.
    labels = pd.Series([PASS, PASS, PASS, PASS, FAIL])

    result = yield_summary(labels)

    assert result == YieldSummary(
        n_total=5,
        n_pass=4,
        n_fail=1,
        yield_fraction=0.8,
        yield_pct=80.0,
        dppm=200_000.0,
    )


def test_pass_fail_sign_convention_is_minus1_plus1():
    # SECOM/UCI encoding red line: -1 = pass, +1 = fail. Assert explicitly so a
    # future edit can't silently flip the convention without a test noticing.
    assert PASS == -1
    assert FAIL == 1
    labels = pd.Series([-1, -1, -1, 1])

    result = yield_summary(labels)

    assert result.n_pass == 3
    assert result.n_fail == 1
    assert result.yield_pct == pytest.approx(75.0)
    assert result.dppm == pytest.approx(250_000.0)


# --- yield_summary edge branches ---------------------------------------------


def test_yield_summary_empty_series_raises_value_error():
    with pytest.raises(ValueError, match="empty"):
        yield_summary(pd.Series([], dtype=int))


def test_yield_summary_out_of_domain_label_raises_value_error():
    with pytest.raises(ValueError, match="out-of-domain"):
        yield_summary(pd.Series([PASS, FAIL, 0]))


def test_yield_summary_all_pass_slice_is_100_pct_yield_zero_dppm():
    result = yield_summary(pd.Series([PASS, PASS, PASS]))

    assert result.n_fail == 0
    assert result.yield_pct == pytest.approx(100.0)
    assert result.dppm == pytest.approx(0.0)


def test_yield_summary_all_fail_slice_is_0_pct_yield_1e6_dppm():
    result = yield_summary(pd.Series([FAIL, FAIL]))

    assert result.n_pass == 0
    assert result.yield_pct == pytest.approx(0.0)
    assert result.dppm == pytest.approx(1_000_000.0)


# --- failing_signal_pareto: synthetic fixture --------------------------------
#
# Frame of 13 wafer rows. FAIL rows = {9, 12}, all others PASS.
#
# - sensor_event_multi: no NaN. A moderate spike (30.0) at row 12, preceded by a
#   monotonic run, so *three* SPC violation events land on failed wafers (WE Rule 1
#   @ row12, WE Rule 4 @ row9, Nelson Rule 5 @ row12) even though only 2 distinct
#   failed wafers (9, 12) are involved -> proves OQ1a counts events, not wafers.
# - sensor_alpha_gap / sensor_zeta_gap: identical data, an interior NaN at raw
#   position 4 shifts the present-value positional index away from the raw row
#   index. The single WE Rule 1 violation is at *present* index 8, which must map
#   to raw row 9 (FAIL) via `features.index[features[signal].notna()]` -- not to
#   raw row 8 (PASS), which is what naive/raw positional indexing would return.
#   Same data under two signal names -> tests the count-tie, name-ascending
#   tie-break.
# - sensor_zero_contributor: genuinely in-control, no violations anywhere ->
#   dropped from the table (OQ1b).
# - sensor_dropped: constant -> "drop" status in the audit, never charted at all.


def _build_pareto_fixture() -> tuple[SecomDataset, pd.DataFrame]:
    sensor_event_multi = [
        10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 10.05, 10.1, 10.15, 30.0,
    ]
    gap_vals = [10.0, 10.1, 9.9, 10.2, np.nan, 9.8, 10.0, 10.1, 9.9, 30.0, 10.0, 9.9, 10.1]
    sensor_zero = [
        10.0, 10.05, 9.95, 10.02, 9.98, 10.01, 9.99, 10.03, 9.97, 10.0, 10.02, 9.98, 10.01,
    ]
    sensor_dropped = [5.0] * 13

    features = pd.DataFrame(
        {
            "sensor_event_multi": sensor_event_multi,
            "sensor_alpha_gap": gap_vals,
            "sensor_zeta_gap": list(gap_vals),
            "sensor_zero_contributor": sensor_zero,
            "sensor_dropped": sensor_dropped,
        }
    )
    audit = select_signals(features, SelectionCriteria(min_non_missing=5))

    labels = pd.Series([PASS] * 13)
    labels[9] = FAIL
    labels[12] = FAIL
    timestamps = pd.Series(pd.to_datetime(["2020-01-01"] * 13))
    dataset = SecomDataset(features=features, labels=labels, timestamps=timestamps)
    return dataset, audit


def test_pareto_fixture_audit_matches_expected_keep_drop_split():
    # Sanity-check the fixture itself before trusting the Pareto assertions on it.
    _dataset, audit = _build_pareto_fixture()

    kept = set(audit.loc[audit["status"] == "keep", "signal"])
    dropped = set(audit.loc[audit["status"] == "drop", "signal"])

    assert kept == {
        "sensor_event_multi",
        "sensor_alpha_gap",
        "sensor_zeta_gap",
        "sensor_zero_contributor",
    }
    assert dropped == {"sensor_dropped"}


def test_pareto_ranking_events_not_wafers_tiebreak_and_cumulative():
    dataset, audit = _build_pareto_fixture()

    result = failing_signal_pareto(dataset, audit)

    # Zero-contributor and dropped signals never appear (OQ1b + audit filter).
    assert "sensor_zero_contributor" not in set(result["signal"])
    assert "sensor_dropped" not in set(result["signal"])

    assert list(result.columns) == _PARETO_COLUMNS
    assert result.to_dict("records") == [
        {
            "signal": "sensor_event_multi",
            "n_fail_violations": 3,
            "pct": pytest.approx(60.0),
            "cumulative_pct": pytest.approx(60.0),
        },
        {
            "signal": "sensor_alpha_gap",
            "n_fail_violations": 1,
            "pct": pytest.approx(20.0),
            "cumulative_pct": pytest.approx(80.0),
        },
        {
            "signal": "sensor_zeta_gap",
            "n_fail_violations": 1,
            "pct": pytest.approx(20.0),
            "cumulative_pct": pytest.approx(100.0),
        },
    ]

    # sensor_event_multi: 3 violation *events* land on only 2 *distinct* failed
    # wafers (rows 9 and 12) -> OQ1a (events, not distinct-wafer count) confirmed:
    # a wafer-count Pareto would have reported 2 here, not 3.
    n_distinct_failed_wafers_for_event_multi = 2
    assert result.loc[result["signal"] == "sensor_event_multi", "n_fail_violations"].item() != (
        n_distinct_failed_wafers_for_event_multi
    )

    # Monotone non-decreasing cumulative %, ending at exactly 100.0.
    cumulative = result["cumulative_pct"].tolist()
    assert cumulative == sorted(cumulative)
    assert cumulative[-1] == pytest.approx(100.0)


def test_pareto_interior_nan_maps_violation_to_correct_wafer_row_not_naive_index():
    """The flagged correctness trap: violation["index"] is positional into the
    *present* (non-NaN) values, not a raw row label. `sensor_alpha_gap` has an
    interior NaN at raw row 4; its one violation is present-index 8, which must
    resolve to raw row 9 (a FAIL wafer) -- not raw row 8 (a PASS wafer), which is
    what naive/buggy raw-positional indexing would return.
    """
    dataset, audit = _build_pareto_fixture()
    column = dataset.features["sensor_alpha_gap"]

    # The correct mapping, per spec/ASSUMPTIONS_LOG (independently recomputed here,
    # not imported from the module under test):
    original_rows = dataset.features.index[column.notna()]
    correct_row_for_present_index_8 = original_rows[8]
    assert correct_row_for_present_index_8 == 9
    assert dataset.labels.loc[9] == FAIL

    # What a naive implementation (raw positional indexing, ignoring the NaN gap)
    # would wrongly compute instead:
    naive_row_for_index_8 = dataset.features.index[8]
    assert naive_row_for_index_8 == 8
    assert dataset.labels.loc[8] == PASS
    assert naive_row_for_index_8 != correct_row_for_present_index_8

    result = failing_signal_pareto(dataset, audit)

    # The engine must have used the correct (gap-aware) mapping: sensor_alpha_gap
    # is counted with exactly 1 fail-associated violation. Had it used the naive
    # mapping above, row 8 is PASS and the violation would not have counted at
    # all -- the signal would show 0 fail violations and be dropped from the
    # table entirely (OQ1b), which would make this assertion fail.
    row = result.loc[result["signal"] == "sensor_alpha_gap"]
    assert len(row) == 1
    assert row["n_fail_violations"].item() == 1


def test_pareto_signal_with_violations_only_on_pass_rows_is_still_dropped():
    # A kept signal can have real violations yet zero of them on failed wafers --
    # OQ1b must drop it too (not just the "no violations anywhere" case above).
    # Reuse the event_multi construction but relabel row 12 (its violation row)
    # as PASS and don't fail any row this signal actually flags.
    features = pd.DataFrame(
        {
            "sensor_violates_on_pass_only": [
                10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 10.05, 10.1, 10.15, 30.0,
            ],
        }
    )
    audit = select_signals(features, SelectionCriteria(min_non_missing=5))
    labels = pd.Series([PASS] * 13)  # no FAIL rows at all
    timestamps = pd.Series(pd.to_datetime(["2020-01-01"] * 13))
    dataset = SecomDataset(features=features, labels=labels, timestamps=timestamps)

    result = failing_signal_pareto(dataset, audit)

    assert list(result.columns) == _PARETO_COLUMNS
    assert len(result) == 0


# --- Degenerate branches ------------------------------------------------------


def test_pareto_no_kept_signals_returns_empty_typed_dataframe():
    features = pd.DataFrame({"s": [5.0] * 10})  # constant -> "drop"
    audit = select_signals(features, SelectionCriteria(min_non_missing=5))
    assert (audit["status"] == "keep").sum() == 0
    labels = pd.Series([PASS] * 10)
    timestamps = pd.Series(pd.to_datetime(["2020-01-01"] * 10))
    dataset = SecomDataset(features=features, labels=labels, timestamps=timestamps)

    result = failing_signal_pareto(dataset, audit)

    assert list(result.columns) == _PARETO_COLUMNS
    assert len(result) == 0


def test_pareto_empty_audit_dataframe_returns_empty_typed_dataframe():
    features = pd.DataFrame({"s": [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 10.05]})
    audit = pd.DataFrame(columns=["signal", "status"])
    labels = pd.Series([PASS] * 10)
    timestamps = pd.Series(pd.to_datetime(["2020-01-01"] * 10))
    dataset = SecomDataset(features=features, labels=labels, timestamps=timestamps)

    result = failing_signal_pareto(dataset, audit)

    assert list(result.columns) == _PARETO_COLUMNS
    assert len(result) == 0


def test_pareto_ruleset_passthrough_to_control_charts_for_selection():
    # "we" excludes Nelson-only rules; confirm the ruleset argument really reaches
    # the underlying charting call rather than being ignored (default "nelson").
    features = pd.DataFrame(
        {
            "sensor_event_multi": [
                10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 10.05, 10.1, 10.15, 30.0,
            ],
        }
    )
    audit = select_signals(features, SelectionCriteria(min_non_missing=5))
    labels = pd.Series([PASS] * 13)
    labels[12] = FAIL
    timestamps = pd.Series(pd.to_datetime(["2020-01-01"] * 13))
    dataset = SecomDataset(features=features, labels=labels, timestamps=timestamps)

    nelson_result = failing_signal_pareto(dataset, audit, ruleset="nelson")
    we_result = failing_signal_pareto(dataset, audit, ruleset="we")

    # Under "nelson", row 12 collects WE Rule 1 *and* Nelson Rule 5 (2 events);
    # under "we", only WE Rule 1 fires on row 12 (Nelson Rule 5 doesn't exist under
    # this ruleset) -- so the two rulesets must disagree on the count.
    nelson_count = nelson_result.loc[
        nelson_result["signal"] == "sensor_event_multi", "n_fail_violations"
    ].item()
    we_count = we_result.loc[
        we_result["signal"] == "sensor_event_multi", "n_fail_violations"
    ].item()
    assert nelson_count > we_count


# --- Real-data integration touch (W09-2 reuse wires up end to end) ----------


def test_pareto_real_secom_data_integration_smoke():
    dataset = load_secom()
    audit = select_signals(dataset.features)

    result = failing_signal_pareto(dataset, audit)

    assert len(result) > 0
    assert list(result.columns) == _PARETO_COLUMNS
    assert result["cumulative_pct"].iloc[-1] == pytest.approx(100.0)
    cumulative = result["cumulative_pct"].tolist()
    assert cumulative == sorted(cumulative)
    # No zero-contributor rows leaked through.
    assert (result["n_fail_violations"] > 0).all()


# --- Association/screening labeling, not root-cause (SME red line) ---------


def test_module_and_function_docstrings_label_pareto_as_association_not_causation():
    import secom_app.yield_dppm as module

    assert "association" in module.__doc__.lower()
    assert "root cause" in module.__doc__.lower() or "root-cause" in module.__doc__.lower()
    assert "association" in failing_signal_pareto.__doc__.lower()
    assert "root cause" in failing_signal_pareto.__doc__.lower()


def test_pareto_reuses_control_charts_for_selection_not_a_reimplementation():
    # Reuse-proof: monkeypatch-free check that the real, already-tested W09-2
    # charting function produces the same per-signal violations the Pareto used,
    # by cross-checking one signal's violation set directly.
    from secom_app.charts import control_chart_for_signal

    dataset, audit = _build_pareto_fixture()
    direct = control_chart_for_signal(dataset.features, "sensor_event_multi")

    fail_rows = set(dataset.labels.index[dataset.labels == FAIL])
    expected_fail_events = sum(
        1 for violation in direct.violations if int(violation["index"]) in fail_rows
    )
    # (sensor_event_multi has no NaNs, so present-index == raw row index here.)

    result = failing_signal_pareto(dataset, audit)
    actual = result.loc[result["signal"] == "sensor_event_multi", "n_fail_violations"].item()

    assert actual == expected_fail_events == 3
