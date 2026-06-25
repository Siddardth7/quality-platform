"""
tests/test_schema.py
Tests for quality_core/schema/fmea.py — the shared FMEA schema contracts (W05-1).

These exercise the models directly (not via the FMEA app's re-export shim) so the
`quality_core.schema` coverage gate stands on its own tests, mirroring how
`quality_core.io` is self-sufficiently covered. They lock the field constraints,
the `reject_blank` validator, the derived `RPN` property, and the dataset-level
duplicate-ID rule that the FMEA pipeline depends on.
"""

from __future__ import annotations

import pydantic
import pytest
from quality_core.schema import FMEADataset, FMEARow

# --- A complete, valid row, reused across tests ------------------------------

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


def _row(**overrides: object) -> FMEARow:
    return FMEARow(**{**VALID_ROW, **overrides})


# --- FMEARow: happy path + derived RPN ---------------------------------------


def test_valid_row_constructs() -> None:
    row = _row()
    assert row.ID == 1
    assert row.Severity == 8


def test_rpn_is_product_of_sod() -> None:
    # RPN = Severity × Occurrence × Detection = 8 × 4 × 5
    assert _row().RPN == 160


# --- reject_blank validator (the three branches) -----------------------------


def test_blank_string_field_is_rejected() -> None:
    with pytest.raises(pydantic.ValidationError, match="must not be blank"):
        _row(Process_Step="   ")


def test_string_field_is_stripped() -> None:
    # The validator strips surrounding whitespace from text fields.
    assert _row(Component="  Resin  ").Component == "Resin"


def test_non_string_value_passes_through_validator() -> None:
    # Strict typing rejects a non-int ID before/at validation, proving the
    # validator's non-str branch returns the value untouched rather than
    # coercing it. A float ID must raise (strict=True), not silently pass.
    with pytest.raises(pydantic.ValidationError):
        _row(ID=1.5)


# --- Field constraints: strict ints + S/O/D range ----------------------------


def test_severity_above_range_is_rejected() -> None:
    with pytest.raises(pydantic.ValidationError):
        _row(Severity=11)


def test_occurrence_below_range_is_rejected() -> None:
    with pytest.raises(pydantic.ValidationError):
        _row(Occurrence=0)


def test_id_must_be_positive() -> None:
    with pytest.raises(pydantic.ValidationError):
        _row(ID=0)


def test_strict_int_rejects_bool_for_sod() -> None:
    # bool is an int subclass; strict mode must still reject it for S/O/D.
    with pytest.raises(pydantic.ValidationError):
        _row(Detection=True)


# --- FMEADataset: duplicate-ID rule ------------------------------------------


def test_dataset_accepts_unique_ids() -> None:
    ds = FMEADataset(rows=[_row(ID=1), _row(ID=2), _row(ID=3)])
    assert [r.ID for r in ds.rows] == [1, 2, 3]


def test_dataset_rejects_duplicate_ids() -> None:
    with pytest.raises(pydantic.ValidationError, match="duplicate IDs found"):
        FMEADataset(rows=[_row(ID=1), _row(ID=2), _row(ID=1)])
