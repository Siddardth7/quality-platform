"""Phase I/II control-limit freezing (W10-1, #141).

The freezing logic itself now lives in ``quality_core.spc.phase`` so every tool
shares one copy instead of importing sideways into this app (audit A12, #205,
PR 2 of 3). This module re-exports it for backward compatibility — existing
``from spc_app.spc_engine.phase import ...`` callers keep working unchanged.

Do not re-declare ``freeze_*`` or ``FrozenLimits`` here — change them in
``quality_core.spc.phase`` or the copies drift.
"""

from __future__ import annotations

from quality_core.spc.phase import (
    ExcludedPoint,
    FrozenLimits,
    freeze_imr,
    freeze_xbar_r,
    freeze_xbar_s,
)

__all__ = [
    "ExcludedPoint",
    "FrozenLimits",
    "freeze_imr",
    "freeze_xbar_r",
    "freeze_xbar_s",
]
