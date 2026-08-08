import math

import pytest
from quality_core.spc.constants import EWMA_DEFAULT_L, EWMA_DEFAULT_LAMBDA, EWMA_L_BY_LAMBDA
from quality_core.spc.control_charts import compute_ewma

EWMA_RESULT_KEYS = {
    "values",
    "z",
    "ucl",
    "lcl",
    "signals",
    "mu0",
    "sigma",
    "lam",
    "L",
    "pairing_adequate",
    "pairing_note",
}

VALUES = [11.0, 9.5, 10.2, 10.8, 9.9]
MU0 = 10.0
SIGMA = 1.0


# ---------------------------------------------------------------------------
# 1: key-set check
# ---------------------------------------------------------------------------


def test_compute_ewma_returns_expected_keys():
    result = compute_ewma(VALUES, MU0, SIGMA)
    assert set(result.keys()) == EWMA_RESULT_KEYS


# ---------------------------------------------------------------------------
# 2-3: recursion, z_0 == mu0-based (not x0-based)
# ---------------------------------------------------------------------------


def test_compute_ewma_recursion_hand_computed():
    x0, x1 = 11.0, 9.5
    result = compute_ewma([x0, x1, 10.2], mu0=MU0, sigma=SIGMA, lam=0.2)
    z0 = 0.2 * x0 + 0.8 * MU0
    z1 = 0.2 * x1 + 0.8 * z0
    assert result["z"][0] == pytest.approx(z0)
    assert result["z"][1] == pytest.approx(z1)


def test_compute_ewma_z0_uses_mu0_not_x0():
    x0 = 11.0
    result = compute_ewma([x0, 9.5], mu0=MU0, sigma=SIGMA, lam=0.2)
    assert result["z"][0] == pytest.approx(0.2 * x0 + 0.8 * MU0)
    assert result["z"][0] != pytest.approx(0.2 * x0 + 0.8 * x0)


# ---------------------------------------------------------------------------
# 4-5: time-varying limits widen, asymptote reached
# ---------------------------------------------------------------------------


def test_compute_ewma_limits_strictly_widen_below_asymptote():
    values = [10.0 + (i % 3) for i in range(20)]
    result = compute_ewma(values, mu0=MU0, sigma=SIGMA, lam=0.2, L=3.0)
    ucl = result["ucl"]
    lcl = result["lcl"]
    asymptote = MU0 + 3.0 * SIGMA * math.sqrt(0.2 / (2 - 0.2))

    assert ucl[0] < ucl[-1]
    assert all(ucl[i] < ucl[i + 1] for i in range(len(ucl) - 1))
    assert all(lcl[i] > lcl[i + 1] for i in range(len(lcl) - 1))
    assert all(u < asymptote for u in ucl)


def test_compute_ewma_asymptote_reached_for_large_n():
    values = [10.0] * 60
    result = compute_ewma(values, mu0=MU0, sigma=SIGMA, lam=0.2, L=3.0)
    asymptote = MU0 + 3.0 * SIGMA * math.sqrt(0.2 / (2 - 0.2))
    assert result["ucl"][-1] == pytest.approx(asymptote, rel=1e-3)


# ---------------------------------------------------------------------------
# 6: symmetry
# ---------------------------------------------------------------------------


def test_compute_ewma_limits_symmetric_about_mu0():
    result = compute_ewma(VALUES, mu0=MU0, sigma=SIGMA, lam=0.2, L=3.0)
    for ucl_i, lcl_i in zip(result["ucl"], result["lcl"]):
        assert ucl_i - MU0 == pytest.approx(MU0 - lcl_i)


# ---------------------------------------------------------------------------
# 7: known-shift signal
# ---------------------------------------------------------------------------


def test_compute_ewma_known_shift_signals_only_in_shifted_region():
    k = 15
    in_control = [MU0] * k
    shifted = [MU0 + 1.5 * SIGMA] * 15
    values = in_control + shifted
    result = compute_ewma(values, mu0=MU0, sigma=SIGMA, lam=0.2, L=3.0)

    assert result["signals"] != []
    assert all(i >= k for i in result["signals"])
    # z must actually drift above ucl somewhere in the shifted region.
    assert any(
        result["z"][i] > result["ucl"][i] for i in range(k, len(values))
    )


# ---------------------------------------------------------------------------
# 8: sigma independent of z-series
# ---------------------------------------------------------------------------


def test_compute_ewma_z_independent_of_sigma():
    result_a = compute_ewma(VALUES, mu0=MU0, sigma=1.0, lam=0.2)
    result_b = compute_ewma(VALUES, mu0=MU0, sigma=5.0, lam=0.2)
    assert result_a["z"] == pytest.approx(result_b["z"])
    assert result_a["ucl"] != pytest.approx(result_b["ucl"])


# ---------------------------------------------------------------------------
# 9-10: defaults / custom lam,L echoed
# ---------------------------------------------------------------------------


def test_compute_ewma_defaults_echoed():
    result = compute_ewma(VALUES, mu0=MU0, sigma=SIGMA)
    assert result["lam"] == pytest.approx(EWMA_DEFAULT_LAMBDA)
    assert result["L"] == pytest.approx(EWMA_DEFAULT_L)


def test_compute_ewma_custom_lam_l_echoed():
    result = compute_ewma(VALUES, mu0=MU0, sigma=SIGMA, lam=0.4, L=3.054)
    assert result["lam"] == pytest.approx(0.4)
    assert result["L"] == pytest.approx(3.054)


# ---------------------------------------------------------------------------
# 11: lam == 1 collapses to Shewhart
# ---------------------------------------------------------------------------


def test_compute_ewma_lam_one_collapses_to_shewhart():
    result = compute_ewma(VALUES, mu0=MU0, sigma=SIGMA, lam=1.0, L=3.0)
    assert result["z"] == pytest.approx(VALUES)
    assert result["ucl"] == pytest.approx([MU0 + 3.0 * SIGMA] * len(VALUES))
    assert result["lcl"] == pytest.approx([MU0 - 3.0 * SIGMA] * len(VALUES))


# ---------------------------------------------------------------------------
# 12: validation errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"values": [], "mu0": MU0, "sigma": SIGMA},
        {"values": [[1.0, 2.0], [3.0, 4.0]], "mu0": MU0, "sigma": SIGMA},
        {"values": VALUES, "mu0": MU0, "sigma": 0},
        {"values": VALUES, "mu0": MU0, "sigma": -1.0},
        {"values": VALUES, "mu0": MU0, "sigma": SIGMA, "lam": 0},
        {"values": VALUES, "mu0": MU0, "sigma": SIGMA, "lam": 1.5},
        {"values": VALUES, "mu0": MU0, "sigma": SIGMA, "L": 0},
    ],
)
def test_compute_ewma_validation_raises(kwargs):
    with pytest.raises(ValueError):
        compute_ewma(**kwargs)


def test_compute_ewma_single_value_does_not_raise():
    result = compute_ewma([11.0], mu0=MU0, sigma=SIGMA)
    assert len(result["z"]) == 1


# ---------------------------------------------------------------------------
# 13: on-target -> no signals
# ---------------------------------------------------------------------------


def test_compute_ewma_on_target_has_no_signals():
    result = compute_ewma([MU0] * 10, mu0=MU0, sigma=SIGMA)
    assert result["signals"] == []


# ---------------------------------------------------------------------------
# 14: constant table guard
# ---------------------------------------------------------------------------


def test_ewma_l_by_lambda_table_matches_expected_pairings():
    assert EWMA_L_BY_LAMBDA == {
        0.05: 2.615,
        0.10: 2.703,
        0.20: 2.860,
        0.25: 2.898,
        0.40: 3.054,
    }
    assert EWMA_DEFAULT_LAMBDA == 0.20
    assert EWMA_DEFAULT_L == 2.860


# ---------------------------------------------------------------------------
# Soft-warn pairing field (SME resolution #2) -- three branches.
# ---------------------------------------------------------------------------


def test_compute_ewma_pairing_adequate_when_tabulated_lam_matches_l():
    result = compute_ewma(VALUES, mu0=MU0, sigma=SIGMA, lam=0.20, L=2.860)
    assert result["pairing_adequate"] is True
    assert result["pairing_note"] == ""


def test_compute_ewma_pairing_inadequate_when_tabulated_lam_l_mismatch():
    result = compute_ewma(VALUES, mu0=MU0, sigma=SIGMA, lam=0.05, L=3.0)
    assert result["pairing_adequate"] is False
    assert result["pairing_note"] != ""


def test_compute_ewma_pairing_adequate_when_lam_untabulated():
    result = compute_ewma(VALUES, mu0=MU0, sigma=SIGMA, lam=0.15, L=3.0)
    assert result["pairing_adequate"] is True
    assert result["pairing_note"] == ""
