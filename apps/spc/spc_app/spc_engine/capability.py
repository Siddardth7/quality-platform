"""Process capability calculations (docs/ASSUMPTIONS_LOG.md RULE 14).

The engine now lives in ``quality_core.spc.capability`` so every tool shares one
copy instead of importing sideways into this app (audit A12, #205, PR 3 of 3).
This module re-exports it for backward compatibility — existing
``from spc_app.spc_engine.capability import ...`` callers keep working unchanged.

Do not re-declare ``compute_capability``, ``compute_capability_study`` or
``normality_test`` here — change them in ``quality_core.spc.capability`` or the
copies drift. The non-normal method selection (Box-Cox / Yeo-Johnson / fitted
percentile) and its standards citations live there too.
"""

from __future__ import annotations

from quality_core.spc.capability import (
    CapabilityStudy,
    compute_capability,
    compute_capability_study,
    normality_test,
)

__all__ = [
    "CapabilityStudy",
    "compute_capability",
    "compute_capability_study",
    "normality_test",
]
