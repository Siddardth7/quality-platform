"""
fmea.py
Pydantic v2 domain models for FMEA data validation.
Single source of truth for field types, constraints, and dataset-level rules.
"""
from __future__ import annotations

from typing import Annotated

import pydantic

from quality_core.schema._base import StrictModel, find_duplicates


class FMEARow(StrictModel):
    ID:              Annotated[int, pydantic.Field(gt=0)]
    Process_Step:    Annotated[str, pydantic.Field(min_length=1, max_length=2000)]
    Component:       Annotated[str, pydantic.Field(min_length=1, max_length=2000)]
    Function:        Annotated[str, pydantic.Field(min_length=1, max_length=2000)]
    Failure_Mode:    Annotated[str, pydantic.Field(min_length=1, max_length=2000)]
    Effect:          Annotated[str, pydantic.Field(min_length=1, max_length=2000)]
    Severity:        Annotated[int, pydantic.Field(ge=1, le=10)]
    Cause:           Annotated[str, pydantic.Field(min_length=1, max_length=2000)]
    Occurrence:      Annotated[int, pydantic.Field(ge=1, le=10)]
    Current_Control: Annotated[str, pydantic.Field(min_length=1, max_length=2000)]
    Detection:       Annotated[int, pydantic.Field(ge=1, le=10)]

    @property
    def RPN(self) -> int:
        return self.Severity * self.Occurrence * self.Detection


class FMEADataset(pydantic.BaseModel):
    rows: list[FMEARow]

    @pydantic.model_validator(mode="after")
    def check_no_duplicate_ids(self) -> "FMEADataset":
        dupes = find_duplicates(row.ID for row in self.rows)
        if dupes:
            raise ValueError(f"duplicate IDs found: {dupes}")
        return self
