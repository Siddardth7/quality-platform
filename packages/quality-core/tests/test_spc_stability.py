"""Tests for the capability stability gate (quality_core/spc/stability.py, #191).

Migrated from tests/test_pages_process_capability.py, which tested the same
logic through the Streamlit page's `assess_control_chart`, then promoted out of
`apps/spc/tests/test_stability.py` with the module itself (audit A12, #205 PR 2).
The two #191 baseline tests that read the SPC app's committed demo CSV and its
stream -> chart-type map stay app-side: the core suite imports no app and
hard-codes no app path.
"""

import pandas as pd
import pytest
from quality_core.spc.control_charts import compute_imr
from quality_core.spc.stability import assess_stability, stability_fields


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


# --- #191: the I-MR branch must chart rows in the frame's own order (§8.7) ---


def test_imr_branch_charts_tied_subgroups_in_the_frames_row_order():
    """A frame already in subgroup order must be charted in row order, ties included.

    `assess_stability`'s I-MR branch sorts by "subgroup", and a stream charted as
    I-MR can carry several rows per subgroup — so the sort is full of ties. A stable
    sort is a no-op on already-ordered input, so its sigma_hat must equal
    `compute_imr` on the frame's `value` column exactly as written. The values here
    are deliberately arranged so that any permutation within a tie group changes the
    moving ranges: within each subgroup they alternate far apart.

    CEILING (OQ-D, accepted by the SME): this pins the *semantics*, not the sort
    algorithm. `kind="quicksort"` happens to be a no-op on inputs this small, so
    only the app-side CSV baseline in `apps/spc/tests/test_stability.py` empirically
    catches an unstable `kind`. That test is load-bearing and must not be weakened.
    """
    values = [1.0, 9.0, 2.0, 8.0, 3.0, 7.0, 4.0, 6.0, 5.0, 10.0, 1.5, 9.5]
    frame = pd.DataFrame(
        {
            "stream": "tied",
            # 6 subgroups x 2 rows each -> every subgroup key is tied.
            "subgroup": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6],
            "value": values,
        }
    )
    assert frame["subgroup"].is_monotonic_increasing
    assert len(frame) > frame["subgroup"].nunique(), "fixture must contain tied subgroups"

    sigma_hat, _ = assess_stability(frame, "I-MR")
    expected = compute_imr(frame["value"].tolist())

    assert sigma_hat == expected["sigma_hat"]


def test_imr_branch_reorders_a_frame_that_is_not_in_subgroup_order():
    """The other direction: the sort is real, not dead code.

    Feeding the same rows shuffled by subgroup must produce the sorted frame's
    sigma_hat, not the shuffled row order's. Without this case, deleting
    `sort_values` entirely would leave the test above green.
    """
    frame = pd.DataFrame(
        {
            "stream": "shuffled",
            "subgroup": [3, 1, 2, 5, 4, 6],
            "value": [30.0, 10.0, 20.0, 50.0, 40.0, 60.0],
        }
    )

    sigma_hat, _ = assess_stability(frame, "I-MR")

    assert sigma_hat == compute_imr([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])["sigma_hat"]
    assert sigma_hat != compute_imr(frame["value"].tolist())["sigma_hat"]
