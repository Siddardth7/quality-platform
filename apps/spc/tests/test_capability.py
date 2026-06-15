import numpy as np
import pytest

from spc_app.spc_engine.capability import compute_capability, normality_test


DATA = np.array([9.9, 10.0, 10.1, 10.0, 10.2])
SIGMA_HAT = 0.1
LSL = 9.5
USL = 10.5


def test_compute_capability_returns_expected_keys():
    result = compute_capability(DATA, lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT)
    expected = {"cp", "cpk", "pp", "ppk", "mean", "sigma_hat", "sigma_overall"}
    assert expected.issubset(result.keys())


def test_compute_capability_cp_formula():
    result = compute_capability(DATA, lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT)
    np.testing.assert_allclose(result["cp"], (USL - LSL) / (6 * SIGMA_HAT), rtol=1e-4)


def test_compute_capability_cpk_formula():
    result = compute_capability(DATA, lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT)
    mean = DATA.mean()
    expected = min((USL - mean) / (3 * SIGMA_HAT), (mean - LSL) / (3 * SIGMA_HAT))
    np.testing.assert_allclose(result["cpk"], expected, rtol=1e-4)


def test_compute_capability_cpk_negative_when_mean_outside_spec():
    data = np.array([10.9, 11.0, 11.1])
    result = compute_capability(data, lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT)
    assert result["cpk"] < 0


def test_compute_capability_pp_formula():
    result = compute_capability(DATA, lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT)
    sigma_overall = np.std(DATA, ddof=1)
    expected = (USL - LSL) / (6 * sigma_overall)
    np.testing.assert_allclose(result["pp"], expected, rtol=1e-4)


def test_compute_capability_ppk_formula():
    result = compute_capability(DATA, lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT)
    sigma_overall = np.std(DATA, ddof=1)
    mean = DATA.mean()
    expected = min((USL - mean) / (3 * sigma_overall), (mean - LSL) / (3 * sigma_overall))
    np.testing.assert_allclose(result["ppk"], expected, rtol=1e-4)


def test_compute_capability_usl_only():
    result = compute_capability(DATA, lsl=None, usl=USL, sigma_hat=SIGMA_HAT)
    mean = DATA.mean()
    assert result["cp"] is None
    np.testing.assert_allclose(result["cpk"], (USL - mean) / (3 * SIGMA_HAT), rtol=1e-4)


def test_compute_capability_lsl_only():
    result = compute_capability(DATA, lsl=LSL, usl=None, sigma_hat=SIGMA_HAT)
    mean = DATA.mean()
    assert result["cp"] is None
    np.testing.assert_allclose(result["cpk"], (mean - LSL) / (3 * SIGMA_HAT), rtol=1e-4)


def test_compute_capability_sigma_overall_uses_sample_std():
    result = compute_capability(DATA, lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT)
    np.testing.assert_allclose(result["sigma_overall"], np.std(DATA, ddof=1), rtol=1e-4)


def test_compute_capability_preserves_sigma_hat():
    result = compute_capability(DATA, lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT)
    assert result["sigma_hat"] == SIGMA_HAT


def test_normality_test_returns_expected_keys():
    result = normality_test(DATA)
    expected = {"w_stat", "p_value", "is_normal"}
    assert expected.issubset(result.keys())


def test_normality_test_reports_normal_for_normal_data():
    rng = np.random.default_rng(42)
    data = rng.normal(loc=0.0, scale=1.0, size=200)
    result = normality_test(data)
    assert result["p_value"] > 0.05
    assert result["is_normal"] is True


def test_compute_capability_pp_none_for_unilateral_spec():
    result = compute_capability(DATA, lsl=None, usl=USL, sigma_hat=SIGMA_HAT)
    assert result["pp"] is None
    assert result["ppk"] is not None


def test_compute_capability_no_spec_limits_all_indices_none():
    data = np.array([10.0, 10.1, 9.9, 10.2, 10.0])
    result = compute_capability(data, lsl=None, usl=None, sigma_hat=0.1)
    assert result["cp"] is None
    assert result["cpk"] is None
    assert result["pp"] is None
    assert result["ppk"] is None
    assert result["mean"] == pytest.approx(data.mean(), rel=1e-4)
    assert result["sigma_hat"] == pytest.approx(0.1)
