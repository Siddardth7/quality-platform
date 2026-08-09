"""Control chart rule detection.

The Western Electric / Nelson detectors now live in
``quality_core.spc.rule_detection`` so SECOM and the future API run the same rules
this app does, without importing sideways into it (audit A12, #205). This module
re-exports that API for backward compatibility — existing
``from spc_app.spc_engine.rule_detection import ...`` callers keep working
unchanged. Never re-implement a rule here.
"""

from __future__ import annotations

from quality_core.spc.rule_detection import (
    NELSON_LABELS,
    SHEWHART_CHART_TYPES,
    WE_LABELS,
    detect_nelson_violations,
    detect_violations,
    detect_we_violations,
)

__all__ = [
    "NELSON_LABELS",
    "SHEWHART_CHART_TYPES",
    "WE_LABELS",
    "detect_nelson_violations",
    "detect_violations",
    "detect_we_violations",
]
