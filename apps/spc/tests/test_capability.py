import math

import numpy as np
import pytest
from scipy import special, stats
from scipy.stats import chi2, norm

import spc_app.spc_engine.capability as capability
from spc_app.spc_engine.capability import (
    _bootstrap_percentile_ci,
    _fit_percentile_capability,
    compute_capability,
    compute_capability_study,
    normality_test,
)

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


def test_compute_capability_too_few_points_raises():
    with pytest.raises(ValueError):
        compute_capability(np.array([10.0]), lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT)


def test_compute_capability_nonpositive_sigma_hat_raises():
    with pytest.raises(ValueError):
        compute_capability(DATA, lsl=LSL, usl=USL, sigma_hat=0.0)


def test_normality_test_too_few_points_raises():
    with pytest.raises(ValueError):
        normality_test(np.array([10.0, 10.1]))


# ---------------------------------------------------------------------------
# W10-4: compute_capability new CI fields (T8, T9, T11)
# ---------------------------------------------------------------------------

CI_DATA = np.random.default_rng(42).normal(loc=10.0, scale=0.5, size=30)
CI_SIGMA_HAT = 0.5
CI_LSL = 8.0
CI_USL = 12.0


def test_compute_capability_cp_chi2_ci_hand_checked():
    # T8 — hand-check against known chi2 quantiles at n=30, alpha=0.05.
    result = compute_capability(CI_DATA, lsl=CI_LSL, usl=CI_USL, sigma_hat=CI_SIGMA_HAT)
    f_lo = (chi2.ppf(0.025, 29) / 29) ** 0.5
    f_hi = (chi2.ppf(0.975, 29) / 29) ** 0.5
    assert f_lo == pytest.approx(0.7438, rel=1e-3)
    assert f_hi == pytest.approx(1.2557, rel=1e-3)
    cp = result["cp"]
    lo, hi = result["cp_ci"]
    assert lo == pytest.approx(cp * f_lo, rel=1e-4)
    assert hi == pytest.approx(cp * f_hi, rel=1e-4)
    assert lo < cp < hi


def test_compute_capability_cpk_bissell_ci_recompute_match():
    # T9 — recompute-match against the Bissell (1990) large-sample variance formula.
    result = compute_capability(CI_DATA, lsl=CI_LSL, usl=CI_USL, sigma_hat=CI_SIGMA_HAT)
    n = result["n"]
    cpk = result["cpk"]
    se = (1.0 / (9.0 * n) + cpk**2 / (2.0 * (n - 1))) ** 0.5
    z_two = norm.ppf(0.975)
    z_one = norm.ppf(0.95)
    lo, hi = result["cpk_ci"]
    assert lo == pytest.approx(cpk - z_two * se, rel=1e-4)
    assert hi == pytest.approx(cpk + z_two * se, rel=1e-4)
    assert result["cpk_lower"] == pytest.approx(cpk - z_one * se, rel=1e-4)
    assert result["cpk_lower"] < cpk


def test_compute_capability_new_keys_present():
    result = compute_capability(DATA, lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT)
    assert {"n", "alpha", "cp_ci", "cpk_ci", "cpk_lower"}.issubset(result.keys())
    assert result["n"] == len(DATA)
    assert result["alpha"] == pytest.approx(0.05)


def test_compute_capability_usl_only_ci_none_branches():
    # T11 — one-sided spec: cp/cp_ci None, cpk/cpk_ci present.
    result = compute_capability(DATA, lsl=None, usl=USL, sigma_hat=SIGMA_HAT)
    assert result["cp_ci"] is None
    assert result["cpk_ci"] is not None
    assert result["cpk_lower"] is not None


def test_compute_capability_lsl_only_ci_none_branches():
    result = compute_capability(DATA, lsl=LSL, usl=None, sigma_hat=SIGMA_HAT)
    assert result["cp_ci"] is None
    assert result["cpk_ci"] is not None


def test_compute_capability_no_spec_limits_all_cis_none():
    result = compute_capability(DATA, lsl=None, usl=None, sigma_hat=SIGMA_HAT)
    assert result["cp_ci"] is None
    assert result["cpk_ci"] is None
    assert result["cpk_lower"] is None


def test_compute_capability_alpha_out_of_range_raises():
    with pytest.raises(ValueError):
        compute_capability(DATA, lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT, alpha=1.5)
    with pytest.raises(ValueError):
        compute_capability(DATA, lsl=LSL, usl=USL, sigma_hat=SIGMA_HAT, alpha=0.0)


# ---------------------------------------------------------------------------
# W10-4: compute_capability_study — non-normal capability (Box-Cox / Yeo-Johnson /
# fitted-percentile) + orchestrator-level CIs.
# ---------------------------------------------------------------------------

STUDY_ALPHA = 0.05


def _lognormal_individuals(seed: int, sigma: float, size: int) -> np.ndarray:
    return np.random.default_rng(seed).lognormal(mean=0.0, sigma=sigma, size=size)


def _bimodal_data() -> np.ndarray:
    rng = np.random.default_rng(3)
    cluster1 = rng.normal(2.0, 0.2, 40)
    cluster2 = rng.normal(8.0, 0.2, 40)
    return np.concatenate([cluster1, cluster2])


def _nonpositive_data() -> np.ndarray:
    return np.random.default_rng(109).gamma(shape=3.0, scale=1.0, size=60) - 5.0


# --- T1 / T1b — Box-Cox round trip, individuals vs subgroups (Decision 1) ---


def test_compute_capability_study_boxcox_individuals_round_trip():
    data = _lognormal_individuals(seed=1, sigma=0.6, size=60)
    lsl, usl = 0.1, 3.0
    study = compute_capability_study(data, lsl=lsl, usl=usl, alpha=STUDY_ALPHA)

    assert study["method"] == "boxcox"
    assert study["subgroup_size"] == 1
    assert study["shift"] == pytest.approx(0.0)

    lam_used = study["lambda_used"]
    lsl_t = special.boxcox(lsl, lam_used)
    usl_t = special.boxcox(usl, lam_used)
    expected_cp = (usl_t - lsl_t) / (6.0 * study["sigma_hat"])
    assert study["cp"] == pytest.approx(expected_cp, rel=1e-6)


def test_compute_capability_study_subgrouped_within_sigma_branch():
    # T1b — 2D subgroups (n=5); covers the compute_xbar_r branch of _within_sigma.
    data = _lognormal_individuals(seed=2, sigma=0.6, size=150).reshape(30, 5)
    study = compute_capability_study(data, lsl=0.1, usl=3.0, alpha=STUDY_ALPHA)

    assert study["method"] == "boxcox"
    assert study["subgroup_size"] == 5
    assert study["cp"] is not None


# --- T2 — lambda < 0 ordering preservation, no swap branch (Decision 5) ---


def test_compute_capability_study_negative_lambda_preserves_ordering():
    rng = np.random.default_rng(1)
    data = 1.0 / rng.gamma(shape=2.0, scale=1.0, size=80) + 0.01
    study = compute_capability_study(data, lsl=0.1, usl=5.0, alpha=STUDY_ALPHA)

    assert study["method"] == "boxcox"
    assert study["lambda_used"] < 0.0
    assert study["cp"] is not None
    assert study["cp"] > 0.0
    assert study["cpk"] is not None
    assert study["cpk"] > 0.0


# --- T3 / T4 — non-positive data: Yeo-Johnson default vs shift opt-in (Decision 2) ---


def test_compute_capability_study_nonpositive_defaults_to_yeojohnson():
    data = _nonpositive_data()
    study = compute_capability_study(data, lsl=-8.0, usl=0.0, alpha=STUDY_ALPHA)

    assert study["method"] == "yeojohnson"
    assert study["shift"] == pytest.approx(0.0)
    assert study["cp"] is not None and math.isfinite(study["cp"])
    assert study["cpk"] is not None and math.isfinite(study["cpk"])


def test_compute_capability_study_nonpositive_opt_out_uses_shift():
    data = _nonpositive_data()
    study = compute_capability_study(
        data, lsl=-8.0, usl=0.0, alpha=STUDY_ALPHA, allow_yeojohnson=False
    )

    assert study["method"] == "boxcox"
    assert study["shift"] == pytest.approx(1.0 - float(data.min()))


# --- T5 — fitted-percentile fallback (Decision 3) ---


def test_compute_capability_study_percentile_fallback_on_bimodal_data(monkeypatch):
    monkeypatch.setattr(capability, "BOOTSTRAP_RESAMPLES", 50)
    data = _bimodal_data()
    lsl, usl = 1.0, 9.0
    study = compute_capability_study(data, lsl=lsl, usl=usl, alpha=STUDY_ALPHA)

    assert study["method"] == "percentile"
    assert study["normal_after"] is False
    assert study["fitted_dist"] in ("lognorm", "weibull_min", "gamma", "johnsonsu")
    assert study["pp"] is None
    assert study["ppk"] is None

    dist = getattr(stats, study["fitted_dist"])
    params = dist.fit(data)
    p_lo = dist.ppf(0.00135, *params)
    p_hi = dist.ppf(0.99865, *params)
    expected_cp = (usl - lsl) / (p_hi - p_lo)
    assert study["cp"] == pytest.approx(expected_cp, rel=1e-3)


# --- T5b — AIC selection + per-candidate fit-skip branch ---


def test_fit_percentile_capability_selects_min_aic_family():
    data = np.random.default_rng(5).gamma(shape=2.0, scale=1.0, size=100)
    _, _, fitted_dist = _fit_percentile_capability(data, lsl=0.1, usl=8.0)
    assert fitted_dist == "gamma"


def test_fit_percentile_capability_skips_failed_candidate(monkeypatch):
    data = np.random.default_rng(5).gamma(shape=2.0, scale=1.0, size=100)

    def _failing_fit(*args, **kwargs):
        raise RuntimeError("forced fit failure")

    monkeypatch.setattr(stats.gamma, "fit", _failing_fit)
    _, _, fitted_dist = _fit_percentile_capability(data, lsl=0.1, usl=8.0)

    assert fitted_dist != "gamma"
    assert fitted_dist in ("lognorm", "weibull_min", "johnsonsu")


# --- T5c — all candidates fail -> empirical np.quantile fallback (E11) ---


def test_fit_percentile_capability_all_candidates_fail_uses_empirical_fallback(monkeypatch):
    data = np.random.default_rng(5).gamma(shape=2.0, scale=1.0, size=100)

    def _failing_fit(*args, **kwargs):
        raise RuntimeError("forced fit failure")

    for name in ("lognorm", "weibull_min", "gamma", "johnsonsu"):
        monkeypatch.setattr(getattr(stats, name), "fit", _failing_fit)

    cp, cpk, fitted_dist = _fit_percentile_capability(data, lsl=0.1, usl=8.0)

    assert fitted_dist is None
    expected_cp = (8.0 - 0.1) / (
        np.quantile(data, 0.99865) - np.quantile(data, 0.00135)
    )
    assert cp == pytest.approx(expected_cp, rel=1e-6)
    assert cpk is not None


# --- T6 / T7 — rounded-lambda snap in vs out of the likelihood CI (E4) ---


def test_compute_capability_study_rounded_lambda_snaps_when_inside_ci():
    data = _lognormal_individuals(seed=9, sigma=0.6, size=150)
    study = compute_capability_study(data, lsl=0.1, usl=3.0, alpha=STUDY_ALPHA)

    assert study["method"] == "boxcox"
    assert study["lambda_ci"] is not None
    assert study["lambda_ci"][0] <= 0.0 <= study["lambda_ci"][1]
    assert study["lambda_used"] == pytest.approx(0.0)
    assert study["lambda_used"] != pytest.approx(study["lambda_mle"])


def test_compute_capability_study_rounded_lambda_kept_when_outside_ci():
    data = _lognormal_individuals(seed=12, sigma=0.35, size=400)
    study = compute_capability_study(data, lsl=0.2, usl=4.0, alpha=STUDY_ALPHA)

    assert study["method"] == "boxcox"
    lam_ci = study["lambda_ci"]
    candidates = (-1.0, -0.5, 0.0, 0.5, 1.0, 2.0)
    nearest = min(candidates, key=lambda c: abs(c - study["lambda_mle"]))
    assert not (lam_ci[0] <= nearest <= lam_ci[1])
    assert study["lambda_used"] == pytest.approx(study["lambda_mle"])


# --- T10 — bootstrap determinism + reproducibility (percentile path) ---


def test_bootstrap_percentile_ci_deterministic_with_fixed_seed(monkeypatch):
    # Fast: monkeypatched down from the production BOOTSTRAP_RESAMPLES=2000. Coverage of
    # the branch structure doesn't depend on resample count; bit-reproducibility does depend
    # on the fixed seed, which is exercised here too (small count, same seed twice).
    monkeypatch.setattr(capability, "BOOTSTRAP_RESAMPLES", 50)
    data = _bimodal_data()
    cp_ci_a, cpk_ci_a = _bootstrap_percentile_ci(data, lsl=1.0, usl=9.0, alpha=0.05)
    cp_ci_b, cpk_ci_b = _bootstrap_percentile_ci(data, lsl=1.0, usl=9.0, alpha=0.05)

    assert cp_ci_a == cp_ci_b
    assert cpk_ci_a == cpk_ci_b


def test_bootstrap_percentile_ci_different_seed_changes_result(monkeypatch):
    monkeypatch.setattr(capability, "BOOTSTRAP_RESAMPLES", 50)
    data = _bimodal_data()
    monkeypatch.setattr(capability, "BOOTSTRAP_SEED", 111)
    cp_ci_a, _ = _bootstrap_percentile_ci(data, lsl=1.0, usl=9.0, alpha=0.05)
    monkeypatch.setattr(capability, "BOOTSTRAP_SEED", 222)
    cp_ci_b, _ = _bootstrap_percentile_ci(data, lsl=1.0, usl=9.0, alpha=0.05)

    assert cp_ci_a != cp_ci_b


def test_bootstrap_percentile_ci_one_sided_spec_skips_missing_side(monkeypatch):
    # Covers the "point statistic is None" skip branch — only usl present -> cp_ci None.
    monkeypatch.setattr(capability, "BOOTSTRAP_RESAMPLES", 50)
    data = _bimodal_data()
    cp_ci, cpk_ci = _bootstrap_percentile_ci(data, lsl=None, usl=9.0, alpha=0.05)

    assert cp_ci is None
    assert cpk_ci is not None


def test_compute_capability_study_percentile_one_sided_spec(monkeypatch):
    monkeypatch.setattr(capability, "BOOTSTRAP_RESAMPLES", 50)
    data = _bimodal_data()
    study = compute_capability_study(data, lsl=None, usl=9.0, alpha=STUDY_ALPHA)

    assert study["method"] == "percentile"
    assert study["cp"] is None
    assert study["cp_ci"] is None
    assert study["cpk"] is not None
    assert study["cpk_ci"] is not None


def test_compute_capability_study_percentile_lsl_only_spec(monkeypatch):
    # Mirrors the usl-only case above but exercises the lsl-only branches: the transform's
    # lsl-only limit-mapping (E2) and _percentile_cpk's lsl-only ratio.
    monkeypatch.setattr(capability, "BOOTSTRAP_RESAMPLES", 50)
    data = _bimodal_data()
    study = compute_capability_study(data, lsl=1.0, usl=None, alpha=STUDY_ALPHA)

    assert study["method"] == "percentile"
    assert study["cp"] is None
    assert study["cp_ci"] is None
    assert study["cpk"] is not None
    assert study["cpk_ci"] is not None


def test_compute_capability_study_percentile_no_spec_limits(monkeypatch):
    # Covers the transform's no-spec branch (E2) and _percentile_cpk's None-return branch,
    # which in turn means both bootstrap CIs are skipped (cp_ci and cpk_ci both None).
    monkeypatch.setattr(capability, "BOOTSTRAP_RESAMPLES", 50)
    data = _bimodal_data()
    study = compute_capability_study(data, lsl=None, usl=None, alpha=STUDY_ALPHA)

    assert study["method"] == "percentile"
    assert study["cp"] is None
    assert study["cpk"] is None
    assert study["cp_ci"] is None
    assert study["cpk_ci"] is None


def test_bootstrap_percentile_ci_no_spec_limits_skips_both_sides(monkeypatch):
    monkeypatch.setattr(capability, "BOOTSTRAP_RESAMPLES", 50)
    data = _bimodal_data()
    cp_ci, cpk_ci = _bootstrap_percentile_ci(data, lsl=None, usl=None, alpha=0.05)
    assert cp_ci is None
    assert cpk_ci is None


def test_bootstrap_percentile_ci_reproducible_at_production_resample_count():
    # SLOW (~2-4 min real wall-clock): the ONE test at the real BOOTSTRAP_RESAMPLES=2000 —
    # proves the audit-critical bit-reproducibility guarantee at production settings. All
    # other percentile-path tests above monkeypatch the resample count down for speed.
    data = _bimodal_data()
    cp_ci_a, cpk_ci_a = _bootstrap_percentile_ci(data, lsl=1.0, usl=9.0, alpha=0.05)
    cp_ci_b, cpk_ci_b = _bootstrap_percentile_ci(data, lsl=1.0, usl=9.0, alpha=0.05)

    assert cp_ci_a == cp_ci_b
    assert cpk_ci_a == cpk_ci_b
    assert cp_ci_a[0] < cp_ci_a[1]


# --- T12 — within vs overall sigma preserved post-transform (E6) ---


def test_compute_capability_study_within_vs_overall_sigma_preserved():
    data = _lognormal_individuals(seed=1, sigma=0.6, size=60)
    study = compute_capability_study(data, lsl=0.1, usl=3.0, alpha=STUDY_ALPHA)

    assert study["sigma_hat"] != pytest.approx(study["sigma_overall"])
    assert study["cpk"] != pytest.approx(study["ppk"])


# --- T13 — method + fitted_dist recorded across all four methods ---


@pytest.mark.parametrize(
    "data, lsl, usl, kwargs, expected_method",
    [
        (np.random.default_rng(0).normal(10, 0.5, size=10), 8.0, 12.0, {}, "normal"),
        (_lognormal_individuals(seed=1, sigma=0.6, size=60), 0.1, 3.0, {}, "boxcox"),
        (_nonpositive_data(), -8.0, 0.0, {}, "yeojohnson"),
    ],
)
def test_compute_capability_study_method_recorded(data, lsl, usl, kwargs, expected_method):
    study = compute_capability_study(data, lsl=lsl, usl=usl, alpha=STUDY_ALPHA, **kwargs)
    assert study["method"] == expected_method
    assert study["fitted_dist"] is None


def test_compute_capability_study_percentile_method_records_fitted_dist(monkeypatch):
    monkeypatch.setattr(capability, "BOOTSTRAP_RESAMPLES", 50)
    study = compute_capability_study(_bimodal_data(), lsl=1.0, usl=9.0, alpha=STUDY_ALPHA)
    assert study["method"] == "percentile"
    assert study["fitted_dist"] is not None


# --- T14 — validation branches ---


def test_compute_capability_study_alpha_out_of_range_raises():
    with pytest.raises(ValueError):
        compute_capability_study(DATA, lsl=LSL, usl=USL, alpha=1.5)


def test_compute_capability_study_too_few_points_raises():
    with pytest.raises(ValueError):
        compute_capability_study([1.0, 2.0], lsl=LSL, usl=USL)


def test_compute_capability_study_invalid_ndim_raises():
    data = np.zeros((2, 3, 4))
    with pytest.raises(ValueError):
        compute_capability_study(data, lsl=LSL, usl=USL)


def test_compute_capability_study_invalid_subgroup_size_raises():
    data = np.random.default_rng(42).normal(10.0, 0.5, size=33).reshape(3, 11)
    with pytest.raises(ValueError):
        compute_capability_study(data, lsl=8.0, usl=12.0)


def test_compute_capability_study_constant_data_raises():
    with pytest.raises(ValueError):
        compute_capability_study(np.array([5.0] * 10), lsl=1.0, usl=9.0)


# --- T15 — small-n note ---


def test_compute_capability_study_small_n_note_present():
    data = np.random.default_rng(0).normal(10.0, 0.5, size=10)
    study = compute_capability_study(data, lsl=8.0, usl=12.0, alpha=STUDY_ALPHA)
    assert study["n"] < 30
    assert "n<30" in study["note"]


def test_compute_capability_study_no_small_n_note_when_n_at_least_30():
    study = compute_capability_study(CI_DATA, lsl=CI_LSL, usl=CI_USL, alpha=STUDY_ALPHA)
    assert study["n"] >= 30
    assert "n<30" not in study["note"]


# ---------------------------------------------------------------------------
# W10-5 (#145): force_method override (SME Q1) — 4 values x conditions.
# ---------------------------------------------------------------------------

NORMAL_DATA = np.random.default_rng(0).normal(10.0, 0.5, size=40)


def test_force_method_auto_is_unchanged_default_behaviour():
    # "auto" (the implicit default) is byte-for-byte the pre-existing gate logic.
    explicit = compute_capability_study(NORMAL_DATA, lsl=8.0, usl=12.0, alpha=STUDY_ALPHA, force_method="auto")
    implicit = compute_capability_study(NORMAL_DATA, lsl=8.0, usl=12.0, alpha=STUDY_ALPHA)
    assert explicit == implicit
    assert explicit["method"] == "normal"


def test_force_method_normal_on_already_normal_data():
    study = compute_capability_study(NORMAL_DATA, lsl=8.0, usl=12.0, alpha=STUDY_ALPHA, force_method="normal")
    assert study["method"] == "normal"
    assert study["normal_before"] is True
    assert "user-forced" in study["note"]
    assert study["cp"] is not None
    assert study["cp_ci"] is not None


def test_force_method_normal_skips_gate_on_non_normal_data():
    data = _bimodal_data()
    study = compute_capability_study(data, lsl=1.0, usl=9.0, alpha=STUDY_ALPHA, force_method="normal")
    assert study["method"] == "normal"
    assert study["normal_before"] is False
    assert "user-forced" in study["note"]
    assert study["cp"] is not None
    assert study["cp_ci"] is not None


def test_force_method_boxcox_on_data_that_already_passed_normal():
    # Forces the transform path even though normal_before is True; note records
    # the "forced despite already normal" prefix.
    data = _lognormal_individuals(seed=1, sigma=0.6, size=60)
    assert normality_test(data)["is_normal"] in (True, False)  # sanity, not asserted on
    study = compute_capability_study(data, lsl=0.1, usl=3.0, alpha=STUDY_ALPHA, force_method="boxcox")
    assert study["method"] in ("boxcox", "yeojohnson")
    assert study["lambda_used"] is not None


def test_force_method_boxcox_forced_note_when_raw_data_was_already_normal():
    data = NORMAL_DATA  # already positive + normal
    study = compute_capability_study(data, lsl=8.0, usl=12.0, alpha=STUDY_ALPHA, force_method="boxcox")
    assert study["method"] == "boxcox"
    assert "user-forced" in study["note"]
    assert "already" in study["note"] or "passing Shapiro-Wilk" in study["note"]


def test_force_method_boxcox_no_forced_note_when_raw_data_was_non_normal():
    data = _lognormal_individuals(seed=1, sigma=0.6, size=60)
    normal_before = normality_test(data)["is_normal"]
    study = compute_capability_study(data, lsl=0.1, usl=3.0, alpha=STUDY_ALPHA, force_method="boxcox")
    if not normal_before:
        assert "user-forced" not in study["note"]


def test_force_method_boxcox_honors_allow_yeojohnson_false_on_nonpositive_data():
    data = _nonpositive_data()
    study = compute_capability_study(
        data, lsl=-8.0, usl=0.0, alpha=STUDY_ALPHA, force_method="boxcox", allow_yeojohnson=False
    )
    assert study["method"] == "boxcox"
    assert study["shift"] == pytest.approx(1.0 - float(data.min()))


def test_force_method_boxcox_defaults_to_yeojohnson_on_nonpositive_data():
    data = _nonpositive_data()
    study = compute_capability_study(data, lsl=-8.0, usl=0.0, alpha=STUDY_ALPHA, force_method="boxcox")
    assert study["method"] == "yeojohnson"
    assert study["shift"] == pytest.approx(0.0)


def test_force_method_percentile_direct_call(monkeypatch):
    monkeypatch.setattr(capability, "BOOTSTRAP_RESAMPLES", 50)
    study = compute_capability_study(
        NORMAL_DATA, lsl=8.0, usl=12.0, alpha=STUDY_ALPHA, force_method="percentile"
    )
    assert study["method"] == "percentile"
    assert study["fitted_dist"] is not None
    assert study["lambda_used"] is None
    assert study["shift"] == pytest.approx(0.0)
    assert "user-forced to 'percentile'" in study["note"]
    assert study["cp_ci"] is not None
    assert study["cpk_ci"] is not None


def test_force_method_percentile_skips_normal_and_transform_paths(monkeypatch):
    # Even data that would normally take the "normal" path (already Gaussian) goes
    # straight to the fitted-distribution percentile method when forced.
    monkeypatch.setattr(capability, "BOOTSTRAP_RESAMPLES", 50)
    assert normality_test(NORMAL_DATA)["is_normal"] is True
    study = compute_capability_study(
        NORMAL_DATA, lsl=8.0, usl=12.0, alpha=STUDY_ALPHA, force_method="percentile"
    )
    assert study["method"] == "percentile"
    assert study["normal_before"] is True
    assert study["normal_after"] is None
