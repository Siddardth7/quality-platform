"""AIAG SPC chart constants.

The constants themselves now live in ``quality_core.spc.constants`` so SECOM, the
Control Plan app and the future API share one copy instead of importing sideways
into this app (audit A12, #205). This module re-exports them for backward
compatibility — existing ``from spc_app.spc_engine.constants import ...`` callers
keep working unchanged.

Source: AIAG SPC Reference Manual, 4th Ed. (2005); every value is cited in
``docs/ASSUMPTIONS_LOG.md``. Do not re-declare a constant here — change it in
``quality_core.spc.constants`` (and the log) or the copies drift.
"""

from __future__ import annotations

from quality_core.spc.constants import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    BOXCOX_LAMBDA_CANDIDATES,
    CAPABILITY_ALPHA,
    CUSUM_DEFAULT_H,
    CUSUM_DEFAULT_K,
    CUSUM_FIR_FRACTION,
    EWMA_DEFAULT_L,
    EWMA_DEFAULT_LAMBDA,
    EWMA_L_BY_LAMBDA,
    IMR_D2,
    IMR_D4,
    IMR_E2,
    MIN_BASELINE_INDIVIDUALS,
    MIN_BASELINE_SUBGROUPS,
    NONNORMAL_LOWER_PCTL,
    NONNORMAL_UPPER_PCTL,
    PERCENTILE_FIT_CANDIDATES,
    XBAR_R_CONSTANTS,
    XBAR_S_CONSTANTS,
    SPCChart,
)

__all__ = [
    "BOOTSTRAP_RESAMPLES",
    "BOOTSTRAP_SEED",
    "BOXCOX_LAMBDA_CANDIDATES",
    "CAPABILITY_ALPHA",
    "CUSUM_DEFAULT_H",
    "CUSUM_DEFAULT_K",
    "CUSUM_FIR_FRACTION",
    "EWMA_DEFAULT_L",
    "EWMA_DEFAULT_LAMBDA",
    "EWMA_L_BY_LAMBDA",
    "IMR_D2",
    "IMR_D4",
    "IMR_E2",
    "MIN_BASELINE_INDIVIDUALS",
    "MIN_BASELINE_SUBGROUPS",
    "NONNORMAL_LOWER_PCTL",
    "NONNORMAL_UPPER_PCTL",
    "PERCENTILE_FIT_CANDIDATES",
    "SPCChart",
    "XBAR_R_CONSTANTS",
    "XBAR_S_CONSTANTS",
]
