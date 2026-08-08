import math
import subprocess
import sys

import pytest
from quality_core.spc.control_charts import (
    compute_c,
    compute_imr,
    compute_p,
    compute_u,
    compute_xbar_r,
    compute_xbar_s,
    imr_limits,
)
from quality_core.spc.phase import freeze_imr, freeze_xbar_r, freeze_xbar_s

XBAR_R_SAMPLE = [
    [10, 11, 12, 13, 14],
    [11, 12, 13, 14, 15],
    [9, 10, 11, 12, 13],
]

XBAR_S_SAMPLE = [
    list(range(1, 13)),
    list(range(2, 14)),
    list(range(3, 15)),
]

IMR_SAMPLE = [10, 12, 11, 15, 14]
P_COUNTS = [3, 5, 4]
P_SAMPLE_SIZES = [100, 120, 80]
C_COUNTS = [4, 7, 5, 6]
U_COUNTS = [2, 4, 3]
U_SAMPLE_SIZES = [1.0, 2.0, 1.5]


def test_compute_xbar_r_returns_expected_keys():
    result = compute_xbar_r(XBAR_R_SAMPLE)
    expected = {
        "subgroup_means",
        "ranges",
        "xbarbar",
        "rbar",
        "ucl_x",
        "lcl_x",
        "ucl_r",
        "lcl_r",
        "sigma_hat",
    }
    assert expected.issubset(result.keys())


def test_compute_xbar_r_subgroup_means():
    result = compute_xbar_r(XBAR_R_SAMPLE)
    assert result["subgroup_means"] == pytest.approx([12.0, 13.0, 11.0])


def test_compute_xbar_r_ranges():
    result = compute_xbar_r(XBAR_R_SAMPLE)
    assert result["ranges"] == pytest.approx([4.0, 4.0, 4.0])


def test_compute_xbar_r_xbar_limits_use_aiag_a2_for_n5():
    result = compute_xbar_r(XBAR_R_SAMPLE)
    assert result["ucl_x"] == pytest.approx(14.308, rel=1e-4)
    assert result["lcl_x"] == pytest.approx(9.692, rel=1e-4)


def test_compute_xbar_r_r_limits_use_aiag_d4_for_n5():
    result = compute_xbar_r(XBAR_R_SAMPLE)
    assert result["ucl_r"] == pytest.approx(8.456, rel=1e-4)


def test_compute_xbar_r_lcl_r_clamped_at_zero():
    result = compute_xbar_r(XBAR_R_SAMPLE)
    assert result["lcl_r"] == pytest.approx(0.0)


def test_compute_xbar_r_sigma_hat_uses_d2():
    result = compute_xbar_r(XBAR_R_SAMPLE)
    assert result["sigma_hat"] == pytest.approx(4.0 / 2.326, rel=1e-4)


def test_compute_xbar_r_invalid_n_raises():
    with pytest.raises(ValueError):
        compute_xbar_r([[1], [2], [3]])


def test_compute_xbar_s_returns_expected_keys():
    result = compute_xbar_s(XBAR_S_SAMPLE)
    expected = {
        "subgroup_means",
        "std_devs",
        "xbarbar",
        "sbar",
        "ucl_x",
        "lcl_x",
        "ucl_s",
        "lcl_s",
        "sigma_hat",
    }
    assert expected.issubset(result.keys())


def test_compute_xbar_s_ucl_formula_for_n12():
    result = compute_xbar_s(XBAR_S_SAMPLE)
    subgroup_std = math.sqrt(13.0)
    expected_ucl = 7.5 + (0.886 * subgroup_std)
    assert result["ucl_x"] == pytest.approx(expected_ucl, rel=1e-4)


def test_compute_xbar_s_sigma_hat_uses_c4():
    result = compute_xbar_s(XBAR_S_SAMPLE)
    subgroup_std = math.sqrt(13.0)
    assert result["sigma_hat"] == pytest.approx(subgroup_std / 0.9776, rel=1e-4)


def test_compute_imr_returns_expected_keys():
    result = compute_imr(IMR_SAMPLE)
    expected = {
        "values",
        "moving_ranges",
        "xbar",
        "mrbar",
        "ucl_x",
        "lcl_x",
        "ucl_mr",
        "lcl_mr",
        "sigma_hat",
    }
    assert expected.issubset(result.keys())


def test_compute_imr_moving_ranges():
    result = compute_imr(IMR_SAMPLE)
    assert result["moving_ranges"] == pytest.approx([2.0, 1.0, 4.0, 1.0])


def test_compute_imr_x_limits_use_e2():
    result = compute_imr(IMR_SAMPLE)
    assert result["ucl_x"] == pytest.approx(17.72, rel=1e-4)
    assert result["lcl_x"] == pytest.approx(7.08, rel=1e-4)


def test_compute_imr_mr_limits_use_d4():
    result = compute_imr(IMR_SAMPLE)
    assert result["ucl_mr"] == pytest.approx(6.534, rel=1e-4)


def test_compute_imr_sigma_hat_uses_d2():
    result = compute_imr(IMR_SAMPLE)
    assert result["sigma_hat"] == pytest.approx(2.0 / 1.128, rel=1e-4)


def test_compute_p_returns_expected_keys():
    result = compute_p(P_COUNTS, P_SAMPLE_SIZES)
    expected = {"counts", "sample_sizes", "proportions", "pbar", "ucl", "lcl"}
    assert expected.issubset(result.keys())


def test_compute_p_pbar():
    result = compute_p(P_COUNTS, P_SAMPLE_SIZES)
    assert result["pbar"] == pytest.approx(12.0 / 300.0, rel=1e-4)


def test_compute_p_ucl_formula_uses_variable_n():
    result = compute_p(P_COUNTS, P_SAMPLE_SIZES)
    pbar = 12.0 / 300.0
    expected = pbar + 3.0 * math.sqrt((pbar * (1.0 - pbar)) / 100.0)
    assert result["ucl"][0] == pytest.approx(expected, rel=1e-4)


def test_compute_p_lcl_clamped_to_zero():
    result = compute_p(P_COUNTS, P_SAMPLE_SIZES)
    assert result["lcl"][0] == pytest.approx(0.0)


def test_compute_p_returns_point_proportions():
    result = compute_p(P_COUNTS, P_SAMPLE_SIZES)
    assert result["proportions"] == pytest.approx([0.03, 5 / 120, 0.05], rel=1e-4)


def test_compute_c_returns_expected_keys():
    result = compute_c(C_COUNTS)
    expected = {"counts", "cbar", "ucl", "lcl"}
    assert expected.issubset(result.keys())


def test_compute_c_cbar():
    result = compute_c(C_COUNTS)
    assert result["cbar"] == pytest.approx(5.5)


def test_compute_c_ucl_formula():
    result = compute_c(C_COUNTS)
    expected = 5.5 + 3.0 * math.sqrt(5.5)
    assert result["ucl"] == pytest.approx(expected, rel=1e-4)


def test_compute_c_lcl_clamped_to_zero():
    result = compute_c(C_COUNTS)
    assert result["lcl"] == pytest.approx(0.0)


def test_compute_u_returns_expected_keys():
    result = compute_u(U_COUNTS, U_SAMPLE_SIZES)
    expected = {"counts", "sample_sizes", "u_values", "ubar", "ucl", "lcl"}
    assert expected.issubset(result.keys())


def test_compute_u_ubar():
    result = compute_u(U_COUNTS, U_SAMPLE_SIZES)
    assert result["ubar"] == pytest.approx(2.0)


def test_compute_u_ucl_formula_uses_variable_n():
    result = compute_u(U_COUNTS, U_SAMPLE_SIZES)
    expected = 2.0 + 3.0 * math.sqrt(2.0 / 2.0)
    assert result["ucl"][1] == pytest.approx(expected, rel=1e-4)


def test_compute_u_lcl_clamped_to_zero():
    result = compute_u(U_COUNTS, U_SAMPLE_SIZES)
    assert result["lcl"][0] == pytest.approx(0.0)


def test_compute_u_ucl_exceeds_ubar_for_nonzero_rate():
    result = compute_u([2, 4, 3], [1.0, 2.0, 1.5])
    for ucl_val in result["ucl"]:
        assert ucl_val > result["ubar"]


def test_compute_u_lcl_still_clamped_to_zero():
    result = compute_u([0, 0, 1], [10.0, 10.0, 10.0])
    assert all(v >= 0.0 for v in result["lcl"])


def test_compute_xbar_r_non_2d_input_raises():
    with pytest.raises(ValueError):
        compute_xbar_r([1, 2, 3])  # type: ignore[list-item]


def test_compute_xbar_s_invalid_subgroup_size_raises():
    with pytest.raises(ValueError):
        compute_xbar_s([[1], [2]])  # subgroup size 1 is out of range


def test_compute_imr_too_few_values_raises():
    with pytest.raises(ValueError):
        compute_imr([5])


def test_compute_c_empty_raises():
    with pytest.raises(ValueError):
        compute_c([])


def test_compute_p_mismatched_lengths_raises():
    with pytest.raises(ValueError):
        compute_p([1, 2], [100])


def test_compute_p_nonpositive_sample_size_raises():
    with pytest.raises(ValueError):
        compute_p([1], [0])


@pytest.mark.parametrize("compute", [compute_p, compute_u])
@pytest.mark.parametrize("size", [float("nan"), float("inf"), float("-inf")])
def test_attribute_charts_reject_a_non_finite_sample_size(compute, size):
    # #200 regression: `np.nan <= 0` is False, so a NaN n slipped the positivity
    # check and produced NaN control limits with no error at all. Removing the
    # `~np.isfinite` guard makes the NaN case return silently instead of raising.
    with pytest.raises(ValueError, match="sample sizes must be positive"):
        compute([1, 2], [10.0, size])


# ---------------------------------------------------------------------------
# Phase II `frozen=` cases (W10-1, #141) — obligations 12-16
# ---------------------------------------------------------------------------

XBAR_R_PHASE_II_DATA = [
    [20, 21, 22, 23, 24],
    [19, 18, 17, 16, 15],
]

XBAR_S_PHASE_II_DATA = [
    list(range(20, 32)),
    list(range(30, 18, -1)),
]

IMR_PHASE_II_DATA = [50, 55, 48, 60, 52, 47]


def test_compute_xbar_r_frozen_returns_limits_identical_to_frozen():
    frozen = freeze_xbar_r(XBAR_R_SAMPLE)
    result = compute_xbar_r(XBAR_R_PHASE_II_DATA, frozen=frozen)
    assert result["xbarbar"] == pytest.approx(frozen["center_line"])
    assert result["rbar"] == pytest.approx(frozen["dispersion_center"])
    assert result["ucl_x"] == pytest.approx(frozen["ucl_x"])
    assert result["lcl_x"] == pytest.approx(frozen["lcl_x"])
    assert result["ucl_r"] == pytest.approx(frozen["ucl_disp"])
    assert result["lcl_r"] == pytest.approx(frozen["lcl_disp"])
    assert result["sigma_hat"] == pytest.approx(frozen["sigma_hat"])


def test_compute_xbar_r_frozen_plots_new_subgroup_means_and_ranges():
    frozen = freeze_xbar_r(XBAR_R_SAMPLE)
    result = compute_xbar_r(XBAR_R_PHASE_II_DATA, frozen=frozen)
    assert result["subgroup_means"] == pytest.approx([22.0, 17.0])
    assert result["ranges"] == pytest.approx([4.0, 4.0])
    assert result["subgroup_means"] != pytest.approx(
        compute_xbar_r(XBAR_R_SAMPLE)["subgroup_means"]
    )


def test_compute_xbar_s_frozen_returns_limits_identical_to_frozen():
    frozen = freeze_xbar_s(XBAR_S_SAMPLE)
    result = compute_xbar_s(XBAR_S_PHASE_II_DATA, frozen=frozen)
    assert result["xbarbar"] == pytest.approx(frozen["center_line"])
    assert result["sbar"] == pytest.approx(frozen["dispersion_center"])
    assert result["ucl_x"] == pytest.approx(frozen["ucl_x"])
    assert result["lcl_x"] == pytest.approx(frozen["lcl_x"])
    assert result["ucl_s"] == pytest.approx(frozen["ucl_disp"])
    assert result["lcl_s"] == pytest.approx(frozen["lcl_disp"])
    assert result["sigma_hat"] == pytest.approx(frozen["sigma_hat"])


def test_compute_xbar_s_frozen_plots_new_subgroup_means_and_std_devs():
    frozen = freeze_xbar_s(XBAR_S_SAMPLE)
    result = compute_xbar_s(XBAR_S_PHASE_II_DATA, frozen=frozen)
    baseline_means = compute_xbar_s(XBAR_S_SAMPLE)["subgroup_means"]
    assert result["subgroup_means"] != pytest.approx(baseline_means)


def test_compute_imr_frozen_returns_limits_identical_to_frozen():
    frozen = freeze_imr(IMR_SAMPLE)
    result = compute_imr(IMR_PHASE_II_DATA, frozen=frozen)
    assert result["xbar"] == pytest.approx(frozen["center_line"])
    assert result["mrbar"] == pytest.approx(frozen["dispersion_center"])
    assert result["ucl_x"] == pytest.approx(frozen["ucl_x"])
    assert result["lcl_x"] == pytest.approx(frozen["lcl_x"])
    assert result["ucl_mr"] == pytest.approx(frozen["ucl_disp"])
    assert result["lcl_mr"] == pytest.approx(frozen["lcl_disp"])
    assert result["sigma_hat"] == pytest.approx(frozen["sigma_hat"])


def test_compute_imr_frozen_plots_new_values_and_moving_ranges():
    frozen = freeze_imr(IMR_SAMPLE)
    result = compute_imr(IMR_PHASE_II_DATA, frozen=frozen)
    assert result["values"] == pytest.approx(IMR_PHASE_II_DATA)
    assert result["moving_ranges"] == pytest.approx([5.0, 7.0, 12.0, 8.0, 5.0])
    baseline_moving_ranges = compute_imr(IMR_SAMPLE)["moving_ranges"]
    assert result["moving_ranges"] != pytest.approx(baseline_moving_ranges)


def test_compute_xbar_r_frozen_chart_type_mismatch_raises():
    imr_frozen = freeze_imr(IMR_SAMPLE)
    with pytest.raises(ValueError):
        compute_xbar_r(XBAR_R_PHASE_II_DATA, frozen=imr_frozen)  # type: ignore[arg-type]


def test_compute_xbar_r_frozen_n_mismatch_raises():
    frozen = freeze_xbar_r(XBAR_R_SAMPLE)  # n=5
    new_data_n3 = [[1, 2, 3], [4, 5, 6]]
    with pytest.raises(ValueError):
        compute_xbar_r(new_data_n3, frozen=frozen)


def test_compute_xbar_s_frozen_chart_type_mismatch_raises():
    xbar_r_frozen = freeze_xbar_r(XBAR_R_SAMPLE)
    with pytest.raises(ValueError):
        compute_xbar_s(XBAR_S_PHASE_II_DATA, frozen=xbar_r_frozen)  # type: ignore[arg-type]


def test_compute_xbar_s_frozen_n_mismatch_raises():
    frozen = freeze_xbar_s(XBAR_S_SAMPLE)  # n=12
    new_data_n2 = [[1, 2], [3, 4]]
    with pytest.raises(ValueError):
        compute_xbar_s(new_data_n2, frozen=frozen)


def test_compute_imr_frozen_chart_type_mismatch_raises():
    xbar_r_frozen = freeze_xbar_r(XBAR_R_SAMPLE)
    with pytest.raises(ValueError):
        compute_imr(IMR_PHASE_II_DATA, frozen=xbar_r_frozen)  # type: ignore[arg-type]


# --- imr_limits: the single home of the AIAG I-MR limit formula (#205 PR 2, §8.2) ---


def test_imr_limits_matches_hand_evaluated_aiag_arithmetic():
    """All five keys against the AIAG constants evaluated by hand, not by re-calling it.

    Re-deriving the expected value with `IMR_E2 * mrbar` inside the test would only
    restate the implementation; these numbers come from the published constants
    (E2=2.66, D4=3.267, d2=1.128 — AIAG SPC 4th Ed.) multiplied out.
    """
    limits = imr_limits(10.0, 2.0)

    assert limits["ucl_x"] == pytest.approx(15.32, abs=1e-12)  # 10 + 2.66*2
    assert limits["lcl_x"] == pytest.approx(4.68, abs=1e-12)  # 10 - 2.66*2
    assert limits["ucl_mr"] == pytest.approx(6.534, abs=1e-12)  # 3.267*2
    assert limits["lcl_mr"] == 0.0
    assert limits["sigma_hat"] == pytest.approx(1.7730496453900707, rel=1e-12)  # 2/1.128
    assert set(limits) == {"ucl_x", "lcl_x", "ucl_mr", "lcl_mr", "sigma_hat"}


def test_imr_limits_lcl_mr_is_a_hard_zero_not_a_clamped_d3_term():
    """`lcl_mr` is literally 0.0 for every mrbar — spec §7.5, not `max(0.0, D3*mrbar)`.

    Two mrbar values, one large enough that any D3 term would be visibly non-zero.
    """
    assert imr_limits(10.0, 2.0)["lcl_mr"] == 0.0
    assert imr_limits(-5.0, 1000.0)["lcl_mr"] == 0.0


def test_imr_limits_with_zero_mrbar_is_zero_width_and_zero_sigma():
    """Spec §7.4: no guard, no raise, no clamp — degenerate input passes straight through."""
    limits = imr_limits(7.5, 0.0)

    assert limits["ucl_x"] == 7.5
    assert limits["lcl_x"] == 7.5
    assert limits["ucl_mr"] == 0.0
    assert limits["lcl_mr"] == 0.0
    assert limits["sigma_hat"] == 0.0


def test_imr_limits_is_a_pure_function_of_its_two_arguments():
    """Shifting the centre line moves both x limits by exactly that shift and nothing else.

    Pins that `xbar` enters only the individuals limits — an implementation that
    let it leak into `ucl_mr`/`sigma_hat` would still satisfy the point checks above.
    """
    base = imr_limits(0.0, 3.0)
    shifted = imr_limits(100.0, 3.0)

    assert shifted["ucl_x"] - base["ucl_x"] == pytest.approx(100.0, abs=1e-9)
    assert shifted["lcl_x"] - base["lcl_x"] == pytest.approx(100.0, abs=1e-9)
    assert shifted["ucl_mr"] == base["ucl_mr"]
    assert shifted["sigma_hat"] == base["sigma_hat"]


def test_compute_imr_reads_its_five_limit_fields_from_imr_limits():
    """§8.3: exact `==`, not approx — compute_imr must not re-derive the arithmetic.

    A second copy of the formula that rounds, reorders the terms or recomputes
    sigma differently would still pass an approx check; bit-equality is what makes
    the de-duplication provable.
    """
    result = compute_imr(IMR_SAMPLE)
    expected = imr_limits(result["xbar"], result["mrbar"])

    assert result["ucl_x"] == expected["ucl_x"]
    assert result["lcl_x"] == expected["lcl_x"]
    assert result["ucl_mr"] == expected["ucl_mr"]
    assert result["lcl_mr"] == expected["lcl_mr"]
    assert result["sigma_hat"] == expected["sigma_hat"]


def test_compute_imr_frozen_branch_does_not_go_through_imr_limits():
    """The other direction of the choice: with `frozen=`, the limits are the frozen ones.

    Without this case a `compute_imr` that always called `imr_limits` would pass the
    test above and silently discard Phase-I frozen limits.
    """
    frozen = freeze_imr(IMR_SAMPLE)
    result = compute_imr([100.0, 101.0, 99.0], frozen=frozen)

    assert result["ucl_x"] == frozen["ucl_x"]
    assert result["lcl_x"] == frozen["lcl_x"]
    assert result["sigma_hat"] == frozen["sigma_hat"]
    # And they are NOT the Phase-II data's own limits: recomputing unfrozen on the
    # same points gives a different chart, so the frozen arm really is a branch.
    assert result["ucl_x"] != compute_imr([100.0, 101.0, 99.0])["ucl_x"]


# --- The control_charts <-> phase import cycle (#205 PR 2, §8.6) ---

_CYCLE_PROBE = """
import importlib
importlib.import_module("quality_core.spc.{first}")
importlib.import_module("quality_core.spc.{second}")
from quality_core.spc.control_charts import compute_imr, compute_xbar_r, compute_xbar_s
from quality_core.spc.phase import freeze_imr, freeze_xbar_r, freeze_xbar_s

xbar_r = [[10, 11, 12], [11, 12, 13], [9, 10, 11]]
xbar_s = [list(range(1, 13)), list(range(2, 14)), list(range(3, 15))]
imr = [10, 12, 11, 15, 14]

assert compute_imr(imr, frozen=freeze_imr(imr))["ucl_x"] == freeze_imr(imr)["ucl_x"]
assert compute_xbar_r(xbar_r, frozen=freeze_xbar_r(xbar_r))["ucl_x"] == freeze_xbar_r(xbar_r)["ucl_x"]
assert compute_xbar_s(xbar_s, frozen=freeze_xbar_s(xbar_s))["ucl_x"] == freeze_xbar_s(xbar_s)["ucl_x"]
print("CYCLE_OK")
"""


@pytest.mark.parametrize(
    ("first", "second"),
    [("control_charts", "phase"), ("phase", "control_charts")],
)
def test_both_import_orders_work_and_frozen_paths_run(first, second):
    """§8.6: the lazy `_require_frozen` import is what keeps the cycle breakable.

    Run in a FRESH interpreter, because the in-process module cache would hide the
    cycle entirely — by the time this test file runs, both modules are long imported.
    `phase` imports `compute_*` at module level; promoting `control_charts`' lazy
    `from ...phase import _require_frozen` to module level makes one of these two
    orders an ImportError, and exercising `frozen=` proves the lazy import resolves
    at runtime rather than merely parsing.
    """
    script = _CYCLE_PROBE.format(first=first, second=second)
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )

    assert completed.returncode == 0, completed.stderr
    assert "CYCLE_OK" in completed.stdout


def test_importing_the_spc_package_alone_works_in_a_fresh_interpreter():
    """`import quality_core.spc` triggers the `__init__` re-export of both cycle halves."""
    completed = subprocess.run(
        [sys.executable, "-c", "import quality_core.spc; print(quality_core.spc.imr_limits)"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "imr_limits" in completed.stdout
