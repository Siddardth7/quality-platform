"""
relational.py
Relational FMEA domain model (W05-2): Function → FailureMode → Effect / Cause /
Control, per AIAG/VDA structure — Severity lives on the Effect, Occurrence on
the Cause, Detection on the Control.

`flat_to_relational` / `relational_to_flat` adapt to and from the flat
`FMEADataset` row representation loss-lessly on the canonical columns (row
*content*, not row *order* — the flat output is ID-ordered, canonically). Within
a failure mode, identical effects/causes/controls are deduplicated into single
entities, and each original flat row is kept as a `FailureLink` tying one
(effect, cause, control) triple to its row ID, so every row is reconstructed
exactly. Round-tripping is loss-less in both directions because the model
enforces the same canonical invariants the adapter produces: within a failure
mode, IDs are unique, no two entities share a (description, rating) pair, and
every entity is referenced by at least one link.
"""
from __future__ import annotations

from typing import Annotated

import pydantic

from quality_core.schema._base import StrictModel, find_duplicates
from quality_core.schema.action import Action
from quality_core.schema.fmea import FMEADataset, FMEARow

EntityId = Annotated[str, pydantic.Field(min_length=1, max_length=100)]
Text = Annotated[str, pydantic.Field(min_length=1, max_length=2000)]
Rating = Annotated[int, pydantic.Field(ge=1, le=10)]


class Effect(StrictModel):
    id: EntityId
    description: Text
    severity: Rating


class Cause(StrictModel):
    id: EntityId
    description: Text
    occurrence: Rating


class Control(StrictModel):
    id: EntityId
    description: Text
    detection: Rating


class FailureLink(StrictModel):
    """One original flat row: ties an (effect, cause, control) triple to its ID.

    An optional `action` records the AIAG optimization step taken on this failure
    (owner, status, re-rated S/O/D); its effectiveness is scored against this
    link's effect.severity / cause.occurrence / control.detection. Actions live
    outside the canonical columns, so they don't affect the flat round-trip.
    """

    row_id: Annotated[int, pydantic.Field(gt=0)]
    effect_id: EntityId
    cause_id: EntityId
    control_id: EntityId
    action: Action | None = None


class FailureMode(StrictModel):
    id: EntityId
    description: Text
    effects: Annotated[list[Effect], pydantic.Field(min_length=1)]
    causes: Annotated[list[Cause], pydantic.Field(min_length=1)]
    controls: Annotated[list[Control], pydantic.Field(min_length=1)]
    links: Annotated[list[FailureLink], pydantic.Field(min_length=1)]

    @pydantic.model_validator(mode="after")
    def check_ids_and_links(self) -> "FailureMode":
        # Within a failure mode, an entity is identified by its (description,
        # rating) pair; two entities sharing that pair under different IDs would
        # merge on flat_to_relational, so forbid it to keep the round-trip
        # loss-less in both directions. IDs must also be unique.
        for label, ids, pairs in (
            ("effect", [e.id for e in self.effects],
             [(e.description, e.severity) for e in self.effects]),
            ("cause", [c.id for c in self.causes],
             [(c.description, c.occurrence) for c in self.causes]),
            ("control", [c.id for c in self.controls],
             [(c.description, c.detection) for c in self.controls]),
        ):
            id_dupes = find_duplicates(ids)
            if id_dupes:
                raise ValueError(f"duplicate {label} IDs found: {id_dupes}")
            pair_dupes = find_duplicates(pairs)
            if pair_dupes:
                raise ValueError(f"duplicate {label} (description, rating): {pair_dupes}")
        effect_ids = {e.id for e in self.effects}
        cause_ids = {c.id for c in self.causes}
        control_ids = {c.id for c in self.controls}
        for link in self.links:
            if link.effect_id not in effect_ids:
                raise ValueError(f"link row {link.row_id}: unknown effect ID {link.effect_id!r}")
            if link.cause_id not in cause_ids:
                raise ValueError(f"link row {link.row_id}: unknown cause ID {link.cause_id!r}")
            if link.control_id not in control_ids:
                raise ValueError(f"link row {link.row_id}: unknown control ID {link.control_id!r}")
        # No orphans: every entity must be referenced by ≥1 link, or it would be
        # silently dropped by relational_to_flat (which reads only via links).
        for label, defined, referenced in (
            ("effect", effect_ids, {lk.effect_id for lk in self.links}),
            ("cause", cause_ids, {lk.cause_id for lk in self.links}),
            ("control", control_ids, {lk.control_id for lk in self.links}),
        ):
            orphaned = defined - referenced
            if orphaned:
                raise ValueError(f"unreferenced {label} ID(s): {sorted(orphaned)}")
        return self


class Function(StrictModel):
    id: EntityId
    process_step: Text
    component: Text
    description: Text
    failure_modes: Annotated[list[FailureMode], pydantic.Field(min_length=1)]

    @pydantic.model_validator(mode="after")
    def check_unique_failure_mode_ids(self) -> "Function":
        dupes = find_duplicates(fm.id for fm in self.failure_modes)
        if dupes:
            raise ValueError(f"duplicate failure-mode IDs found: {dupes}")
        return self


class RelationalFMEA(StrictModel):
    functions: list[Function]

    @pydantic.model_validator(mode="after")
    def check_global_uniqueness(self) -> "RelationalFMEA":
        dupes = find_duplicates(fn.id for fn in self.functions)
        if dupes:
            raise ValueError(f"duplicate function IDs found: {dupes}")
        row_dupes = find_duplicates(
            link.row_id
            for fn in self.functions
            for fm in fn.failure_modes
            for link in fm.links
        )
        if row_dupes:
            raise ValueError(f"duplicate row IDs found: {row_dupes}")
        return self


# ===========================================================================
# Adapters — flat FMEADataset ↔ relational model
# ===========================================================================


class _FMBucket:
    """Mutable per-failure-mode accumulator used while grouping flat rows."""

    def __init__(self) -> None:
        # (description, rating) → local entity ID; insertion order = ID order.
        self.effects: dict[tuple[str, int], str] = {}
        self.causes: dict[tuple[str, int], str] = {}
        self.controls: dict[tuple[str, int], str] = {}
        # (row_id, effect_id, cause_id, control_id)
        self.links: list[tuple[int, str, str, str]] = []


def flat_to_relational(dataset: FMEADataset) -> RelationalFMEA:
    """Group flat rows into Function → FailureMode → Effect/Cause/Control.

    Grouping keys: a Function is (Process_Step, Component, Function); a
    FailureMode is its description within that function. Within a failure mode,
    effects/causes/controls with identical (description, rating) are one entity.
    IDs are deterministic by order of first appearance: F1, F1-M1, F1-M1-E1, …
    """
    # (process_step, component, function) → {failure_mode → per-FM buckets}
    functions: dict[tuple[str, str, str], dict[str, _FMBucket]] = {}
    for row in dataset.rows:
        fkey = (row.Process_Step, row.Component, row.Function)
        modes = functions.setdefault(fkey, {})
        fm = modes.setdefault(row.Failure_Mode, _FMBucket())
        e_id = fm.effects.setdefault((row.Effect, row.Severity), f"E{len(fm.effects) + 1}")
        c_id = fm.causes.setdefault((row.Cause, row.Occurrence), f"C{len(fm.causes) + 1}")
        ct_id = fm.controls.setdefault(
            (row.Current_Control, row.Detection), f"CT{len(fm.controls) + 1}"
        )
        fm.links.append((row.ID, e_id, c_id, ct_id))

    out: list[Function] = []
    for f_idx, ((step, component, func), modes) in enumerate(functions.items(), start=1):
        f_id = f"F{f_idx}"
        fms: list[FailureMode] = []
        for m_idx, (mode_desc, fm) in enumerate(modes.items(), start=1):
            m_id = f"{f_id}-M{m_idx}"
            fms.append(
                FailureMode(
                    id=m_id,
                    description=mode_desc,
                    effects=[
                        Effect(id=f"{m_id}-{eid}", description=desc, severity=sev)
                        for (desc, sev), eid in fm.effects.items()
                    ],
                    causes=[
                        Cause(id=f"{m_id}-{cid}", description=desc, occurrence=occ)
                        for (desc, occ), cid in fm.causes.items()
                    ],
                    controls=[
                        Control(id=f"{m_id}-{ctid}", description=desc, detection=det)
                        for (desc, det), ctid in fm.controls.items()
                    ],
                    links=[
                        FailureLink(
                            row_id=rid,
                            effect_id=f"{m_id}-{eid}",
                            cause_id=f"{m_id}-{cid}",
                            control_id=f"{m_id}-{ctid}",
                        )
                        for rid, eid, cid, ctid in fm.links
                    ],
                )
            )
        out.append(
            Function(
                id=f_id,
                process_step=step,
                component=component,
                description=func,
                failure_modes=fms,
            )
        )
    return RelationalFMEA(functions=out)


def relational_to_flat(model: RelationalFMEA) -> FMEADataset:
    """Expand the relational model back to flat rows, sorted by row ID.

    Each `FailureLink` becomes one `FMEARow`; sorting by ID canonicalises the
    order, so flat → relational → flat reproduces an ID-sorted dataset exactly.
    """
    rows: list[FMEARow] = []
    for fn in model.functions:
        for fm in fn.failure_modes:
            effects = {e.id: e for e in fm.effects}
            causes = {c.id: c for c in fm.causes}
            controls = {c.id: c for c in fm.controls}
            for link in fm.links:
                effect = effects[link.effect_id]
                cause = causes[link.cause_id]
                control = controls[link.control_id]
                rows.append(
                    FMEARow(
                        ID=link.row_id,
                        Process_Step=fn.process_step,
                        Component=fn.component,
                        Function=fn.description,
                        Failure_Mode=fm.description,
                        Effect=effect.description,
                        Severity=effect.severity,
                        Cause=cause.description,
                        Occurrence=cause.occurrence,
                        Current_Control=control.description,
                        Detection=control.detection,
                    )
                )
    rows.sort(key=lambda r: r.ID)
    return FMEADataset(rows=rows)
