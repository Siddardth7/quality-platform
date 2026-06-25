"""Shared schema contracts for Quality Platform apps.

`fmea` holds the FMEA row/dataset models — the single source of truth for field
types, range constraints (`strict=True`, S/O/D in 1–10), the `reject_blank`
validator, the derived `RPN` property, and the dataset-level duplicate-ID rule.
The FMEA app re-exports these from `fmea_app.schema`, so promoting them here is a
zero-behaviour-change move that lets SPC and the future Control Plan share one
schema package — mirroring how `quality_core.io` consolidates export + ingest.
"""

from quality_core.schema.fmea import FMEADataset, FMEARow

__all__ = [
    "FMEARow",
    "FMEADataset",
]
