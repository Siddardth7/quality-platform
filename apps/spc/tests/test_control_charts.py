import math

import pytest

from src.spc_engine.control_charts import (
    compute_c,
    compute_imr,
    compute_p,
    compute_u,
    compute_xbar_r,
    compute_xbar_s,
)


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
