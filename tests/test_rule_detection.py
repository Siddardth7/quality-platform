from src.spc_engine.rule_detection import detect_we_violations


def _has_violation(violations, rule, index):
    return any(v["rule"] == rule and v["index"] == index for v in violations)


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


def test_we_rule_3_does_not_fire_when_points_cross_centerline():
    violations = detect_we_violations([1.2, 1.3, -1.4, 1.5, 1.6], cl=0.0, sigma=1.0)
    assert not any(v["rule"] == "Western Electric Rule 3" for v in violations)


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
