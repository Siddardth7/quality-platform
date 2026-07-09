"""
tests/test_relational.py
Tests for quality_core/schema/relational.py — the relational FMEA domain model
and its flat ↔ relational adapters (W05-2).

The headline guarantee is loss-less round-tripping: the demo dataset converts to
the nested Function → FailureMode → Effect/Cause/Control model and back with all
canonical columns intact. The rest locks the structural invariants (S/O/D placed
per AIAG, ≥1 effect/cause/control per failure mode, ID uniqueness, link
referential integrity) and the deduplication behaviour of the adapter.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path

import pydantic
import pytest
from quality_core.schema import (
    Cause,
    Control,
    Effect,
    FailureLink,
    FailureMode,
    FMEADataset,
    FMEARow,
    Function,
    RelationalFMEA,
    flat_to_relational,
    relational_to_flat,
)

DEMO_CSV = (
    Path(__file__).resolve().parents[3]
    / "apps"
    / "fmea"
    / "data"
    / "composite_panel_fmea_demo.csv"
)

INT_COLUMNS = ("ID", "Severity", "Occurrence", "Detection")

DatasetFactory = Callable[..., FMEADataset]


def load_demo_dataset() -> FMEADataset:
    with DEMO_CSV.open(newline="", encoding="utf-8") as fh:
        records = list(csv.DictReader(fh))
    rows = [
        FMEARow(**{**rec, **{col: int(rec[col]) for col in INT_COLUMNS}})  # type: ignore[arg-type]
        for rec in records
    ]
    return FMEADataset(rows=rows)


# --- Round-trip: the headline guarantee ---------------------------------------


def test_demo_dataset_round_trips_losslessly() -> None:
    flat = load_demo_dataset()
    back = relational_to_flat(flat_to_relational(flat))
    original = sorted(flat.rows, key=lambda r: r.ID)
    assert [r.model_dump() for r in back.rows] == [r.model_dump() for r in original]


def test_round_trip_with_shared_entities_and_scattered_rows(
    make_dataset: DatasetFactory,
) -> None:
    # Two rows of one failure mode share the same effect (dedup path), and rows
    # of the same function arrive non-contiguously (regrouping path).
    flat = make_dataset(
        {"ID": 3},
        {"ID": 1, "Function": "Seal edge", "Failure_Mode": "Void"},
        {"ID": 2, "Cause": "Contamination", "Occurrence": 2},  # same effect as ID 3
    )
    back = relational_to_flat(flat_to_relational(flat))
    assert [r.model_dump() for r in back.rows] == [
        r.model_dump() for r in sorted(flat.rows, key=lambda r: r.ID)
    ]


def test_empty_dataset_round_trips() -> None:
    empty = FMEADataset(rows=[])
    assert relational_to_flat(flat_to_relational(empty)).rows == []


# --- flat_to_relational: grouping, dedup, stable IDs ---------------------------


def test_grouping_and_deduplication(make_dataset: DatasetFactory) -> None:
    flat = make_dataset(
        {"ID": 1},
        {"ID": 2, "Cause": "Contamination", "Occurrence": 2},  # same FM, new cause
        {"ID": 3, "Function": "Seal edge"},  # new function
    )
    rel = flat_to_relational(flat)
    assert len(rel.functions) == 2
    fm = rel.functions[0].failure_modes[0]
    assert len(fm.effects) == 1  # shared effect deduplicated
    assert len(fm.causes) == 2
    assert len(fm.controls) == 1
    assert len(fm.links) == 2


def test_ids_are_deterministic_and_hierarchical(make_dataset: DatasetFactory) -> None:
    rel = flat_to_relational(make_dataset({"ID": 1}))
    fn = rel.functions[0]
    fm = fn.failure_modes[0]
    assert fn.id == "F1"
    assert fm.id == "F1-M1"
    assert fm.effects[0].id == "F1-M1-E1"
    assert fm.causes[0].id == "F1-M1-C1"
    assert fm.controls[0].id == "F1-M1-CT1"
    assert fm.links[0] == FailureLink(
        row_id=1, effect_id="F1-M1-E1", cause_id="F1-M1-C1", control_id="F1-M1-CT1"
    )


def test_same_text_different_rating_is_a_distinct_entity(
    make_dataset: DatasetFactory,
) -> None:
    rel = flat_to_relational(make_dataset({"ID": 1}, {"ID": 2, "Severity": 9}))
    fm = rel.functions[0].failure_modes[0]
    assert len(fm.effects) == 2  # same description, different severity


def test_sod_placement_follows_aiag(make_dataset: DatasetFactory) -> None:
    rel = flat_to_relational(make_dataset({"ID": 1}))
    fm = rel.functions[0].failure_modes[0]
    assert fm.effects[0].severity == 8
    assert fm.causes[0].occurrence == 4
    assert fm.controls[0].detection == 5


# --- Structural invariants ------------------------------------------------------


def _valid_fm_kwargs() -> dict[str, object]:
    return {
        "id": "F1-M1",
        "description": "Incomplete cure",
        "effects": [Effect(id="E1", description="Delamination", severity=8)],
        "causes": [Cause(id="C1", description="Low temperature", occurrence=4)],
        "controls": [Control(id="CT1", description="Oven thermocouple", detection=5)],
        "links": [FailureLink(row_id=1, effect_id="E1", cause_id="C1", control_id="CT1")],
    }


def _valid_function(fm: FailureMode) -> Function:
    return Function(
        id="F1",
        process_step="Mix",
        component="Resin",
        description="Bond layers",
        failure_modes=[fm],
    )


@pytest.mark.parametrize("field", ["effects", "causes", "controls", "links"])
def test_failure_mode_requires_at_least_one_of_each(field: str) -> None:
    with pytest.raises(pydantic.ValidationError, match="at least 1"):
        FailureMode(**{**_valid_fm_kwargs(), field: []})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "entity", "label"),
    [
        ("effects", Effect(id="E1", description="Other", severity=2), "effect"),
        ("causes", Cause(id="C1", description="Other", occurrence=2), "cause"),
        ("controls", Control(id="CT1", description="Other", detection=2), "control"),
    ],
)
def test_duplicate_entity_ids_rejected(field: str, entity: object, label: str) -> None:
    kwargs = _valid_fm_kwargs()
    kwargs[field] = [*kwargs[field], entity]  # type: ignore[misc]
    with pytest.raises(pydantic.ValidationError, match=f"duplicate {label} IDs"):
        FailureMode(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("link_field", ["effect_id", "cause_id", "control_id"])
def test_link_to_unknown_entity_rejected(link_field: str) -> None:
    kwargs = _valid_fm_kwargs()
    link = FailureLink(
        **{
            "row_id": 2,
            "effect_id": "E1",
            "cause_id": "C1",
            "control_id": "CT1",
            link_field: "MISSING",
        }  # type: ignore[arg-type]
    )
    kwargs["links"] = [*kwargs["links"], link]  # type: ignore[misc]
    with pytest.raises(pydantic.ValidationError, match="unknown .* ID 'MISSING'"):
        FailureMode(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "label", "entity"),
    [
        ("effects", "effect", Effect(id="E2", description="Blistering", severity=3)),
        ("causes", "cause", Cause(id="C2", description="Overmix", occurrence=3)),
        ("controls", "control", Control(id="CT2", description="Visual check", detection=3)),
    ],
)
def test_unreferenced_entity_rejected(field: str, label: str, entity: object) -> None:
    # An entity with no incoming link would be silently dropped by
    # relational_to_flat, breaking the round-trip — the model must reject it.
    kwargs = _valid_fm_kwargs()
    kwargs[field] = [*kwargs[field], entity]  # type: ignore[misc]
    with pytest.raises(pydantic.ValidationError, match=f"unreferenced {label} ID"):
        FailureMode(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "label", "entities"),
    [
        (
            "effects",
            "effect",
            [
                Effect(id="E1", description="Delamination", severity=8),
                Effect(id="E2", description="Delamination", severity=8),
            ],
        ),
        (
            "causes",
            "cause",
            [
                Cause(id="C1", description="Low temperature", occurrence=4),
                Cause(id="C2", description="Low temperature", occurrence=4),
            ],
        ),
        (
            "controls",
            "control",
            [
                Control(id="CT1", description="Oven thermocouple", detection=5),
                Control(id="CT2", description="Oven thermocouple", detection=5),
            ],
        ),
    ],
)
def test_duplicate_description_rating_pair_rejected(
    field: str, label: str, entities: object
) -> None:
    # Two entities with the same (description, rating) but different IDs would
    # merge on flat_to_relational, so the model forbids the pair collision.
    kwargs = _valid_fm_kwargs()
    kwargs[field] = entities
    with pytest.raises(
        pydantic.ValidationError, match=rf"duplicate {label} \(description, rating\)"
    ):
        FailureMode(**kwargs)  # type: ignore[arg-type]


def test_duplicate_failure_mode_ids_rejected() -> None:
    fm = FailureMode(**_valid_fm_kwargs())  # type: ignore[arg-type]
    with pytest.raises(pydantic.ValidationError, match="duplicate failure-mode IDs"):
        Function(
            id="F1",
            process_step="Mix",
            component="Resin",
            description="Bond layers",
            failure_modes=[fm, fm],
        )


def test_duplicate_function_ids_rejected() -> None:
    fn = _valid_function(FailureMode(**_valid_fm_kwargs()))  # type: ignore[arg-type]
    with pytest.raises(pydantic.ValidationError, match="duplicate function IDs"):
        RelationalFMEA(functions=[fn, fn])


def test_duplicate_row_ids_across_functions_rejected() -> None:
    fm = FailureMode(**_valid_fm_kwargs())  # type: ignore[arg-type]
    fn1 = _valid_function(fm)
    fn2 = fn1.model_copy(update={"id": "F2", "description": "Seal edge"})
    with pytest.raises(pydantic.ValidationError, match="duplicate row IDs"):
        RelationalFMEA(functions=[fn1, fn2])


# --- Field-level constraints ------------------------------------------------------


def test_blank_description_rejected() -> None:
    with pytest.raises(pydantic.ValidationError, match="blank"):
        Effect(id="E1", description="   ", severity=8)


def test_descriptions_are_stripped() -> None:
    assert Effect(id="E1", description="  Delamination ", severity=8).description == (
        "Delamination"
    )


@pytest.mark.parametrize("severity", [0, 11])
def test_rating_out_of_range_rejected(severity: int) -> None:
    with pytest.raises(pydantic.ValidationError):
        Effect(id="E1", description="Delamination", severity=severity)


def test_non_positive_row_id_rejected() -> None:
    with pytest.raises(pydantic.ValidationError):
        FailureLink(row_id=0, effect_id="E1", cause_id="C1", control_id="CT1")
