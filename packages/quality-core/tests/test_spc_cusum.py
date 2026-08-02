import pytest
from quality_core.spc.constants import CUSUM_DEFAULT_H, CUSUM_DEFAULT_K, CUSUM_FIR_FRACTION
from quality_core.spc.control_charts import compute_cusum

CUSUM_RESULT_KEYS = {
    "values",
    "z",
    "c_plus",
    "c_minus",
    "signals",
    "n_plus",
    "n_minus",
    "mu0",
    "sigma",
    "k",
    "h",
    "fir",
}

MU0 = 10.0
SIGMA = 1.0
K = 0.5
H = 5.0


# ---------------------------------------------------------------------------
# 1: key-set check
# ---------------------------------------------------------------------------


def test_compute_cusum_returns_expected_keys():
    result = compute_cusum([11.0, 9.5, 10.2], MU0, SIGMA)
    assert set(result.keys()) == CUSUM_RESULT_KEYS


# ---------------------------------------------------------------------------
# 2: recursion, hand-computed
# ---------------------------------------------------------------------------


def test_compute_cusum_recursion_hand_computed():
    x0, x1 = 11.0, 9.5
    result = compute_cusum([x0, x1, 10.2], mu0=MU0, sigma=SIGMA, k=K, h=H, fir=False)
    z0 = (x0 - MU0) / SIGMA
    z1 = (x1 - MU0) / SIGMA
    c_plus0 = max(0.0, z0 - K)
    c_minus0 = max(0.0, -z0 - K)
    c_plus1 = max(0.0, z1 - K + c_plus0)
    c_minus1 = max(0.0, -z1 - K + c_minus0)

    assert result["c_plus"][0] == pytest.approx(c_plus0)
    assert result["c_minus"][0] == pytest.approx(c_minus0)
    assert result["c_plus"][1] == pytest.approx(c_plus1)
    assert result["c_minus"][1] == pytest.approx(c_minus1)


# ---------------------------------------------------------------------------
# 3: standardization
# ---------------------------------------------------------------------------


def test_compute_cusum_standardization():
    values = [11.0, 9.5, 10.2, 10.8, 9.9]
    result = compute_cusum(values, mu0=MU0, sigma=SIGMA)
    for x_i, z_i in zip(values, result["z"]):
        assert z_i == pytest.approx((x_i - MU0) / SIGMA)


# ---------------------------------------------------------------------------
# 4: max(0, ...) reset barrier
# ---------------------------------------------------------------------------


def test_compute_cusum_reset_barrier_clamps_to_exactly_zero():
    # Drive c_plus up for three points, then a strong opposite deviation.
    values = [MU0 + 3.0, MU0 + 3.0, MU0 + 3.0, MU0 - 10.0]
    result = compute_cusum(values, mu0=MU0, sigma=SIGMA, k=K, h=H, fir=False)

    assert result["c_plus"][2] > 0.0
    assert result["c_plus"][3] == 0.0
    assert result["c_plus"][3] >= 0.0


# ---------------------------------------------------------------------------
# 5: C- positive-accumulator convention
# ---------------------------------------------------------------------------


def test_compute_cusum_c_minus_is_positive_accumulator_for_downward_shift():
    values = [MU0 - 2.0] * 10
    result = compute_cusum(values, mu0=MU0, sigma=SIGMA, k=K, h=H, fir=False)

    assert all(c >= 0.0 for c in result["c_minus"])
    assert result["c_plus"] == pytest.approx([0.0] * 10)
    assert result["c_minus"][-1] > H


# ---------------------------------------------------------------------------
# 6-7: known-shift signal detection on both arms
# ---------------------------------------------------------------------------


def test_compute_cusum_known_upward_shift_signals_upper_arm():
    k_len = 5
    values = ([MU0] * k_len) + ([MU0 + 1.0 * SIGMA] * 15)
    result = compute_cusum(values, mu0=MU0, sigma=SIGMA, k=K, h=H)

    assert result["signals"] != []
    assert all(i >= k_len for i in result["signals"])
    for i in result["signals"]:
        assert result["c_plus"][i] > H


def test_compute_cusum_known_downward_shift_signals_lower_arm():
    k_len = 5
    values = ([MU0] * k_len) + ([MU0 - 1.0 * SIGMA] * 15)
    result = compute_cusum(values, mu0=MU0, sigma=SIGMA, k=K, h=H)

    assert result["signals"] != []
    assert all(i >= k_len for i in result["signals"])
    for i in result["signals"]:
        assert result["c_minus"][i] > H


# ---------------------------------------------------------------------------
# 8: FIR head-start seeding
# ---------------------------------------------------------------------------


def test_compute_cusum_fir_seeds_both_arms_with_head_start():
    values = [MU0] * 5
    result = compute_cusum(values, mu0=MU0, sigma=SIGMA, k=K, h=H, fir=True)
    z0 = (values[0] - MU0) / SIGMA
    seed = CUSUM_FIR_FRACTION * H

    assert result["c_plus"][0] == pytest.approx(max(0.0, z0 - K + seed))
    assert result["c_minus"][0] == pytest.approx(max(0.0, -z0 - K + seed))
    assert result["c_plus"][0] == pytest.approx(2.0)
    assert result["c_minus"][0] == pytest.approx(2.0)


def test_compute_cusum_fir_first_accumulators_exceed_non_fir_on_same_data():
    values = [MU0] * 5
    fir_result = compute_cusum(values, mu0=MU0, sigma=SIGMA, k=K, h=H, fir=True)
    no_fir_result = compute_cusum(values, mu0=MU0, sigma=SIGMA, k=K, h=H, fir=False)

    assert fir_result["c_plus"][0] > no_fir_result["c_plus"][0]
    assert fir_result["c_minus"][0] > no_fir_result["c_minus"][0]


# ---------------------------------------------------------------------------
# 9: FIR decay
# ---------------------------------------------------------------------------


def test_compute_cusum_fir_decays_to_zero_on_on_target_data():
    values = [MU0] * 6
    result = compute_cusum(values, mu0=MU0, sigma=SIGMA, k=K, h=H, fir=True)

    assert result["c_plus"][0] > 0.0
    assert result["c_plus"][4] == pytest.approx(0.0)
    assert result["c_minus"][4] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 10: onset run-length counters
# ---------------------------------------------------------------------------


def test_compute_cusum_run_length_counts_consecutive_periods_since_reset():
    # Small clean shift case, hand-checked.
    k_len = 3
    values = ([MU0] * k_len) + ([MU0 + 3.0 * SIGMA] * 3)
    result = compute_cusum(values, mu0=MU0, sigma=SIGMA, k=K, h=H, fir=False)

    # In-control region: c_plus stays clamped at 0, counter stays 0.
    assert result["n_plus"][:k_len] == [0, 0, 0]
    # Shift region: consecutive periods since the arm rose above 0.
    assert result["n_plus"][k_len] == 1
    assert result["n_plus"][k_len + 1] == 2
    assert result["n_plus"][k_len + 2] == 3
    assert result["c_plus"][k_len + 2] > H
    assert (k_len + 2) in result["signals"]


def test_compute_cusum_run_length_resets_to_zero_with_its_arm():
    values = [MU0 + 3.0, MU0 + 3.0, MU0 + 3.0, MU0 - 10.0]
    result = compute_cusum(values, mu0=MU0, sigma=SIGMA, k=K, h=H, fir=False)

    assert result["n_plus"][2] == 3
    assert result["n_plus"][3] == 0


# ---------------------------------------------------------------------------
# 11: on-target -> no signals
# ---------------------------------------------------------------------------


def test_compute_cusum_on_target_has_no_signals():
    result = compute_cusum([MU0] * 10, mu0=MU0, sigma=SIGMA)
    assert result["signals"] == []


# ---------------------------------------------------------------------------
# 12: params echoed
# ---------------------------------------------------------------------------


def test_compute_cusum_defaults_echoed():
    result = compute_cusum([MU0] * 5, mu0=MU0, sigma=SIGMA)
    assert result["k"] == pytest.approx(CUSUM_DEFAULT_K)
    assert result["h"] == pytest.approx(CUSUM_DEFAULT_H)
    assert result["fir"] is False


def test_compute_cusum_custom_params_echoed():
    result = compute_cusum([MU0] * 5, mu0=MU0, sigma=SIGMA, k=0.75, h=4.0, fir=True)
    assert result["k"] == pytest.approx(0.75)
    assert result["h"] == pytest.approx(4.0)
    assert result["fir"] is True


# ---------------------------------------------------------------------------
# 13: validation errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"values": [], "mu0": MU0, "sigma": SIGMA},
        {"values": [[1.0, 2.0], [3.0, 4.0]], "mu0": MU0, "sigma": SIGMA},
        {"values": [MU0, MU0 + 1.0], "mu0": MU0, "sigma": 0},
        {"values": [MU0, MU0 + 1.0], "mu0": MU0, "sigma": -1.0},
        {"values": [MU0, MU0 + 1.0], "mu0": MU0, "sigma": SIGMA, "k": 0},
        {"values": [MU0, MU0 + 1.0], "mu0": MU0, "sigma": SIGMA, "h": 0},
    ],
)
def test_compute_cusum_validation_raises(kwargs):
    with pytest.raises(ValueError):
        compute_cusum(**kwargs)


def test_compute_cusum_single_value_does_not_raise():
    result = compute_cusum([11.0], mu0=MU0, sigma=SIGMA)
    assert len(result["c_plus"]) == 1
    assert len(result["c_minus"]) == 1


# ---------------------------------------------------------------------------
# 14: constants guard
# ---------------------------------------------------------------------------


def test_cusum_constants_match_expected_values():
    assert CUSUM_DEFAULT_K == 0.5
    assert CUSUM_DEFAULT_H == 5.0
    assert CUSUM_FIR_FRACTION == 0.5
