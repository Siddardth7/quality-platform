"""Tests for the capability stability gate (spc_engine/stability.py, #191).

Migrated from tests/test_pages_process_capability.py, which tested the same
logic through the Streamlit page's `assess_control_chart`.
"""

from pathlib import Path

import pandas as pd
import pytest

from spc_app.spc_engine.stability import assess_stability, stability_fields


def _imr_frame(values: list[float], stream: str = "autoclave_temp") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "stream": stream,
            "subgroup": range(1, len(values) + 1),
            "value": values,
        }
    )


def _subgrouped_frame(subgroups: list[list[float]], stream: str) -> pd.DataFrame:
    rows = []
    for index, group in enumerate(subgroups, start=1):
        for value in group:
            rows.append({"stream": stream, "subgroup": index, "value": value})
    return pd.DataFrame(rows)


def test_stable_individuals_series_has_no_signals():
    # Small, centered oscillation well within +/-1 sigma -> in control.
    values = [1.0, 2.0] * 5
    sigma_hat, signals = assess_stability(_imr_frame(values), "I-MR")
    assert sigma_hat > 0
    assert signals == []


def test_imr_is_the_default_chart_type():
    values = [1.0, 2.0] * 5
    assert assess_stability(_imr_frame(values)) == assess_stability(_imr_frame(values), "I-MR")


def test_out_of_control_series_is_flagged():
    # A gross outlier trips Western Electric Rule 1 (point beyond +/-3 sigma).
    values = [1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 20.0]
    _, signals = assess_stability(_imr_frame(values), "I-MR")
    assert len(signals) >= 1


def test_xbar_r_path_returns_sigma_and_signals():
    subgroups = [
        [10.0, 11.0, 12.0, 13.0, 14.0],
        [11.0, 12.0, 13.0, 14.0, 15.0],
        [9.0, 10.0, 11.0, 12.0, 13.0],
    ]
    sigma_hat, signals = assess_stability(
        _subgrouped_frame(subgroups, "ply_thickness"), "Xbar-R"
    )
    assert sigma_hat > 0
    assert isinstance(signals, list)


def test_xbar_s_path_returns_sigma_and_signals():
    subgroups = [list(range(1, 13)), list(range(2, 14)), list(range(3, 15))]
    sigma_hat, signals = assess_stability(
        _subgrouped_frame([[float(v) for v in g] for g in subgroups], "hole_diameter"), "Xbar-S"
    )
    assert sigma_hat > 0
    assert isinstance(signals, list)


# --- the detection sigma on subgrouped charts (spec edge case 4) ---
#
# The plotted points are subgroup MEANS, so the chart's sigma is the standard
# error sigma_hat/sqrt(n), not the within-subgroup sigma_hat. The fixture below
# is built so the last subgroup mean sits BETWEEN the two candidate 3-sigma
# limits: outside 3*sigma_hat/sqrt(n) (correct -> Rule 1 fires) but inside
# 3*sigma_hat (the "simplified" sigma -> no signal at all). One case per
# direction, with the breaking point at the edge of the window.

_SE_MEANS = [10.5, 9.5] * 5 + [10.5, 11.6]  # 12 subgroups; the last one is shifted


def _standard_error_frame(stream: str) -> pd.DataFrame:
    # Each subgroup is mean + [-1, -0.5, 0, +0.5, +1] -> constant within-spread,
    # so sigma_hat is driven only by the within-subgroup range/std.
    return _subgrouped_frame(
        [[m - 1.0, m - 0.5, m, m + 0.5, m + 1.0] for m in _SE_MEANS], stream
    )


@pytest.mark.parametrize("chart_type,stream", [("Xbar-R", "ply_thickness"), ("Xbar-S", "hole_diameter")])
def test_subgrouped_detection_sigma_is_the_standard_error_of_the_means(chart_type, stream):
    sigma_hat, signals = assess_stability(_standard_error_frame(stream), chart_type)

    # Direction 1: with sigma_hat/sqrt(n) the shifted mean is out of control.
    assert [s["rule"] for s in signals] == ["Western Electric Rule 1"]
    assert signals[0]["index"] == len(_SE_MEANS) - 1

    # Direction 2: with the un-divided sigma_hat that same point is INSIDE the
    # limits, so this signal can only come from the standard error.
    center = sum(_SE_MEANS) / len(_SE_MEANS)
    deviation = abs(_SE_MEANS[-1] - center)
    assert deviation > 3 * sigma_hat / (5**0.5)
    assert deviation < 3 * sigma_hat


def test_imr_points_are_ordered_by_subgroup_not_by_row_order():
    # I-MR sigma comes from MOVING ranges, so row order changes the verdict.
    # This permutation gives sigma 4.137 / 1 signal if the frame is read as-is,
    # versus 2.660 / 3 signals in subgroup order.
    values = [1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 20.0]
    in_order = assess_stability(_imr_frame(values), "I-MR")
    shuffled = _imr_frame(values).iloc[[1, 5, 6, 0, 9, 4, 7, 2, 8, 3]].reset_index(drop=True)

    assert assess_stability(shuffled, "I-MR") == in_order
    assert in_order[0] == pytest.approx(2.659574468085107)
    assert len(in_order[1]) == 3


# --- degenerate and propagating inputs (spec edge cases 5 and 6) ---


def test_zero_sigma_chart_reports_no_signals():
    # A constant stream gives sigma_hat == 0; detect_violations' own sigma<=0
    # guard returns [], so a degenerate chart reads as in control (never raises).
    sigma_hat, signals = assess_stability(_imr_frame([5.0] * 10), "I-MR")
    assert sigma_hat == 0.0
    assert signals == []


def test_ragged_subgroups_propagate_valueerror():
    # The page's `except (ValueError, KeyError)` handler depends on this.
    ragged = _subgrouped_frame([[1.0, 2.0, 3.0], [4.0, 5.0]], "ply_thickness")
    with pytest.raises(ValueError):
        assess_stability(ragged, "Xbar-R")


def test_xbar_r_subgroup_size_above_ten_propagates_valueerror():
    too_wide = _subgrouped_frame([[float(v) for v in range(1, 13)]] * 3, "ply_thickness")
    with pytest.raises(ValueError):
        assess_stability(too_wide, "Xbar-R")


# --- the caller-supplied chart context (#191 D3) ---


def test_imr_sort_is_stable_across_tied_subgroups():
    """The I-MR branch must not reorder rows that share a subgroup.

    A stream charted as I-MR can still carry several rows per subgroup
    (ply_misalignment has 5 across 20 subgroups), so `sort_values("subgroup")`
    is full of ties. pandas' default quicksort is unstable and permutes them
    differently on different platforms, which changes every moving range and
    moves sigma_hat enough to flip the verdict — this cost two red CI runs.

    Pinned two ways: the result must equal the already-ordered frame's result
    (a stable sort is a no-op on data that is already in subgroup order), and
    sigma_hat must match the stable value exactly. Switching the engine back to
    an unstable `kind` fails both.
    """
    demo_csv = Path(__file__).resolve().parents[1] / "data" / "demo_composites_aerospace.csv"
    frame = pd.read_csv(demo_csv)
    sub = frame[frame["stream"] == "ply_misalignment"]
    assert sub["subgroup"].is_monotonic_increasing, "fixture must already be in subgroup order"
    assert len(sub) > sub["subgroup"].nunique(), "fixture must contain tied subgroups"

    sigma_hat, signals = assess_stability(sub, "I-MR")
    assert sigma_hat == pytest.approx(0.24489039329464862, rel=1e-12)
    assert len(signals) == 19

    # Sorting an already-sorted frame must be a no-op, so re-sorting stably
    # changes nothing. An unstable sort inside the engine breaks this.
    resorted = sub.sort_values("subgroup", kind="stable")
    assert assess_stability(resorted, "I-MR") == (sigma_hat, signals)


def test_demo_stream_verdicts_match_the_recorded_baseline():
    # The engine does not derive the chart type, so this map is the only thing
    # tying a demo stream to its chart. Charting hole_diameter as I-MR (a lost
    # map entry) gives 5 signals instead of 0; ply_thickness as I-MR gives 0
    # instead of 1. Golden baseline for the A09 move — a change here means a
    # verdict flipped, not that the number needs updating.
    #
    # Reads the COMMITTED demo CSV, deliberately, NOT generate_demo_dataset():
    # `data_generator._RNG` is module-level, so what it returns depends on how
    # many times it has been called in the process. The committed CSV is tracked
    # in git, is byte-identical everywhere, and is what the app actually loads.
    #
    # ply_misalignment is 19, not 20. 20 was the WRONG answer, produced by the
    # unstable default sort in assess_stability's I-MR branch reordering tied
    # subgroup rows (see test_imr_sort_is_stable_across_tied_subgroups below).
    # Fixing that sort is what moved this number; the verdict did not drift.
    from spc_app.pages.process_capability import STREAM_CHART_TYPES

    demo_csv = Path(__file__).resolve().parents[1] / "data" / "demo_composites_aerospace.csv"
    assert demo_csv.exists(), f"committed demo dataset missing: {demo_csv}"
    frame = pd.read_csv(demo_csv)
    counts = {
        stream: len(
            assess_stability(
                frame[frame["stream"] == stream], STREAM_CHART_TYPES.get(stream, "I-MR")
            )[1]
        )
        for stream in sorted(frame["stream"].unique())
    }
    assert counts == {
        "autoclave_temp": 3,
        "hole_diameter": 0,
        "panel_defects": 0,
        "ply_misalignment": 19,
        "ply_thickness": 1,
        "reject_proportion": 0,
        "surface_defects": 0,
    }


# --- stability_fields — the tri-state contract (#191 D2) ---


def test_stability_fields_none_means_not_assessed():
    stable, note = stability_fields(None)
    assert stable is None
    assert note is not None
    assert "not assessed" in note
    assert "statistical control" in note


def test_stability_fields_empty_list_means_assessed_and_in_control():
    # Load-bearing: `[]` is falsy but NOT None — an assessed, in-control process.
    # A `if not violations` test here would return the "not assessed" tri-state.
    assert stability_fields([]) == (True, None)


def test_stability_fields_non_empty_means_out_of_control():
    stable, note = stability_fields([{"index": 1, "rule": "a"}, {"index": 4, "rule": "b"}])
    assert stable is False
    assert note is not None
    assert "2 out-of-control signal(s)" in note
