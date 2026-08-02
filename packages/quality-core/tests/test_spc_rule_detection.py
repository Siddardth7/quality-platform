import pytest
from quality_core.spc.rule_detection import (
    SHEWHART_CHART_TYPES,
    detect_nelson_violations,
    detect_violations,
    detect_we_violations,
)


def _has_violation(violations, rule, index):
    return any(v["rule"] == rule and v["index"] == index for v in violations)


def test_we_raises_for_nonpositive_sigma():
    with pytest.raises(ValueError):
        detect_we_violations([0.1, 0.2, 0.3], cl=0.0, sigma=0.0)


def test_nelson_raises_for_nonpositive_sigma():
    with pytest.raises(ValueError):
        detect_nelson_violations([0.1, 0.2, 0.3], cl=0.0, sigma=-1.0)


def test_nelson_rule_4_does_not_fire_with_equal_consecutive_points():
    # A flat segment (delta == 0) breaks alternation regardless of length.
    points = [1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 3, 1]
    violations = detect_nelson_violations(points, cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Nelson Rule 4" for v in violations)


def test_we_rule_1_fires_for_point_above_positive_3sigma():
    violations = detect_we_violations([0.1, 0.2, 3.2], cl=0.0, sigma=1.0)
    assert _has_violation(violations, "Western Electric Rule 1", 2)


def test_we_rule_1_fires_for_point_below_negative_3sigma():
    violations = detect_we_violations([0.1, -0.2, -3.4], cl=0.0, sigma=1.0)
    assert _has_violation(violations, "Western Electric Rule 1", 2)


def test_we_rule_1_does_not_fire_at_exactly_3sigma():
    violations = detect_we_violations([0.0, 3.0], cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Western Electric Rule 1" for v in violations)


def test_we_rule_2_fires_for_two_of_three_beyond_2sigma_same_side():
    violations = detect_we_violations([0.2, 2.2, 2.4], cl=0.0, sigma=1.0)
    assert _has_violation(violations, "Western Electric Rule 2", 2)


def test_we_rule_2_does_not_fire_when_points_are_on_opposite_sides():
    violations = detect_we_violations([2.3, 0.2, -2.4], cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Western Electric Rule 2" for v in violations)


def test_we_rule_2_does_not_fire_with_only_one_of_three_beyond_2sigma():
    violations = detect_we_violations([0.2, 2.2, 1.8], cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Western Electric Rule 2" for v in violations)


def test_we_rule_3_fires_for_four_of_five_beyond_1sigma_same_side():
    violations = detect_we_violations([0.2, 1.2, 1.3, 1.4, 1.5], cl=0.0, sigma=1.0)
    assert _has_violation(violations, "Western Electric Rule 3", 4)


def test_we_rule_3_does_not_fire_with_only_three_of_five_beyond_1sigma():
    violations = detect_we_violations([0.2, 1.2, 1.3, 1.4, 0.5], cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Western Electric Rule 3" for v in violations)


def test_we_rule_3_fires_when_four_of_five_are_same_side_despite_an_opposite_point():
    # F-03: 4 of 5 beyond 1sigma on one side still fires even though the 5th
    # point is on the opposite side (same-side count only, no opposite veto).
    violations = detect_we_violations([1.2, 1.3, -1.4, 1.5, 1.6], cl=0.0, sigma=1.0)
    assert _has_violation(violations, "Western Electric Rule 3", 4)


def test_we_rule_4_fires_for_eight_points_on_same_side_of_centerline():
    violations = detect_we_violations([0.2, 0.3, 0.1, 0.4, 0.5, 0.3, 0.2, 0.4], cl=0.0, sigma=1.0)
    assert _has_violation(violations, "Western Electric Rule 4", 7)


def test_we_rule_4_does_not_fire_for_only_seven_points_on_same_side():
    violations = detect_we_violations([0.2, 0.3, 0.1, 0.4, 0.5, 0.3, 0.2], cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Western Electric Rule 4" for v in violations)


def test_we_rule_4_does_not_fire_when_sequence_crosses_centerline():
    violations = detect_we_violations([0.2, 0.3, 0.1, 0.4, -0.1, 0.3, 0.2, 0.4], cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Western Electric Rule 4" for v in violations)


def test_we_returns_empty_for_clean_sequence():
    violations = detect_we_violations([0.2, -0.1, 0.4, -0.3, 0.1], cl=0.0, sigma=1.0)
    assert violations == []


def test_we_can_report_multiple_rule_hits_for_same_sequence():
    violations = detect_we_violations([1.2, 1.3, 1.4, 1.5, 1.6, 2.3, 2.4, 3.4], cl=0.0, sigma=1.0)
    assert any(v["rule"] == "Western Electric Rule 1" for v in violations)
    assert any(v["rule"] == "Western Electric Rule 2" for v in violations)
    assert any(v["rule"] == "Western Electric Rule 3" for v in violations)
    assert any(v["rule"] == "Western Electric Rule 4" for v in violations)


def test_nelson_set_uses_its_own_numbering_not_western_electric_labels():
    # DECISION 2: the Nelson set emits only "Nelson Rule N" labels (its own
    # eight tests, own numbers) -- it never delegates to the WE labels.
    violations = detect_nelson_violations([1.2, 1.3, 1.4, 1.5, 1.6, 2.3, 2.4, 3.4], cl=0.0, sigma=1.0)
    assert any(v["rule"] == "Nelson Rule 1" for v in violations)
    assert any(v["rule"] == "Nelson Rule 5" for v in violations)
    assert any(v["rule"] == "Nelson Rule 6" for v in violations)
    assert not any(str(v["rule"]).startswith("Western Electric") for v in violations)
    # Only 8 points -- the 9-in-a-row run test (Nelson Rule 2) cannot fire yet.
    assert not any(v["rule"] == "Nelson Rule 2" for v in violations)


def test_nelson_zone_labels_are_not_interchangeable():
    """Pin two_of_three -> Nelson Rule 5 and four_of_five -> Nelson Rule 6 individually.

    The set-level test above trips BOTH zone tests, so it passes even if the two
    labels are swapped in NELSON_LABELS. These two fixtures each trip exactly
    one zone test, so swapping the labels flips both assertions. This is the
    single standards-fidelity claim DECISION 2 exists to make.
    """
    # Two points beyond +2 sigma inside a 3-window; 1-sigma zone needs 4 of 5,
    # unreachable with 3 points -> only the 2-of-3 test can fire.
    only_two_of_three = detect_nelson_violations([2.5, -2.5, 2.5], cl=0.0, sigma=1.0)
    assert _has_violation(only_two_of_three, "Nelson Rule 5", 2)
    assert not any(v["rule"] == "Nelson Rule 6" for v in only_two_of_three)

    # Four points beyond +1 sigma inside a 5-window, all below 2 sigma -> only
    # the 4-of-5 test can fire.
    only_four_of_five = detect_nelson_violations(
        [1.5, 1.5, -1.5, 1.5, 1.5], cl=0.0, sigma=1.0
    )
    assert _has_violation(only_four_of_five, "Nelson Rule 6", 4)
    assert not any(v["rule"] == "Nelson Rule 5" for v in only_four_of_five)


def test_run_rule_window_length_is_exact_for_both_sets():
    """Pin the 8-vs-9 run length at its exact boundary, in both directions.

    An off-by-one in the run window is the easiest mistake in this issue and is
    invisible to any fixture whose breaking point sits mid-window. Values are
    held inside +/-1 sigma so no zone test can fire and mask the result.
    """
    # Western Electric Rule 4 = 8 in a row: 7 must not fire, 8 must.
    assert not any(
        v["rule"] == "Western Electric Rule 4"
        for v in detect_we_violations([0.5] * 7, cl=0.0, sigma=1.0)
    )
    assert _has_violation(
        detect_we_violations([0.5] * 8, cl=0.0, sigma=1.0),
        "Western Electric Rule 4",
        7,
    )

    # Nelson Test 2 = 9 in a row: 8 must not fire, 9 must.
    assert not any(
        v["rule"] == "Nelson Rule 2"
        for v in detect_nelson_violations([0.5] * 8, cl=0.0, sigma=1.0)
    )
    assert _has_violation(
        detect_nelson_violations([0.5] * 9, cl=0.0, sigma=1.0),
        "Nelson Rule 2",
        8,
    )

    # Series length alone does not pin the window WIDTH: the loop start
    # (`range(run_length - 1, ...)`) is independent of the slice bound, so a
    # narrowed window still fires on a long-enough series. Put the breaking
    # point at window position 0 -- the only position a narrowed window drops.
    assert not any(
        v["rule"] == "Western Electric Rule 4"
        for v in detect_we_violations([-0.1] + [0.5] * 7, cl=0.0, sigma=1.0)
    )
    assert not any(
        v["rule"] == "Nelson Rule 2"
        for v in detect_nelson_violations([-0.1] + [0.5] * 8, cl=0.0, sigma=1.0)
    )


def test_point_exactly_on_centerline_breaks_a_run():
    """A point exactly at the centerline is on neither side, so it breaks the run.

    Pins the strict `> 0` / `< 0` comparison against a `>= 0` relaxation, which
    no other fixture distinguishes.
    """
    nine_with_centerline_point = [0.5] * 4 + [0.0] + [0.5] * 4
    assert not any(
        v["rule"] == "Nelson Rule 2"
        for v in detect_nelson_violations(nine_with_centerline_point, cl=0.0, sigma=1.0)
    )
    assert not any(
        v["rule"] == "Western Electric Rule 4"
        for v in detect_we_violations([0.5] * 3 + [0.0] + [0.5] * 4, cl=0.0, sigma=1.0)
    )


def test_nelson_rule_3_fires_for_six_strictly_increasing_points():
    violations = detect_nelson_violations([1, 2, 3, 4, 5, 6], cl=0.0, sigma=1.0)
    assert _has_violation(violations, "Nelson Rule 3", 5)


def test_nelson_rule_3_does_not_fire_for_only_five_monotonic_points():
    violations = detect_nelson_violations([1, 2, 3, 4, 5], cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Nelson Rule 3" for v in violations)


def test_nelson_rule_3_does_not_fire_when_trend_breaks():
    violations = detect_nelson_violations([1, 2, 3, 4, 4, 5], cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Nelson Rule 3" for v in violations)


def test_nelson_rule_4_fires_for_fourteen_alternating_points():
    violations = detect_nelson_violations([1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3], cl=0.0, sigma=1.0)
    assert _has_violation(violations, "Nelson Rule 4", 13)


def test_nelson_rule_4_does_not_fire_when_alternation_breaks():
    violations = detect_nelson_violations([1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 2, 1], cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Nelson Rule 4" for v in violations)


def test_nelson_rule_7_fires_for_fifteen_points_within_one_sigma():
    points = [0.1, -0.2, 0.3, -0.4, 0.2, -0.1, 0.5, -0.6, 0.2, -0.3, 0.1, -0.2, 0.4, -0.5, 0.2]
    violations = detect_nelson_violations(points, cl=0.0, sigma=1.0)
    assert _has_violation(violations, "Nelson Rule 7", 14)


def test_nelson_rule_7_does_not_fire_when_point_hits_one_sigma_boundary():
    points = [0.1, -0.2, 0.3, -0.4, 0.2, -0.1, 0.5, -0.6, 0.2, -0.3, 0.1, -0.2, 0.4, -0.5, 1.0]
    violations = detect_nelson_violations(points, cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Nelson Rule 7" for v in violations)


def test_nelson_rule_8_fires_for_eight_points_outside_one_sigma_on_both_sides():
    points = [1.2, -1.3, 1.4, -1.5, 1.6, -1.7, 1.8, -1.9]
    violations = detect_nelson_violations(points, cl=0.0, sigma=1.0)
    assert _has_violation(violations, "Nelson Rule 8", 7)


def test_nelson_rule_8_does_not_fire_when_all_points_are_on_same_side():
    points = [1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9]
    violations = detect_nelson_violations(points, cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Nelson Rule 8" for v in violations)


def test_nelson_rule_8_does_not_fire_when_a_point_is_within_one_sigma():
    points = [1.2, -1.3, 1.4, -1.5, 1.6, -1.7, 0.9, -1.9]
    violations = detect_nelson_violations(points, cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Nelson Rule 8" for v in violations)


# ---------------------------------------------------------------------------
# #192 (F-03 / F-04): same-side counting fix + Nelson's own 1-8 numbering.
# ---------------------------------------------------------------------------


def test_we_rule_2_fires_on_same_side_hits_even_with_an_opposite_side_point():
    # F-03: same-side count alone decides it; an opposite-side hit no longer vetoes.
    violations = detect_we_violations([2.5, -2.5, 2.5], cl=0.0, sigma=1.0)
    assert violations == [{"index": 2, "rule": "Western Electric Rule 2"}]


def test_we_rule_3_fires_on_same_side_hits_even_with_an_opposite_side_point():
    violations = detect_we_violations([1.5, 1.5, -1.5, 1.5, 1.5], cl=0.0, sigma=1.0)
    assert violations == [{"index": 4, "rule": "Western Electric Rule 3"}]


def test_count_same_side_does_not_fire_with_one_hit_per_side():
    # Negative case: one hit on each side is neither 2-of-3 nor 4-of-5 same-side.
    violations = detect_we_violations([2.5, -2.5, 0.2], cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Western Electric Rule 2" for v in violations)


def test_nelson_does_not_fire_eight_in_a_row_run_rule():
    # F-04: Nelson's run test is 9-in-a-row, not WE's 8-in-a-row.
    assert detect_nelson_violations([1.0] * 8, cl=0.0, sigma=1.0) == []


def test_nelson_rule_2_fires_for_nine_in_a_row_same_side():
    violations = detect_nelson_violations([1.0] * 9, cl=0.0, sigma=1.0)
    assert violations == [{"index": 8, "rule": "Nelson Rule 2"}]


def test_we_rule_4_still_fires_for_eight_in_a_row():
    # DECISION 1: WE keeps its own 8-in-a-row run length.
    violations = detect_we_violations([1.0] * 8, cl=0.0, sigma=1.0)
    assert violations == [{"index": 7, "rule": "Western Electric Rule 4"}]


# ---------------------------------------------------------------------------
# W10-5 (#145): detect_violations — the run-rule gating chokepoint.
# ---------------------------------------------------------------------------


def test_shewhart_chart_types_is_exactly_the_documented_set():
    assert SHEWHART_CHART_TYPES == frozenset({"Xbar-R", "Xbar-S", "I-MR", "p", "c", "u"})
    assert "EWMA" not in SHEWHART_CHART_TYPES
    assert "CUSUM" not in SHEWHART_CHART_TYPES


def test_gate_runs_we_on_shewhart():
    # A >3sigma point on a Shewhart type fires WE Rule 1 through the gate.
    violations = detect_violations("I-MR", [0.1, 0.2, 3.2], cl=0.0, sigma=1.0, rule_set="Western Electric")
    assert _has_violation(violations, "Western Electric Rule 1", 2)


def test_gate_runs_nelson_when_selected():
    points = [1, 2, 3, 4, 5, 6]
    violations = detect_violations("I-MR", points, cl=0.0, sigma=1.0, rule_set="Nelson")
    assert _has_violation(violations, "Nelson Rule 5", 5)


@pytest.mark.parametrize("chart_type", ["EWMA", "CUSUM"])
@pytest.mark.parametrize("rule_set", ["Western Electric", "Nelson"])
def test_gate_does_not_run_rules_on_ewma_or_cusum(chart_type, rule_set):
    # MANDATED: data that WOULD trip WE Rule 1 on a Shewhart chart is suppressed
    # by the gate itself (not the data) for EWMA/CUSUM chart types.
    points = [0.1, 0.2, 3.2]
    assert detect_we_violations(points, cl=0.0, sigma=1.0) != []  # prove the data trips it
    assert detect_violations(chart_type, points, cl=0.0, sigma=1.0, rule_set=rule_set) == []


def test_gate_returns_empty_for_nonpositive_sigma():
    points = [0.1, 0.2, 3.2]
    assert detect_we_violations(points, cl=0.0, sigma=1.0) != []  # would fire if not gated
    assert detect_violations("I-MR", points, cl=0.0, sigma=0.0, rule_set="Western Electric") == []


def test_gate_returns_empty_for_unknown_chart_type():
    points = [0.1, 0.2, 3.2]
    assert detect_violations("bogus", points, cl=0.0, sigma=1.0, rule_set="Western Electric") == []
