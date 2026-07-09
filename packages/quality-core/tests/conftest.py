"""
conftest.py
Shared FMEA test fixtures for the quality_core.schema suites, so the canonical
"valid row" and its factories are defined once instead of copied across
test_schema and test_relational.
"""
from __future__ import annotations

from collections.abc import Callable

import pytest
from quality_core.schema import FMEADataset, FMEARow

VALID_ROW: dict[str, object] = {
    "ID": 1,
    "Process_Step": "Mix",
    "Component": "Resin",
    "Function": "Bond layers",
    "Failure_Mode": "Incomplete cure",
    "Effect": "Delamination",
    "Severity": 8,
    "Cause": "Low temperature",
    "Occurrence": 4,
    "Current_Control": "Oven thermocouple",
    "Detection": 5,
}


@pytest.fixture
def make_row() -> Callable[..., FMEARow]:
    """Factory: build a valid FMEARow, applying any field overrides."""

    def _make(**overrides: object) -> FMEARow:
        return FMEARow(**{**VALID_ROW, **overrides})  # type: ignore[arg-type]

    return _make


@pytest.fixture
def make_dataset() -> Callable[..., FMEADataset]:
    """Factory: build an FMEADataset from per-row override dicts."""

    def _make(*rows: dict[str, object]) -> FMEADataset:
        return FMEADataset(rows=[FMEARow(**{**VALID_ROW, **r}) for r in rows])  # type: ignore[arg-type]

    return _make
