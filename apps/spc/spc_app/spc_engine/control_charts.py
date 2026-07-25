"""Control chart calculations for SPC dashboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

import numpy as np

from spc_app.spc_engine.constants import IMR_D2, IMR_D4, IMR_E2, XBAR_R_CONSTANTS, XBAR_S_CONSTANTS

if TYPE_CHECKING:
    # Avoid a runtime import cycle: phase.py imports compute_* from this module.
    from spc_app.spc_engine.phase import FrozenLimits


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
        from spc_app.spc_engine.phase import _require_frozen

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
        from spc_app.spc_engine.phase import _require_frozen

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


def compute_imr(values: list[float], frozen: FrozenLimits | None = None) -> ImrResult:
    values_array = np.asarray(values, dtype=float)
    if values_array.ndim != 1 or values_array.size < 2:
        raise ValueError("I-MR chart requires at least two values.")

    moving_ranges = np.abs(np.diff(values_array))

    if frozen is not None:
        from spc_app.spc_engine.phase import _require_frozen

        _require_frozen(frozen, "imr", 1)
        xbar = frozen["center_line"]
        mrbar = frozen["dispersion_center"]
        ucl_x, lcl_x = frozen["ucl_x"], frozen["lcl_x"]
        ucl_mr, lcl_mr = frozen["ucl_disp"], frozen["lcl_disp"]
        sigma_hat = frozen["sigma_hat"]
    else:
        xbar = float(values_array.mean())
        mrbar = float(moving_ranges.mean())
        ucl_x = xbar + (IMR_E2 * mrbar)
        lcl_x = xbar - (IMR_E2 * mrbar)
        ucl_mr = IMR_D4 * mrbar
        lcl_mr = 0.0
        sigma_hat = mrbar / IMR_D2

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


def _validate_subgroups(subgroups: list[list[float]]) -> np.ndarray:
    subgroup_array = np.asarray(subgroups, dtype=float)
    if subgroup_array.ndim != 2 or subgroup_array.shape[0] == 0:
        raise ValueError("Control chart input must be a 2D subgroup array.")
    return subgroup_array


def _validate_attribute_inputs(counts: np.ndarray, sizes: np.ndarray) -> None:
    if counts.ndim != 1 or sizes.ndim != 1 or counts.size == 0 or counts.size != sizes.size:
        raise ValueError("Attribute chart inputs must be matching 1D arrays.")
    if np.any(sizes <= 0):
        raise ValueError("Attribute chart sample sizes must be positive.")
