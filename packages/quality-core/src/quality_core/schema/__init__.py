"""Shared schema contracts for Quality Platform apps.

`fmea` holds the FMEA row/dataset models — the single source of truth for field
types, range constraints (`strict=True`, S/O/D in 1–10), the `reject_blank`
validator, the derived `RPN` property, and the dataset-level duplicate-ID rule.
The FMEA app re-exports these from `fmea_app.schema`, so promoting them here is a
zero-behaviour-change move that lets SPC and the future Control Plan share one
schema package — mirroring how `quality_core.io` consolidates export + ingest.

`relational` holds the AIAG/VDA-structured domain model (W05-2) — Function →
FailureMode → Effect/Cause/Control with Severity on Effect, Occurrence on Cause,
Detection on Control — plus loss-less `flat_to_relational` / `relational_to_flat`
adapters to and from the flat row representation.

`action` holds action tracking + effectiveness (W05-3): an `Action` (owner, due,
status, optional re-rated S/O/D) and `Action.effectiveness(...)` comparing RPN/AP
before → after via the shared `quality_core.scoring` scorers.
"""

from quality_core.schema.action import Action, ActionStatus, Effectiveness
from quality_core.schema.fmea import FMEADataset, FMEARow
from quality_core.schema.relational import (
    Cause,
    Control,
    Effect,
    FailureLink,
    FailureMode,
    Function,
    RelationalFMEA,
    flat_to_relational,
    relational_to_flat,
)

__all__ = [
    "FMEARow",
    "FMEADataset",
    "Effect",
    "Cause",
    "Control",
    "FailureLink",
    "FailureMode",
    "Function",
    "RelationalFMEA",
    "flat_to_relational",
    "relational_to_flat",
    "Action",
    "ActionStatus",
    "Effectiveness",
]
