"""
schema.py
FMEA domain models — now owned by the shared core.

The `FMEARow` / `FMEADataset` Pydantic models were promoted into
`quality_core.schema` (W05-1) so SPC and the future Control Plan can share the
same schema contracts. This module re-exports them verbatim, so existing imports
(`from fmea_app.schema import FMEARow`) keep working with zero behaviour change.
"""
from __future__ import annotations

from quality_core.schema import FMEADataset, FMEARow

__all__ = [
    "FMEARow",
    "FMEADataset",
]
