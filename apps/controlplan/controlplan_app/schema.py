"""
schema.py
Control Plan — upload validation schema.

Defines the Pydantic row/dataset models and the shared :class:`TableSchema` that
the uploader routes through, so a malformed CSV gives a friendly, row-addressed
error instead of crashing a downstream call. Mirrors MSA's ``schema.py`` discipline
(row **and** dataset model, uniqueness via ``find_duplicates``), plugged into the
cross-app ``quality_core.io`` validated-ingest boundary.

The field set — characteristic, spec/tolerance (LSL/target/USL), measurement
method, sample size/frequency, control method (recommended SPC chart), reaction
plan — is the AIAG Control Plan column structure (see ROADMAP.md §4). This issue
introduces no thresholds, indices, or computed values (no Cp/Cpk, no AP table);
it is a typed ingest contract only. ``lsl``/``usl``/``target``/``recommended_chart``
are nullable — not every characteristic has a tolerance or is SPC-monitored (e.g.
attribute go/no-go, visual) — so they are left out of ``required_columns``, but
``load_control_plan_csv`` still rejects a bad value in any of them when the column
is present in the upload (see :func:`_reject_bad_optional_values`). FMEA → Control
Plan mapping (W06-2) and the SPC chart type set consumption (Week 7) build on this
contract but are out of scope here.

This schema stays app-local (not promoted into ``quality_core.schema``) until
W06-2/W07 exercise and stabilise its shape — see the Week-5 deferred-extraction
precedent MSA also followed.

``source_cause_id`` (W07-2, #89) is a further nullable field: the durable
SPC->FMEA join key a row carries back to the FMEA cause it was derived from
(``controlplan_app.connector.build_control_plan``). It has no cross-row
uniqueness rule (unlike ``characteristic``) — multiple rows may legitimately
point at the same cause is not expected in practice (one row per failure mode,
one worst-risk cause each) but is not forbidden, since a manually-added row
with no source is simply ``None``.
"""

from __future__ import annotations

from typing import Annotated, Any, BinaryIO, Literal, cast

import pandas as pd
import pydantic
from quality_core.io import IngestError, TableSchema, load_table
from quality_core.schema._base import find_duplicates

__all__ = [
    "SPCChart",
    "ControlPlanRow",
    "ControlPlanDataset",
    "CONTROL_PLAN_SCHEMA",
    "load_control_plan_csv",
    "IngestError",
]

#: SPC engine chart keys a control method may recommend — the variable charts
#: (`apps/spc/spc_app/pages/control_charts.py`) plus the attribute charts SPC's
#: engine computes (`compute_p`/`compute_c`/`compute_u`). Internal SPC keys, not a
#: standard — see the module docstring.
SPCChart = Literal["Xbar-R", "Xbar-S", "I-MR", "p", "c", "u"]


class ControlPlanRow(pydantic.BaseModel):
    """One characteristic row of a Control Plan.

    Non-strict on purpose: a CSV read by pandas yields numpy scalars, so values
    are coerced (e.g. ``"5"``/``5.0`` → ``5``) rather than rejected for not being
    a native Python type. Blank cells arrive as ``None`` (the ingest boundary
    normalises NaN→None) and are rejected with a clear message.
    """

    characteristic: Annotated[str, pydantic.Field(min_length=1, max_length=200)]
    lsl: Annotated[float | None, pydantic.Field(default=None, allow_inf_nan=False)]
    usl: Annotated[float | None, pydantic.Field(default=None, allow_inf_nan=False)]
    target: Annotated[float | None, pydantic.Field(default=None, allow_inf_nan=False)]
    measurement_method: Annotated[str, pydantic.Field(min_length=1, max_length=200)]
    sample_size: Annotated[int, pydantic.Field(ge=1)]
    # Free text: "per shift" / "hourly" / "each lot" — not an enum, control plans
    # phrase frequency too many ways to constrain usefully.
    frequency: Annotated[str, pydantic.Field(min_length=1, max_length=200)]
    recommended_chart: SPCChart | None = None
    reaction_plan: Annotated[str, pydantic.Field(min_length=1, max_length=2000)]
    #: Nullable join key back to the FMEA cause this row's control derives from
    #: (OQ1, W07-2 #89) — set by ``controlplan_app.connector.build_control_plan``
    #: from ``_worst_link``'s cause (see ``connector._source_cause_id``). ``None``
    #: for a manually-added/edited row with no FMEA source. Persisted (not a
    #: session-only lookup) so the SPC->FMEA linkage survives CSV export/reimport.
    source_cause_id: Annotated[str | None, pydantic.Field(default=None, max_length=300)] = None

    @pydantic.field_validator(
        "characteristic", "measurement_method", "frequency", "reaction_plan", mode="before"
    )
    @classmethod
    def reject_blank(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            raise ValueError("must not be blank or whitespace-only")
        return v.strip() if isinstance(v, str) else v

    @pydantic.field_validator("source_cause_id", mode="before")
    @classmethod
    def blank_source_cause_id_to_none(cls, v: object) -> object:
        # A blank cell is the normal "no FMEA source" shape (not an error, unlike
        # the required string fields above) — coerce it to None rather than reject.
        if isinstance(v, str) and not v.strip():
            return None
        return v.strip() if isinstance(v, str) else v

    @pydantic.model_validator(mode="after")
    def check_tolerance(self) -> "ControlPlanRow":
        if self.usl is not None and self.lsl is not None and self.usl <= self.lsl:
            raise ValueError("usl must be greater than lsl")
        if (
            self.target is not None
            and self.lsl is not None
            and self.usl is not None
            and (self.target < self.lsl or self.target > self.usl)
        ):
            raise ValueError("target must be within [lsl, usl]")
        return self


class ControlPlanDataset(pydantic.BaseModel):
    """Cross-row rules for a Control Plan.

    ``characteristic`` is the row identity — a repeated characteristic is a
    duplicate control, so it must be unique across the dataset.
    """

    rows: list[ControlPlanRow]

    @pydantic.model_validator(mode="after")
    def check_unique_characteristics(self) -> "ControlPlanDataset":
        dupes = find_duplicates(row.characteristic for row in self.rows)
        if dupes:
            raise ValueError(f"duplicate characteristic rows found: {dupes}")
        return self


CONTROL_PLAN_SCHEMA = TableSchema(
    name="Control Plan",
    row_model=ControlPlanRow,
    required_columns=(
        "characteristic",
        "measurement_method",
        "sample_size",
        "frequency",
        "reaction_plan",
    ),
    dataset_model=ControlPlanDataset,
    template_hint="data/control_plan_template.csv",
)


#: Optional tolerance/chart columns excluded from ``required_columns`` (nullable —
#: see the module docstring), so ``quality_core.io.load_table`` never reads or
#: validates them. Checked separately, below, when present in the upload.
_OPTIONAL_COLUMNS: tuple[str, ...] = (
    "lsl", "usl", "target", "recommended_chart", "source_cause_id",
)


def _reject_bad_optional_values(df: pd.DataFrame) -> None:
    """Reject bad ``lsl``/``usl``/``target``/``recommended_chart`` values, if present.

    These columns are deliberately nullable and left out of ``required_columns``
    (an attribute/visual characteristic has no tolerance or chart), so
    ``load_table`` never routes them into ``ControlPlanRow`` for validation. If
    the uploaded CSV carries any of them, re-run each row through
    ``ControlPlanRow`` (reusing its existing ``usl``/``target``/chart validators
    rather than duplicating the rules) so a bad value is still rejected.

    A column absent from the CSV entirely is skipped — that is the normal,
    valid "not SPC-monitored" shape and needs no re-check.
    """
    present = [col for col in _OPTIONAL_COLUMNS if col in df.columns]
    if not present:
        return

    columns = [*CONTROL_PLAN_SCHEMA.required_columns, *present]
    for offset, record in enumerate(df[columns].to_dict(orient="records")):
        clean = {str(key): (None if pd.isna(value) else value) for key, value in record.items()}
        try:
            ControlPlanRow(**cast("dict[str, Any]", clean))
        except pydantic.ValidationError as exc:
            first = exc.errors()[0]
            column = ".".join(str(part) for part in first.get("loc", ()))
            where = f"Row {offset + 2}" + (f", column '{column}'" if column else "")
            msg = first.get("msg", "invalid value")
            for prefix in ("Value error, ", "Assertion failed, "):
                msg = msg.removeprefix(prefix)
            # A field-level error (loc set) echoes the one bad cell; a row-level
            # validator (e.g. usl<lsl, target-out-of-bounds) has no single loc, so
            # echoing the whole row would be noisy — the message names the rule.
            echo = f" (got {first.get('input')!r})" if column else ""
            raise IngestError(
                f"{where}: {msg}{echo}."
                f" Check your data against the template at {CONTROL_PLAN_SCHEMA.template_hint}."
            ) from exc


def load_control_plan_csv(source: str | BinaryIO) -> pd.DataFrame:
    """Read + validate an uploaded Control Plan ``.csv`` against :data:`CONTROL_PLAN_SCHEMA`.

    Returns the validated DataFrame unchanged. Raises :class:`IngestError` (a
    ``ValueError`` subclass) with a user-safe message on a malformed upload, for
    the page to surface via ``st.error``. Also rejects a bad ``lsl``/``usl``/
    ``target``/``recommended_chart`` value when that optional column is present
    in the upload — see :func:`_reject_bad_optional_values`.
    """
    df = load_table(source, CONTROL_PLAN_SCHEMA)
    _reject_bad_optional_values(df)
    return df
