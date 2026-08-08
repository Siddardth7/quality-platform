"""Control chart calculations for SPC dashboard.

The calculations themselves now live in ``quality_core.spc.control_charts`` so
SECOM, the Control Plan app and the future API share one copy instead of importing
sideways into this app (audit A12, #205, PR 2 of 3). This module re-exports them
for backward compatibility — existing
``from spc_app.spc_engine.control_charts import ...`` callers keep working unchanged.

Do not re-declare a chart function or a TypedDict here — change it in
``quality_core.spc.control_charts`` or the copies drift. AIAG constants and the
I-MR limit formula (``imr_limits``) are cited in ``docs/ASSUMPTIONS_LOG.md``.
"""

from __future__ import annotations

from quality_core.spc.control_charts import (
    CResult,
    CUSUMResult,
    EWMAResult,
    ImrLimits,
    ImrResult,
    PResult,
    UResult,
    XbarRResult,
    XbarSResult,
    compute_c,
    compute_cusum,
    compute_ewma,
    compute_imr,
    compute_p,
    compute_u,
    compute_xbar_r,
    compute_xbar_s,
    imr_limits,
)

__all__ = [
    "CResult",
    "CUSUMResult",
    "EWMAResult",
    "ImrLimits",
    "ImrResult",
    "PResult",
    "UResult",
    "XbarRResult",
    "XbarSResult",
    "compute_c",
    "compute_cusum",
    "compute_ewma",
    "compute_imr",
    "compute_p",
    "compute_u",
    "compute_xbar_r",
    "compute_xbar_s",
    "imr_limits",
]
