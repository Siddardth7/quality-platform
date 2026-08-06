"""Process capability calculations, including non-normal (Box-Cox / fitted-percentile) studies.

Promoted out of `spc_app.spc_engine` by audit A12 (#205, PR 3 of 3);
`spc_app.spc_engine.capability` now re-exports it, so existing SPC callers are
unchanged, and `secom_app.capability` imports downward into `quality_core`
instead of sideways into another app. Moved verbatim apart from import paths:
every formula, threshold and citation comment is unchanged.

See apps/spc/docs/ASSUMPTIONS_LOG.md RULE 14 for standards attribution.
"""

from __future__ import annotations

import math
from typing import Any, Literal, Mapping, Sequence, TypedDict

import numpy as np
from scipy import special, stats
from scipy.stats import boxcox, chi2, norm, shapiro, yeojohnson

from quality_core.spc.constants import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    BOXCOX_LAMBDA_CANDIDATES,
    CAPABILITY_ALPHA,
    NONNORMAL_LOWER_PCTL,
    NONNORMAL_UPPER_PCTL,
    PERCENTILE_FIT_CANDIDATES,
)
from quality_core.spc.control_charts import compute_imr, compute_xbar_r
from quality_core.spc.stability import stability_fields

_CI_PAIRING_NOTE = (
    " The χ²/Bissell CIs are attached to Pp/Ppk (ν=n−1), which use the ddof=1 sample SD"
    " those intervals are derived for. No CI is reported for the within-σ Cp/Cpk."
)

__all__ = [
    "CapabilityStudy",
    "compute_capability",
    "compute_capability_study",
    "normality_test",
]


class CapabilityStudy(TypedDict):
    method: str  # "normal" | "boxcox" | "yeojohnson" | "percentile"
    subgroup_size: int  # 1 for individuals, else the subgroup n
    cp: float | None
    cpk: float | None
    pp: float | None
    ppk: float | None
    cp_ci: tuple[float, float] | None  # percentile path only (bootstrap); None otherwise
    cpk_ci: tuple[float, float] | None  # percentile path only (bootstrap); None otherwise
    cpk_lower: float | None  # percentile path only (bootstrap); None otherwise
    pp_ci: tuple[float, float] | None  # χ² CI on Pp (ddof=1 sample SD, ν=n−1)
    ppk_ci: tuple[float, float] | None  # Bissell two-sided CI on Ppk
    ppk_lower: float | None  # Bissell one-sided lower bound on Ppk
    ci_estimator: str  # "sample_sd_ddof1" | "bootstrap_percentile"
    ci_df: int | None  # n−1 for the parametric CIs; None for the bootstrap
    mean: float  # in the space capability was computed in
    sigma_hat: float  # within-subgroup sigma in that space
    sigma_overall: float  # overall sigma in that space
    lambda_used: float | None  # None for normal/percentile
    lambda_mle: float | None
    lambda_ci: tuple[float, float] | None
    shift: float  # c in x+c (0.0 if none / Yeo-Johnson)
    fitted_dist: str | None  # selected scipy dist name (percentile method only)
    alpha: float
    n: int  # total observations
    normal_before: bool
    normal_after: bool | None  # None if not transformed
    note: str  # soft-warn method/assumption note
    stable: bool | None  # None = not assessed (no control-chart context supplied)
    stability_note: str | None  # None only when stable is True


def compute_capability(
    data: np.ndarray | list[float],
    lsl: float | None,
    usl: float | None,
    sigma_hat: float,
    *,
    alpha: float = CAPABILITY_ALPHA,
) -> dict[str, Any]:
    values = np.asarray(data, dtype=float)
    if values.ndim != 1 or values.size < 2:
        raise ValueError("Capability analysis requires at least two data points.")
    if sigma_hat <= 0:
        raise ValueError("sigma_hat must be positive.")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1).")

    n = int(values.size)
    mean = float(values.mean())
    sigma_overall = float(np.std(values, ddof=1))

    cp = _spread_capability(lsl=lsl, usl=usl, sigma=sigma_hat)
    cpk = _centered_capability(mean=mean, lsl=lsl, usl=usl, sigma=sigma_hat)
    pp = _spread_capability(lsl=lsl, usl=usl, sigma=sigma_overall)
    ppk = _centered_capability(mean=mean, lsl=lsl, usl=usl, sigma=sigma_overall)

    # The χ²/Bissell intervals are derived for σ estimated by the ddof=1 sample SD with
    # ν = n−1, so they belong to Pp/Ppk (sigma_overall), NOT to the within-σ Cp/Cpk
    # (R̄/d₂ or MR̄/d₂, whose effective df are fewer than n−1). See ASSUMPTIONS_LOG
    # RULE 14 "Confidence intervals" (#193, audit F-05).
    pp_ci = _cp_chi2_ci(pp, n, alpha) if pp is not None else None
    if ppk is not None:
        ppk_ci, ppk_lower = _cpk_bissell_ci(ppk, n, alpha)
    else:
        ppk_ci, ppk_lower = None, None

    return {
        "cp": cp,
        "cpk": cpk,
        "pp": pp,
        "ppk": ppk,
        "mean": mean,
        "sigma_hat": sigma_hat,
        "sigma_overall": sigma_overall,
        "n": n,
        "alpha": alpha,
        "pp_ci": pp_ci,
        "ppk_ci": ppk_ci,
        "ppk_lower": ppk_lower,
        "ci_estimator": "sample_sd_ddof1",
        "ci_df": n - 1,
    }


def normality_test(data: np.ndarray | list[float]) -> dict[str, Any]:
    values = np.asarray(data, dtype=float)
    if values.ndim != 1 or values.size < 3:
        raise ValueError("Shapiro-Wilk normality test requires at least three values.")

    w_stat, p_value = shapiro(values)
    return {
        "w_stat": float(w_stat),
        "p_value": float(p_value),
        "is_normal": bool(p_value > 0.05),
    }


def compute_capability_study(
    data: np.ndarray | list[float] | list[list[float]],
    lsl: float | None,
    usl: float | None,
    *,
    alpha: float = CAPABILITY_ALPHA,
    allow_yeojohnson: bool = True,
    force_method: Literal["auto", "normal", "boxcox", "percentile"] = "auto",
    violations: Sequence[Mapping[str, int | str]] | None = None,
) -> CapabilityStudy:
    """Same as before, plus a user-override `force_method` (SME Q1, W10-5 #145):

    - "auto" (default, unchanged): Shapiro-Wilk-driven method selection.
    - "normal": skip the normality gate, compute normal-theory capability + CIs on
      raw data regardless of the Shapiro-Wilk result. The analyst is responsible
      for that assumption (see docs/ASSUMPTIONS_LOG.md RULE 15 note).
    - "boxcox": force the transform path even if the raw data already passed
      Shapiro-Wilk (non-positive data still honors `allow_yeojohnson`).
    - "percentile": force the fitted-distribution percentile + bootstrap CI method
      directly on the original data, skipping both the normal and transform paths.

    `violations` is the caller's control-chart out-of-control signal list (RULE 7
    stability gate, #191). Omit it and the study reports `stable=None` — "not
    assessed" — never a fabricated in-control claim; pass `[]` to state that the
    chart was assessed and is in control. Indices are annotated, never suppressed.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1).")

    shaped = np.asarray(data, dtype=float)
    if shaped.ndim not in (1, 2):
        raise ValueError("data must be 1D individuals or 2D subgroups.")
    flat = shaped.reshape(-1)
    if flat.size < 3:
        raise ValueError("Capability study requires at least three observations.")
    if np.std(flat, ddof=1) == 0.0:
        raise ValueError("constant data has no capability.")

    n = int(flat.size)
    normal_before = bool(normality_test(flat)["is_normal"])
    # Stability is assessed by the caller on the ORIGINAL data, so the same verdict
    # rides every return path — a transform cannot change it.
    stable, stability_note = stability_fields(violations)

    if force_method == "percentile":
        return _percentile_study(
            flat, shaped, lsl, usl, alpha, n, normal_before,
            note_prefix="Method user-forced to 'percentile' (force_method). ",
            stable=stable, stability_note=stability_note,
        )

    use_normal_path = force_method == "normal" or (force_method == "auto" and normal_before)
    if use_normal_path:
        within_sigma, subgroup_size = _within_sigma(shaped)
        base = compute_capability(flat, lsl, usl, within_sigma, alpha=alpha)
        note = (
            (
                "Normality user-forced (force_method='normal'); normal-theory Cp/Cpk "
                "reported on raw data — the analyst is responsible for this assumption."
                if force_method == "normal"
                else "Data passed Shapiro-Wilk (p>0.05); normal-theory Cp/Cpk reported."
            )
            + _CI_PAIRING_NOTE
        ) + _small_n_note(n)
        return _build_transform_study(
            method="normal",
            subgroup_size=subgroup_size,
            base=base,
            lambda_used=None,
            lambda_mle=None,
            lambda_ci=None,
            shift=0.0,
            alpha=alpha,
            n=n,
            normal_before=normal_before,
            normal_after=None,
            note=note,
            stable=stable,
            stability_note=stability_note,
        )

    # Non-normal (or force_method="boxcox" forcing the transform path): transform (Decision 2).
    shift = 0.0
    lambda_ci: tuple[float, float] | None
    if flat.min() > 0:
        xt, lambda_mle, lambda_ci = boxcox(flat, alpha=alpha)
        method = "boxcox"
    elif allow_yeojohnson:
        xt, lambda_mle = yeojohnson(flat)
        lambda_ci = None
        method = "yeojohnson"
    else:
        shift = 1.0 - float(flat.min())
        xt, lambda_mle, lambda_ci = boxcox(flat + shift, alpha=alpha)
        method = "boxcox"

    lambda_mle = float(lambda_mle)
    lambda_used = lambda_mle
    if method == "boxcox" and lambda_ci is not None:
        # Rounded-λ snap (E4): only snap if a tabulated value falls inside the likelihood CI.
        nearest = min(BOXCOX_LAMBDA_CANDIDATES, key=lambda c: abs(c - lambda_mle))
        if lambda_ci[0] <= nearest <= lambda_ci[1]:
            lambda_used = nearest
            xt = special.boxcox(flat + shift, lambda_used)

    def _transform_limit(v: float) -> float:
        if method == "boxcox":
            return float(special.boxcox(v + shift, lambda_used))
        return float(yeojohnson(np.array([v + shift]), lmbda=lambda_used)[0])

    # E2 — λ<0 ordering guard, no literal swap branch.
    if lsl is not None and usl is not None:
        lsl_t, usl_t = sorted((_transform_limit(lsl), _transform_limit(usl)))
    elif lsl is not None:
        lsl_t, usl_t = _transform_limit(lsl), None
    elif usl is not None:
        lsl_t, usl_t = None, _transform_limit(usl)
    else:
        lsl_t = usl_t = None

    shaped_transformed = xt.reshape(shaped.shape)
    within_sigma_t, subgroup_size = _within_sigma(shaped_transformed)
    normal_after = bool(normality_test(xt)["is_normal"])

    forced_prefix = (
        "Transform user-forced (force_method='boxcox') despite raw data passing Shapiro-Wilk; "
        if force_method == "boxcox" and normal_before
        else ""
    )
    if normal_after:
        base = compute_capability(xt, lsl_t, usl_t, within_sigma_t, alpha=alpha)
        note = (
            forced_prefix
            + f"Data transformed via {method} (λ_used={lambda_used:.4g}); "
            "transformed data passed Shapiro-Wilk; normal-theory Cp/Cpk applied in "
            "transformed space." + _CI_PAIRING_NOTE + _small_n_note(n)
        )
        return _build_transform_study(
            method=method,
            subgroup_size=subgroup_size,
            base=base,
            lambda_used=lambda_used,
            lambda_mle=lambda_mle,
            lambda_ci=lambda_ci,
            shift=shift,
            alpha=alpha,
            n=n,
            normal_before=normal_before,
            normal_after=True,
            note=note,
            stable=stable,
            stability_note=stability_note,
        )

    # E5 — still non-normal after transform: fitted-percentile fallback on the ORIGINAL data.
    # Lambda/shift from the failed transform attempt are kept as informational context.
    return _percentile_study(
        flat, shaped, lsl, usl, alpha, n, normal_before=normal_before, normal_after=False,
        lambda_used=lambda_used, lambda_mle=lambda_mle, lambda_ci=lambda_ci, shift=shift,
        note_prefix=forced_prefix + f"Data remained non-normal after {method} transform "
        "(Shapiro-Wilk p<=0.05); ",
        stable=stable, stability_note=stability_note,
    )


def _percentile_study(
    flat: np.ndarray,
    shaped: np.ndarray,
    lsl: float | None,
    usl: float | None,
    alpha: float,
    n: int,
    normal_before: bool,
    *,
    normal_after: bool | None = None,
    lambda_used: float | None = None,
    lambda_mle: float | None = None,
    lambda_ci: tuple[float, float] | None = None,
    shift: float = 0.0,
    note_prefix: str = "",
    stable: bool | None,
    stability_note: str | None,
) -> CapabilityStudy:
    """Fitted-distribution percentile method (ISO 22514-2) on the ORIGINAL data.

    Shared by the E5 auto fallback (still non-normal after transform) and the
    `force_method="percentile"` user override (SME Q1) — only the note/`normal_*`
    bookkeeping differs between the two callers.
    """
    cp, cpk, fitted_dist = _fit_percentile_capability(flat, lsl, usl)
    cp_ci, cpk_ci = _bootstrap_percentile_ci(flat, lsl, usl, alpha)
    cpk_lower = cpk_ci[0] if cpk_ci is not None else None
    within_sigma, subgroup_size = _within_sigma(shaped)
    sigma_overall = float(np.std(flat, ddof=1))

    return {
        "method": "percentile",
        "subgroup_size": subgroup_size,
        "cp": cp,
        "cpk": cpk,
        "pp": None,
        "ppk": None,
        "cp_ci": cp_ci,
        "cpk_ci": cpk_ci,
        "cpk_lower": cpk_lower,
        "pp_ci": None,
        "ppk_ci": None,
        "ppk_lower": None,
        "ci_estimator": "bootstrap_percentile",
        "ci_df": None,
        "mean": float(np.mean(flat)),
        "sigma_hat": within_sigma,
        "sigma_overall": sigma_overall,
        "lambda_used": lambda_used,
        "lambda_mle": lambda_mle,
        "lambda_ci": lambda_ci,
        "shift": shift,
        "fitted_dist": fitted_dist,
        "alpha": alpha,
        "n": n,
        "normal_before": normal_before,
        "normal_after": normal_after,
        "note": (
            note_prefix
            + "used fitted-distribution percentile method (ISO 22514-2, min-AIC over "
            "lognorm/weibull_min/gamma/johnsonsu). cpk_lower is the two-sided bootstrap "
            "cpk_ci lower bound." + _small_n_note(n)
        ),
        "stable": stable,
        "stability_note": stability_note,
    }


def _build_transform_study(
    *,
    method: str,
    subgroup_size: int,
    base: dict[str, Any],
    lambda_used: float | None,
    lambda_mle: float | None,
    lambda_ci: tuple[float, float] | None,
    shift: float,
    alpha: float,
    n: int,
    normal_before: bool,
    normal_after: bool | None,
    note: str,
    stable: bool | None,
    stability_note: str | None,
) -> CapabilityStudy:
    return {
        "method": method,
        "subgroup_size": subgroup_size,
        "cp": base["cp"],
        "cpk": base["cpk"],
        "pp": base["pp"],
        "ppk": base["ppk"],
        "cp_ci": None,
        "cpk_ci": None,
        "cpk_lower": None,
        "pp_ci": base["pp_ci"],
        "ppk_ci": base["ppk_ci"],
        "ppk_lower": base["ppk_lower"],
        "ci_estimator": base["ci_estimator"],
        "ci_df": base["ci_df"],
        "mean": base["mean"],
        "sigma_hat": base["sigma_hat"],
        "sigma_overall": base["sigma_overall"],
        "lambda_used": lambda_used,
        "lambda_mle": lambda_mle,
        "lambda_ci": lambda_ci,
        "shift": shift,
        "fitted_dist": None,
        "alpha": alpha,
        "n": n,
        "normal_before": normal_before,
        "normal_after": normal_after,
        "note": note,
        "stable": stable,
        "stability_note": stability_note,
    }


def _within_sigma(shaped: np.ndarray) -> tuple[float, int]:
    if shaped.ndim == 1:
        imr_result = compute_imr(shaped.tolist())
        return imr_result["sigma_hat"], 1
    xbar_r_result = compute_xbar_r(shaped.tolist())
    return xbar_r_result["sigma_hat"], shaped.shape[1]


def _fit_percentile_capability(
    flat: np.ndarray, lsl: float | None, usl: float | None
) -> tuple[float | None, float | None, str | None]:
    best_name: str | None = None
    best_aic = math.inf
    best_dist: Any = None
    best_params: tuple[float, ...] | None = None

    for name in PERCENTILE_FIT_CANDIDATES:
        dist = getattr(stats, name)
        try:
            params = dist.fit(flat)
            loglik = float(np.sum(dist.logpdf(flat, *params)))
            aic = 2 * len(params) - 2 * loglik
        except Exception:  # noqa: BLE001 - candidate fit failures are expected/skippable
            continue
        if not math.isfinite(aic):
            continue
        if aic < best_aic:
            best_aic = aic
            best_name = name
            best_dist = dist
            best_params = params

    if best_dist is None or best_params is None:
        # E11 — all candidates failed: empirical last-resort fallback.
        p_lo = float(np.quantile(flat, NONNORMAL_LOWER_PCTL))
        p_hi = float(np.quantile(flat, NONNORMAL_UPPER_PCTL))
        med = float(np.median(flat))
        fitted_dist = None
    else:
        p_lo = float(best_dist.ppf(NONNORMAL_LOWER_PCTL, *best_params))
        p_hi = float(best_dist.ppf(NONNORMAL_UPPER_PCTL, *best_params))
        med = float(best_dist.median(*best_params))
        fitted_dist = best_name

    cp = (usl - lsl) / (p_hi - p_lo) if (lsl is not None and usl is not None) else None
    cpk = _percentile_cpk(med=med, lo=p_lo, hi=p_hi, lsl=lsl, usl=usl)
    return cp, cpk, fitted_dist


def _percentile_cpk(
    *, med: float, lo: float, hi: float, lsl: float | None, usl: float | None
) -> float | None:
    if lsl is not None and usl is not None:
        upper = (usl - med) / (hi - med)
        lower = (med - lsl) / (med - lo)
        return min(upper, lower)
    if usl is not None:
        return (usl - med) / (hi - med)
    if lsl is not None:
        return (med - lsl) / (med - lo)
    return None


def _bootstrap_percentile_ci(
    flat: np.ndarray, lsl: float | None, usl: float | None, alpha: float
) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
    # ponytail: refit per resample; cache the selected family if this ever dominates runtime.
    def _cp_stat(sample: np.ndarray) -> float:
        cp, _, _ = _fit_percentile_capability(np.asarray(sample), lsl, usl)
        return cp if cp is not None else math.nan

    def _cpk_stat(sample: np.ndarray) -> float:
        _, cpk, _ = _fit_percentile_capability(np.asarray(sample), lsl, usl)
        return cpk if cpk is not None else math.nan

    point_cp, point_cpk, _ = _fit_percentile_capability(flat, lsl, usl)

    cp_ci: tuple[float, float] | None = None
    if point_cp is not None:
        result = stats.bootstrap(
            (flat,),
            _cp_stat,
            n_resamples=BOOTSTRAP_RESAMPLES,
            confidence_level=1.0 - alpha,
            method="percentile",
            vectorized=False,
            rng=np.random.default_rng(BOOTSTRAP_SEED),
        )
        cp_ci = (float(result.confidence_interval.low), float(result.confidence_interval.high))

    cpk_ci: tuple[float, float] | None = None
    if point_cpk is not None:
        result = stats.bootstrap(
            (flat,),
            _cpk_stat,
            n_resamples=BOOTSTRAP_RESAMPLES,
            confidence_level=1.0 - alpha,
            method="percentile",
            vectorized=False,
            rng=np.random.default_rng(BOOTSTRAP_SEED),
        )
        cpk_ci = (float(result.confidence_interval.low), float(result.confidence_interval.high))

    return cp_ci, cpk_ci


def _cp_chi2_ci(cp: float, n: int, alpha: float) -> tuple[float, float]:
    lo = cp * math.sqrt(chi2.ppf(alpha / 2.0, n - 1) / (n - 1))
    hi = cp * math.sqrt(chi2.ppf(1.0 - alpha / 2.0, n - 1) / (n - 1))
    return float(lo), float(hi)


def _cpk_bissell_ci(cpk: float, n: int, alpha: float) -> tuple[tuple[float, float], float]:
    se = math.sqrt(1.0 / (9.0 * n) + (cpk**2) / (2.0 * (n - 1)))
    z_two = float(norm.ppf(1.0 - alpha / 2.0))
    z_one = float(norm.ppf(1.0 - alpha))
    ci = (cpk - z_two * se, cpk + z_two * se)
    lower = cpk - z_one * se
    return ci, float(lower)


def _small_n_note(n: int) -> str:
    if n < 30:
        return " Note: n<30 — Bissell/χ² CIs assume a large sample (n≈30-50); use with caution."
    return ""


def _spread_capability(lsl: float | None, usl: float | None, sigma: float) -> float | None:
    if lsl is None or usl is None:
        return None
    return (usl - lsl) / (6.0 * sigma)


def _centered_capability(mean: float, lsl: float | None, usl: float | None, sigma: float) -> float | None:
    if lsl is not None and usl is not None:
        upper = (usl - mean) / (3.0 * sigma)
        lower = (mean - lsl) / (3.0 * sigma)
        return min(upper, lower)
    if usl is not None:
        return (usl - mean) / (3.0 * sigma)
    if lsl is not None:
        return (mean - lsl) / (3.0 * sigma)
    return None
