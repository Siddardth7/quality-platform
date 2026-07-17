"""
schema.py
Measurement System Analysis — gage-study upload validation schema.

Defines the Pydantic row/dataset models and the shared :class:`TableSchema` that
the uploader routes through, so a malformed CSV gives a friendly, row-addressed
error instead of crashing a downstream call. Mirrors SPC's ``schema.py`` discipline,
plugged into the cross-app ``quality_core.io`` validated-ingest boundary.

The schema encodes the **crossed Gage R&R** data structure in long/tidy form: one
row per measurement — each *part* measured by each *appraiser* over multiple
*trials* (replications). Study size (parts × appraisers × trials) is NOT constrained:
AIAG's 10×3×3 is a recommendation, and Week-9 SECOM constructs its own structure, so
arbitrary counts are accepted.

Tolerance (USL/LSL) is deliberately NOT a CSV column: it is a *study-level* value
captured as page number inputs, not a per-measurement value, so keeping it out of
the row schema avoids per-row inconsistency. Ingest validates row types plus the
uniqueness of each ``(part, appraiser, trial)`` triple — a duplicate triple means a
double-entered measurement. Balance (every part measured by every appraiser the same
number of trials) is NOT enforced here; that is a modelling concern for the R&R math,
which is out of scope for this scaffold.
"""

from __future__ import annotations

from typing import Annotated, BinaryIO

import pandas as pd
import pydantic
from quality_core.io import IngestError, TableSchema, load_table
from quality_core.schema._base import find_duplicates

__all__ = [
    "GageStudyRow",
    "GageStudyDataset",
    "GAGE_STUDY_SCHEMA",
    "load_gage_study_csv",
    "IngestError",
]


class GageStudyRow(pydantic.BaseModel):
    """One measurement in a crossed gage study.

    Non-strict on purpose: a CSV read by pandas yields numpy scalars (and the
    occasional string), so values are coerced (e.g. ``"3"``/``3.0`` → ``3``)
    rather than rejected for not being a native Python type. Blank cells arrive
    as ``None`` (the ingest boundary normalises NaN→None) and are rejected with a
    clear message.
    """

    part: Annotated[str, pydantic.Field(min_length=1, max_length=200)]
    appraiser: Annotated[str, pydantic.Field(min_length=1, max_length=200)]
    trial: Annotated[int, pydantic.Field(ge=1)]
    # allow_inf_nan=False rejects an 'inf' cell (NaN is already normalised to None
    # by the ingest boundary) so a non-finite value fails cleanly instead of
    # poisoning the later R&R math with inf/NaN.
    measurement: Annotated[float, pydantic.Field(allow_inf_nan=False)]

    @pydantic.field_validator("part", "appraiser", mode="before")
    @classmethod
    def reject_blank_label(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            raise ValueError("must not be blank or whitespace-only")
        return v.strip() if isinstance(v, str) else v


class GageStudyDataset(pydantic.BaseModel):
    """Cross-row rules for a gage study.

    A ``(part, appraiser, trial)`` triple must be unique: each replicate is a
    single measurement, so a repeated triple means a double-entered row. Balance
    is intentionally not checked here (see module docstring).
    """

    rows: list[GageStudyRow]

    @pydantic.model_validator(mode="after")
    def check_unique_triples(self) -> "GageStudyDataset":
        dupes = find_duplicates(
            (row.part, row.appraiser, row.trial) for row in self.rows
        )
        if dupes:
            raise ValueError(f"duplicate (part, appraiser, trial) rows found: {dupes}")
        return self


GAGE_STUDY_SCHEMA = TableSchema(
    name="Gage R&R",
    row_model=GageStudyRow,
    required_columns=("part", "appraiser", "trial", "measurement"),
    dataset_model=GageStudyDataset,
    template_hint="data/gage_rr_template.csv",
)


def load_gage_study_csv(source: str | BinaryIO) -> pd.DataFrame:
    """Read + validate an uploaded gage-study ``.csv`` against :data:`GAGE_STUDY_SCHEMA`.

    Returns the validated DataFrame unchanged. Raises :class:`IngestError` (a
    ``ValueError`` subclass) with a user-safe message on a malformed upload, for
    the page to surface via ``st.error``.
    """
    return load_table(source, GAGE_STUDY_SCHEMA)
