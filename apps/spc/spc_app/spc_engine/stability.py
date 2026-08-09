"""Stability gate for capability studies (docs/ASSUMPTIONS_LOG.md RULE 7).

The gate itself now lives in ``quality_core.spc.stability`` so every tool shares
one copy instead of importing sideways into this app (audit A12, #205, PR 2 of 3).
This module re-exports it for backward compatibility — existing
``from spc_app.spc_engine.stability import ...`` callers keep working unchanged.

Do not re-declare ``assess_stability`` or ``stability_fields`` here — change them
in ``quality_core.spc.stability`` or the copies drift. The ``kind="stable"`` sort
(#191) and its justification live there too.
"""

from __future__ import annotations

from quality_core.spc.stability import (
    NOT_ASSESSED_NOTE,
    ChartType,
    assess_stability,
    stability_fields,
)

__all__ = [
    "NOT_ASSESSED_NOTE",
    "ChartType",
    "assess_stability",
    "stability_fields",
]
