"""Control chart calculations for SPC dashboard.

Promoted out of ``spc_app.spc_engine`` by audit A12 (#205, PR 2 of 3) so SECOM,
the Control Plan app and the future API import *downward* into ``quality_core``
instead of sideways into another app. ``spc_app.spc_engine.control_charts`` now
re-exports this module, so existing SPC callers are unchanged. Every formula and
constant moved verbatim; the only addition is ``imr_limits`` (§2 of the spec),
which extracts the AIAG I-MR limit arithmetic SECOM previously duplicated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

import numpy as np

from quality_core.spc.constants import (
    CUSUM_DEFAULT_H,
    CUSUM_DEFAULT_K,
    CUSUM_FIR_FRACTION,
    EWMA_DEFAULT_L,
    EWMA_DEFAULT_LAMBDA,
    EWMA_L_BY_LAMBDA,
    IMR_D2,
    IMR_D4,
    IMR_E2,
    XBAR_R_CONSTANTS,
    XBAR_S_CONSTANTS,
)

if TYPE_CHECKING:
    # Avoid a runtime import cycle: phase.py imports compute_* from this module.
    from quality_core.spc.phase import FrozenLimits


class XbarRResult(TypedDict):
    subgroup_means: list[float]
    ranges: list[float]
    xbarbar: float
    rbar: float
    ucl_x: float
    lcl_x: float
    ucl_r: float
    lcl_r: float
    sigma_hat: float


class XbarSResult(TypedDict):
    subgroup_means: list[float]
    std_devs: list[float]
    xbarbar: float
    sbar: float
    ucl_x: float
    lcl_x: float
    ucl_s: float
    lcl_s: float
    sigma_hat: float


class ImrResult(TypedDict):
    values: list[float]
    moving_ranges: list[float]
    xbar: float
    mrbar: float
    ucl_x: float
    lcl_x: float
    ucl_mr: float
    lcl_mr: float
    sigma_hat: float


class ImrLimits(TypedDict):
    ucl_x: float
    lcl_x: float
    ucl_mr: float
    lcl_mr: float
    sigma_hat: float


class PResult(TypedDict):
    counts: list[float]
    sample_sizes: list[float]
    proportions: list[float]
    pbar: float
    ucl: list[float]
    lcl: list[float]


class CResult(TypedDict):
    counts: list[float]
    cbar: float
    ucl: float
    lcl: float


class UResult(TypedDict):
    counts: list[float]
    sample_sizes: list[float]
    u_values: list[float]
    ubar: float
    ucl: list[float]
    lcl: list[float]


class EWMAResult(TypedDict):
    values: list[float]
    z: list[float]
    ucl: list[float]
    lcl: list[float]
    signals: list[int]
    mu0: float
    sigma: float
    lam: float
    L: float
    pairing_adequate: bool
    pairing_note: str


class CUSUMResult(TypedDict):
    values: list[float]
    z: list[float]
    c_plus: list[float]
    c_minus: list[float]
    signals: list[int]
    n_plus: list[int]
    n_minus: list[int]
    mu0: float
    sigma: float
    k: float
    h: float
    fir: bool


def compute_xbar_r(
    subgroups: list[list[float]], frozen: FrozenLimits | None = None
) -> XbarRResult:
    subgroup_array = _validate_subgroups(subgroups)
    subgroup_size = subgroup_array.shape[1]
    if subgroup_size not in XBAR_R_CONSTANTS:
        raise ValueError("X-bar R chart requires subgroup size between 2 and 10.")

    subgroup_means = subgroup_array.mean(axis=1)
    ranges = subgroup_array.max(axis=1) - subgroup_array.min(axis=1)

    if frozen is not None:
        # ponytail: local import breaks the phase<->control_charts cycle (phase imports
        # compute_* at module level); only paid when frozen is actually used.
        from quality_core.spc.phase import _require_frozen

        _require_frozen(frozen, "xbar_r", subgroup_size)
        xbarbar = frozen["center_line"]
        rbar = frozen["dispersion_center"]
        ucl_x, lcl_x = frozen["ucl_x"], frozen["lcl_x"]
        ucl_r, lcl_r = frozen["ucl_disp"], frozen["lcl_disp"]
        sigma_hat = frozen["sigma_hat"]
    else:
        constants = XBAR_R_CONSTANTS[subgroup_size]
        xbarbar = float(subgroup_means.mean())
        rbar = float(ranges.mean())
        ucl_x = xbarbar + (constants["A2"] * rbar)
        lcl_x = xbarbar - (constants["A2"] * rbar)
        ucl_r = constants["D4"] * rbar
        lcl_r = max(0.0, constants["D3"] * rbar)
        sigma_hat = rbar / constants["d2"]

    return {
        "subgroup_means": subgroup_means.tolist(),
        "ranges": ranges.tolist(),
        "xbarbar": xbarbar,
        "rbar": rbar,
        "ucl_x": ucl_x,
        "lcl_x": lcl_x,
        "ucl_r": ucl_r,
        "lcl_r": lcl_r,
        "sigma_hat": sigma_hat,
    }


def compute_xbar_s(
    subgroups: list[list[float]], frozen: FrozenLimits | None = None
) -> XbarSResult:
    subgroup_array = _validate_subgroups(subgroups)
    subgroup_size = subgroup_array.shape[1]
    if subgroup_size not in XBAR_S_CONSTANTS:
        raise ValueError("X-bar S chart requires subgroup size between 2 and 12.")

    subgroup_means = subgroup_array.mean(axis=1)
    std_devs = subgroup_array.std(axis=1, ddof=1)

    if frozen is not None:
        from quality_core.spc.phase import _require_frozen

        _require_frozen(frozen, "xbar_s", subgroup_size)
        xbarbar = frozen["center_line"]
        sbar = frozen["dispersion_center"]
        ucl_x, lcl_x = frozen["ucl_x"], frozen["lcl_x"]
        ucl_s, lcl_s = frozen["ucl_disp"], frozen["lcl_disp"]
        sigma_hat = frozen["sigma_hat"]
    else:
        constants = XBAR_S_CONSTANTS[subgroup_size]
        xbarbar = float(subgroup_means.mean())
        sbar = float(std_devs.mean())
        ucl_x = xbarbar + (constants["A3"] * sbar)
        lcl_x = xbarbar - (constants["A3"] * sbar)
        ucl_s = constants["B4"] * sbar
        lcl_s = max(0.0, constants["B3"] * sbar)
        sigma_hat = sbar / constants["c4"]

    return {
        "subgroup_means": subgroup_means.tolist(),
        "std_devs": std_devs.tolist(),
        "xbarbar": xbarbar,
        "sbar": sbar,
        "ucl_x": ucl_x,
        "lcl_x": lcl_x,
        "ucl_s": ucl_s,
        "lcl_s": lcl_s,
        "sigma_hat": sigma_hat,
    }


def imr_limits(xbar: float, mrbar: float) -> ImrLimits:
    """The AIAG I-MR control limits and within-sigma from a centre line and MR-bar.

    Written once here (audit A12, #205) because SECOM charts the same formula on a
    differently-pooled `mrbar` (gap-broken runs, OQ5) — a legitimate *input* difference,
    not a different formula. Source: AIAG SPC Reference Manual 4th Ed. (2005); see
    apps/spc/docs/ASSUMPTIONS_LOG.md RULE 3.

    Pure arithmetic: no validation, no clamping. `mrbar == 0.0` yields zero-width limits
    and `sigma_hat == 0.0`, which is what both callers already produce today; the
    downstream detectors are what reject it.
    """
    return {
        "ucl_x": xbar + (IMR_E2 * mrbar),
        "lcl_x": xbar - (IMR_E2 * mrbar),
        "ucl_mr": IMR_D4 * mrbar,
        "lcl_mr": 0.0,
        "sigma_hat": mrbar / IMR_D2,
    }


def compute_imr(values: list[float], frozen: FrozenLimits | None = None) -> ImrResult:
    values_array = np.asarray(values, dtype=float)
    if values_array.ndim != 1 or values_array.size < 2:
        raise ValueError("I-MR chart requires at least two values.")

    moving_ranges = np.abs(np.diff(values_array))

    if frozen is not None:
        from quality_core.spc.phase import _require_frozen

        _require_frozen(frozen, "imr", 1)
        xbar = frozen["center_line"]
        mrbar = frozen["dispersion_center"]
        ucl_x, lcl_x = frozen["ucl_x"], frozen["lcl_x"]
        ucl_mr, lcl_mr = frozen["ucl_disp"], frozen["lcl_disp"]
        sigma_hat = frozen["sigma_hat"]
    else:
        xbar = float(values_array.mean())
        mrbar = float(moving_ranges.mean())
        limits = imr_limits(xbar, mrbar)
        ucl_x, lcl_x = limits["ucl_x"], limits["lcl_x"]
        ucl_mr, lcl_mr = limits["ucl_mr"], limits["lcl_mr"]
        sigma_hat = limits["sigma_hat"]

    return {
        "values": values_array.tolist(),
        "moving_ranges": moving_ranges.tolist(),
        "xbar": xbar,
        "mrbar": mrbar,
        "ucl_x": ucl_x,
        "lcl_x": lcl_x,
        "ucl_mr": ucl_mr,
        "lcl_mr": lcl_mr,
        "sigma_hat": sigma_hat,
    }


def compute_p(
    defective_counts: list[float],
    sample_sizes: list[float],
) -> PResult:
    counts = np.asarray(defective_counts, dtype=float)
    sizes = np.asarray(sample_sizes, dtype=float)
    _validate_attribute_inputs(counts, sizes)

    proportions = counts / sizes
    pbar = float(counts.sum() / sizes.sum())
    sigma = np.sqrt((pbar * (1.0 - pbar)) / sizes)

    return {
        "counts": counts.tolist(),
        "sample_sizes": sizes.tolist(),
        "proportions": proportions.tolist(),
        "pbar": pbar,
        "ucl": np.minimum(1.0, pbar + (3.0 * sigma)).tolist(),
        "lcl": np.maximum(0.0, pbar - (3.0 * sigma)).tolist(),
    }


def compute_c(defect_counts: list[float]) -> CResult:
    counts = np.asarray(defect_counts, dtype=float)
    if counts.ndim != 1 or counts.size == 0:
        raise ValueError("c-chart requires at least one count.")

    cbar = float(counts.mean())
    sigma = np.sqrt(cbar)

    return {
        "counts": counts.tolist(),
        "cbar": cbar,
        "ucl": cbar + (3.0 * sigma),
        "lcl": max(0.0, cbar - (3.0 * sigma)),
    }


def compute_u(
    defect_counts: list[float],
    sample_sizes: list[float],
) -> UResult:
    counts = np.asarray(defect_counts, dtype=float)
    sizes = np.asarray(sample_sizes, dtype=float)
    _validate_attribute_inputs(counts, sizes)

    u_values = counts / sizes
    ubar = float(counts.sum() / sizes.sum())
    sigma = np.sqrt(ubar / sizes)

    return {
        "counts": counts.tolist(),
        "sample_sizes": sizes.tolist(),
        "u_values": u_values.tolist(),
        "ubar": ubar,
        "ucl": (ubar + (3.0 * sigma)).tolist(),
        "lcl": np.maximum(0.0, ubar - (3.0 * sigma)).tolist(),
    }


def compute_ewma(
    values: list[float],
    mu0: float,
    sigma: float,
    lam: float = EWMA_DEFAULT_LAMBDA,
    L: float = EWMA_DEFAULT_L,
) -> EWMAResult:
    values_array = np.asarray(values, dtype=float)
    _validate_ewma_params(values_array, sigma, lam, L)

    z = np.empty(values_array.size)
    z[0] = lam * values_array[0] + (1.0 - lam) * mu0
    for i in range(1, values_array.size):
        z[i] = lam * values_array[i] + (1.0 - lam) * z[i - 1]

    i_index = np.arange(1, values_array.size + 1)
    variance = (lam / (2.0 - lam)) * (1.0 - (1.0 - lam) ** (2 * i_index))
    half_width = L * sigma * np.sqrt(variance)
    ucl = mu0 + half_width
    lcl = mu0 - half_width

    signals = [int(i) for i in range(values_array.size) if z[i] > ucl[i] or z[i] < lcl[i]]
    pairing_adequate, pairing_note = _check_ewma_pairing(lam, L)

    return {
        "values": values_array.tolist(),
        "z": z.tolist(),
        "ucl": ucl.tolist(),
        "lcl": lcl.tolist(),
        "signals": signals,
        "mu0": float(mu0),
        "sigma": float(sigma),
        "lam": float(lam),
        "L": float(L),
        "pairing_adequate": pairing_adequate,
        "pairing_note": pairing_note,
    }


def compute_cusum(
    values: list[float],
    mu0: float,
    sigma: float,
    k: float = CUSUM_DEFAULT_K,
    h: float = CUSUM_DEFAULT_H,
    fir: bool = False,
) -> CUSUMResult:
    values_array = np.asarray(values, dtype=float)
    _validate_cusum_params(values_array, sigma, k, h)

    z = (values_array - mu0) / sigma
    seed = (CUSUM_FIR_FRACTION * h) if fir else 0.0

    n = values_array.size
    c_plus = np.empty(n)
    c_minus = np.empty(n)
    c_plus[0] = max(0.0, z[0] - k + seed)
    c_minus[0] = max(0.0, -z[0] - k + seed)
    for i in range(1, n):
        c_plus[i] = max(0.0, z[i] - k + c_plus[i - 1])
        c_minus[i] = max(0.0, -z[i] - k + c_minus[i - 1])

    signals = sorted({i for i in range(n) if c_plus[i] > h or c_minus[i] > h})

    n_plus = [0] * n
    n_minus = [0] * n
    for i in range(n):
        prior_plus = n_plus[i - 1] if i > 0 else 0
        prior_minus = n_minus[i - 1] if i > 0 else 0
        n_plus[i] = prior_plus + 1 if c_plus[i] > 0 else 0
        n_minus[i] = prior_minus + 1 if c_minus[i] > 0 else 0

    return {
        "values": values_array.tolist(),
        "z": z.tolist(),
        "c_plus": c_plus.tolist(),
        "c_minus": c_minus.tolist(),
        "signals": signals,
        "n_plus": n_plus,
        "n_minus": n_minus,
        "mu0": float(mu0),
        "sigma": float(sigma),
        "k": float(k),
        "h": float(h),
        "fir": fir,
    }


def _validate_subgroups(subgroups: list[list[float]]) -> np.ndarray:
    subgroup_array = np.asarray(subgroups, dtype=float)
    if subgroup_array.ndim != 2 or subgroup_array.shape[0] == 0:
        raise ValueError("Control chart input must be a 2D subgroup array.")
    return subgroup_array


def _validate_attribute_inputs(counts: np.ndarray, sizes: np.ndarray) -> None:
    if counts.ndim != 1 or sizes.ndim != 1 or counts.size == 0 or counts.size != sizes.size:
        raise ValueError("Attribute chart inputs must be matching 1D arrays.")
    # ~isfinite first: `np.nan <= 0` is False, so a NaN size slipped the positivity
    # check below and produced NaN control limits with no error at all (#200).
    if np.any(~np.isfinite(sizes)) or np.any(sizes <= 0):
        raise ValueError("Attribute chart sample sizes must be positive.")


def _validate_ewma_params(values_array: np.ndarray, sigma: float, lam: float, L: float) -> None:
    if values_array.ndim != 1 or values_array.size == 0:
        raise ValueError("EWMA chart requires a non-empty 1D array of values.")
    if sigma <= 0:
        raise ValueError("EWMA chart requires sigma > 0.")
    if lam <= 0 or lam > 1:
        raise ValueError("EWMA chart requires 0 < lam <= 1.")
    if L <= 0:
        raise ValueError("EWMA chart requires L > 0.")


def _validate_cusum_params(values_array: np.ndarray, sigma: float, k: float, h: float) -> None:
    if values_array.ndim != 1 or values_array.size == 0:
        raise ValueError("CUSUM chart requires a non-empty 1D array of values.")
    if sigma <= 0:
        raise ValueError("CUSUM chart requires sigma > 0.")
    if k <= 0:
        raise ValueError("CUSUM chart requires k > 0.")
    if h <= 0:
        raise ValueError("CUSUM chart requires h > 0.")


def _check_ewma_pairing(lam: float, L: float) -> tuple[bool, str]:
    for key, paired_l in EWMA_L_BY_LAMBDA.items():
        if abs(lam - key) <= 1e-9:
            if abs(L - paired_l) > 0.01:
                return False, (
                    f"L={L} paired with λ={lam}; Lucas & Saccucci recommends "
                    f"L={paired_l} (ARL0≈370–500)."
                )
            return True, ""
    return True, ""
