"""Process capability calculations."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import shapiro


def compute_capability(
    data: np.ndarray | list[float],
    lsl: float | None,
    usl: float | None,
    sigma_hat: float,
) -> dict[str, Any]:
    values = np.asarray(data, dtype=float)
    if values.ndim != 1 or values.size < 2:
        raise ValueError("Capability analysis requires at least two data points.")
    if sigma_hat <= 0:
        raise ValueError("sigma_hat must be positive.")

    mean = float(values.mean())
    sigma_overall = float(np.std(values, ddof=1))

    cp = _spread_capability(lsl=lsl, usl=usl, sigma=sigma_hat)
    cpk = _centered_capability(mean=mean, lsl=lsl, usl=usl, sigma=sigma_hat)
    pp = _spread_capability(lsl=lsl, usl=usl, sigma=sigma_overall)
    ppk = _centered_capability(mean=mean, lsl=lsl, usl=usl, sigma=sigma_overall)

    return {
        "cp": cp,
        "cpk": cpk,
        "pp": pp,
        "ppk": ppk,
        "mean": mean,
        "sigma_hat": sigma_hat,
        "sigma_overall": sigma_overall,
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
