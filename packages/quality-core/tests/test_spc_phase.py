import pytest
from quality_core.spc.constants import (
    IMR_D2,
    MIN_BASELINE_INDIVIDUALS,
    MIN_BASELINE_SUBGROUPS,
    XBAR_R_CONSTANTS,
    XBAR_S_CONSTANTS,
)
from quality_core.spc.control_charts import compute_imr, compute_xbar_r, compute_xbar_s
from quality_core.spc.phase import freeze_imr, freeze_xbar_r, freeze_xbar_s

FROZEN_LIMITS_KEYS = {
    "chart_type",
    "n",
    "center_line",
    "sigma_hat",
    "sigma_method",
    "unbiasing_constant",
    "ucl_x",
    "lcl_x",
    "dispersion_center",
    "ucl_disp",
    "lcl_disp",
    "baseline_subgroup_count",
    "excluded",
    "phase_i_range",
    "frozen_at",
    "baseline_adequate",
    "baseline_note",
}

# 25 subgroups of size 5 -- at the NIST floor.
XBAR_R_BASELINE_25 = [
    [10 + (i % 3) + j for j in range(5)] for i in range(25)
]
XBAR_R_BASELINE_24 = XBAR_R_BASELINE_25[:24]

# One wide-spread outlier row so excluding it visibly shifts the limits.
XBAR_R_BASELINE_WITH_OUTLIER = [list(row) for row in XBAR_R_BASELINE_25]
XBAR_R_BASELINE_WITH_OUTLIER[10] = [10, 100, 5, 95, 50]

XBAR_R_BASELINE_ZERO_VARIATION = [[10, 10, 10, 10, 10] for _ in range(25)]

# 25 subgroups of size 12 -- at floor.
XBAR_S_BASELINE_25 = [
    [1 + (i % 3) + j for j in range(12)] for i in range(25)
]
XBAR_S_BASELINE_24 = XBAR_S_BASELINE_25[:24]

# 100 individuals -- at the Montgomery floor.
IMR_BASELINE_100 = [10, 12, 11, 15, 14] * 20
IMR_BASELINE_99 = IMR_BASELINE_100[:99]
IMR_BASELINE_WITH_OUTLIER = list(IMR_BASELINE_100)
IMR_BASELINE_WITH_OUTLIER[50] = 500
IMR_BASELINE_ZERO_VARIATION = [7.0] * 100


# ---------------------------------------------------------------------------
# 1-2: key-set checks
# ---------------------------------------------------------------------------


def test_freeze_xbar_r_returns_expected_keys():
    result = freeze_xbar_r(XBAR_R_BASELINE_25)
    assert set(result.keys()) == FROZEN_LIMITS_KEYS


def test_freeze_xbar_s_returns_expected_keys():
    result = freeze_xbar_s(XBAR_S_BASELINE_25)
    assert set(result.keys()) == FROZEN_LIMITS_KEYS


def test_freeze_imr_returns_expected_keys():
    result = freeze_imr(IMR_BASELINE_100)
    assert set(result.keys()) == FROZEN_LIMITS_KEYS


# ---------------------------------------------------------------------------
# 3: frozen limits equal the baseline compute_* limits numerically
# ---------------------------------------------------------------------------


def test_freeze_xbar_r_matches_compute_xbar_r_on_same_baseline():
    frozen = freeze_xbar_r(XBAR_R_BASELINE_25)
    plain = compute_xbar_r(XBAR_R_BASELINE_25)
    assert frozen["center_line"] == pytest.approx(plain["xbarbar"])
    assert frozen["dispersion_center"] == pytest.approx(plain["rbar"])
    assert frozen["ucl_x"] == pytest.approx(plain["ucl_x"])
    assert frozen["lcl_x"] == pytest.approx(plain["lcl_x"])
    assert frozen["ucl_disp"] == pytest.approx(plain["ucl_r"])
    assert frozen["lcl_disp"] == pytest.approx(plain["lcl_r"])
    assert frozen["sigma_hat"] == pytest.approx(plain["sigma_hat"])


def test_freeze_xbar_s_matches_compute_xbar_s_on_same_baseline():
    frozen = freeze_xbar_s(XBAR_S_BASELINE_25)
    plain = compute_xbar_s(XBAR_S_BASELINE_25)
    assert frozen["center_line"] == pytest.approx(plain["xbarbar"])
    assert frozen["dispersion_center"] == pytest.approx(plain["sbar"])
    assert frozen["ucl_x"] == pytest.approx(plain["ucl_x"])
    assert frozen["lcl_x"] == pytest.approx(plain["lcl_x"])
    assert frozen["ucl_disp"] == pytest.approx(plain["ucl_s"])
    assert frozen["lcl_disp"] == pytest.approx(plain["lcl_s"])
    assert frozen["sigma_hat"] == pytest.approx(plain["sigma_hat"])


def test_freeze_imr_matches_compute_imr_on_same_baseline():
    frozen = freeze_imr(IMR_BASELINE_100)
    plain = compute_imr(IMR_BASELINE_100)
    assert frozen["center_line"] == pytest.approx(plain["xbar"])
    assert frozen["dispersion_center"] == pytest.approx(plain["mrbar"])
    assert frozen["ucl_x"] == pytest.approx(plain["ucl_x"])
    assert frozen["lcl_x"] == pytest.approx(plain["lcl_x"])
    assert frozen["ucl_disp"] == pytest.approx(plain["ucl_mr"])
    assert frozen["lcl_disp"] == pytest.approx(plain["lcl_mr"])
    assert frozen["sigma_hat"] == pytest.approx(plain["sigma_hat"])


# ---------------------------------------------------------------------------
# 4: sigma_method + unbiasing_constant + n correct per chart
# ---------------------------------------------------------------------------


def test_freeze_xbar_r_sigma_method_and_constant():
    result = freeze_xbar_r(XBAR_R_BASELINE_25)
    assert result["sigma_method"] == "Rbar/d2"
    assert result["unbiasing_constant"] == pytest.approx(XBAR_R_CONSTANTS[5]["d2"])
    assert result["n"] == 5


def test_freeze_xbar_s_sigma_method_and_constant():
    result = freeze_xbar_s(XBAR_S_BASELINE_25)
    assert result["sigma_method"] == "Sbar/c4"
    assert result["unbiasing_constant"] == pytest.approx(XBAR_S_CONSTANTS[12]["c4"])
    assert result["n"] == 12


def test_freeze_imr_sigma_method_and_constant():
    result = freeze_imr(IMR_BASELINE_100)
    assert result["sigma_method"] == "MRbar/d2"
    assert result["unbiasing_constant"] == pytest.approx(1.128)
    assert result["unbiasing_constant"] == pytest.approx(IMR_D2)
    assert result["n"] == 1


# ---------------------------------------------------------------------------
# 5: excluding a real baseline point shifts limits vs no-exclusion
# ---------------------------------------------------------------------------


def test_freeze_xbar_r_exclusion_shifts_limits():
    no_exclusion = freeze_xbar_r(XBAR_R_BASELINE_WITH_OUTLIER)
    with_exclusion = freeze_xbar_r(
        XBAR_R_BASELINE_WITH_OUTLIER,
        excluded=[{"index": 10, "cause": "tool jam, operator log #4471"}],
    )
    assert with_exclusion["ucl_x"] != pytest.approx(no_exclusion["ucl_x"])
    assert with_exclusion["baseline_subgroup_count"] == no_exclusion["baseline_subgroup_count"] - 1


def test_freeze_imr_exclusion_recomputes_moving_ranges_on_retained_set():
    no_exclusion = freeze_imr(IMR_BASELINE_WITH_OUTLIER)
    with_exclusion = freeze_imr(
        IMR_BASELINE_WITH_OUTLIER,
        excluded=[{"index": 50, "cause": "sensor glitch, ticket #88"}],
    )
    assert with_exclusion["dispersion_center"] != pytest.approx(no_exclusion["dispersion_center"])
    assert with_exclusion["baseline_subgroup_count"] == no_exclusion["baseline_subgroup_count"] - 1
    # Matches directly recomputing compute_imr on the retained sequence.
    retained = IMR_BASELINE_WITH_OUTLIER[:50] + IMR_BASELINE_WITH_OUTLIER[51:]
    plain_retained = compute_imr(retained)
    assert with_exclusion["dispersion_center"] == pytest.approx(plain_retained["mrbar"])


# ---------------------------------------------------------------------------
# 6-7: exclusion validation guards
# ---------------------------------------------------------------------------


def test_freeze_xbar_r_blank_cause_raises():
    with pytest.raises(ValueError):
        freeze_xbar_r(XBAR_R_BASELINE_25, excluded=[{"index": 0, "cause": "   "}])


def test_freeze_xbar_r_empty_cause_raises():
    with pytest.raises(ValueError):
        freeze_xbar_r(XBAR_R_BASELINE_25, excluded=[{"index": 0, "cause": ""}])


def test_freeze_xbar_r_out_of_range_index_raises():
    with pytest.raises(ValueError):
        freeze_xbar_r(XBAR_R_BASELINE_25, excluded=[{"index": 999, "cause": "bad calibration"}])


def test_freeze_xbar_r_negative_index_raises():
    with pytest.raises(ValueError):
        freeze_xbar_r(XBAR_R_BASELINE_25, excluded=[{"index": -1, "cause": "bad calibration"}])


def test_freeze_xbar_r_duplicate_index_raises():
    with pytest.raises(ValueError):
        freeze_xbar_r(
            XBAR_R_BASELINE_25,
            excluded=[
                {"index": 0, "cause": "bad calibration"},
                {"index": 0, "cause": "operator error"},
            ],
        )


# ---------------------------------------------------------------------------
# excluded=() default -> identical to plain compute_*
# ---------------------------------------------------------------------------


def test_freeze_xbar_r_default_excluded_matches_plain_compute():
    frozen = freeze_xbar_r(XBAR_R_BASELINE_25)
    plain = compute_xbar_r(XBAR_R_BASELINE_25)
    assert frozen["excluded"] == []
    assert frozen["ucl_x"] == pytest.approx(plain["ucl_x"])
    assert frozen["baseline_subgroup_count"] == len(XBAR_R_BASELINE_25)


# ---------------------------------------------------------------------------
# 8-9: soft guardrail — both branches, at the exact floor boundary
# ---------------------------------------------------------------------------


def test_freeze_xbar_r_below_floor_is_soft_flagged():
    result = freeze_xbar_r(XBAR_R_BASELINE_24)
    assert len(XBAR_R_BASELINE_24) == MIN_BASELINE_SUBGROUPS - 1
    assert result["baseline_adequate"] is False
    assert result["baseline_note"] != ""


def test_freeze_xbar_r_at_floor_is_adequate():
    result = freeze_xbar_r(XBAR_R_BASELINE_25)
    assert len(XBAR_R_BASELINE_25) == MIN_BASELINE_SUBGROUPS
    assert result["baseline_adequate"] is True
    assert result["baseline_note"] == ""


def test_freeze_imr_below_floor_is_soft_flagged():
    result = freeze_imr(IMR_BASELINE_99)
    assert len(IMR_BASELINE_99) == MIN_BASELINE_INDIVIDUALS - 1
    assert result["baseline_adequate"] is False
    assert result["baseline_note"] != ""


def test_freeze_imr_at_floor_is_adequate():
    result = freeze_imr(IMR_BASELINE_100)
    assert len(IMR_BASELINE_100) == MIN_BASELINE_INDIVIDUALS
    assert result["baseline_adequate"] is True
    assert result["baseline_note"] == ""


def test_freeze_xbar_r_does_not_raise_when_below_floor():
    # Soft guardrail -- never raises, per SME resolution.
    freeze_xbar_r(XBAR_R_BASELINE_24)


# ---------------------------------------------------------------------------
# 10: frozen_at
# ---------------------------------------------------------------------------


def test_freeze_xbar_r_frozen_at_defaults_to_nonempty_iso_string():
    result = freeze_xbar_r(XBAR_R_BASELINE_25)
    assert isinstance(result["frozen_at"], str)
    assert result["frozen_at"] != ""


def test_freeze_xbar_r_frozen_at_explicit_passthrough():
    result = freeze_xbar_r(XBAR_R_BASELINE_25, frozen_at="2026-07-01T00:00:00+00:00")
    assert result["frozen_at"] == "2026-07-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# 11: phase_i_range -- None and tuple
# ---------------------------------------------------------------------------


def test_freeze_xbar_r_phase_i_range_none():
    result = freeze_xbar_r(XBAR_R_BASELINE_25)
    assert result["phase_i_range"] is None


def test_freeze_xbar_r_phase_i_range_tuple_recorded_verbatim():
    result = freeze_xbar_r(
        XBAR_R_BASELINE_25, phase_i_range=("2026-01-01T00:00:00+00:00", "2026-02-01T00:00:00+00:00")
    )
    assert result["phase_i_range"] == (
        "2026-01-01T00:00:00+00:00",
        "2026-02-01T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# All-zero variation baseline does not raise; limits collapse to center line.
# ---------------------------------------------------------------------------


def test_freeze_xbar_r_zero_variation_does_not_raise_and_collapses_limits():
    result = freeze_xbar_r(XBAR_R_BASELINE_ZERO_VARIATION)
    assert result["dispersion_center"] == pytest.approx(0.0)
    assert result["ucl_x"] == pytest.approx(result["center_line"])
    assert result["lcl_x"] == pytest.approx(result["center_line"])


def test_freeze_xbar_s_zero_variation_does_not_raise():
    result = freeze_xbar_s([[5] * 12 for _ in range(25)])
    assert result["dispersion_center"] == pytest.approx(0.0)


def test_freeze_imr_zero_variation_does_not_raise_and_collapses_limits():
    result = freeze_imr(IMR_BASELINE_ZERO_VARIATION)
    assert result["dispersion_center"] == pytest.approx(0.0)
    assert result["ucl_x"] == pytest.approx(result["center_line"])
    assert result["lcl_x"] == pytest.approx(result["center_line"])
