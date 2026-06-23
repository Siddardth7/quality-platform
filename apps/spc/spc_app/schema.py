"""
schema.py
Manufacturing SPC Dashboard — upload validation schema.

Defines the Pydantic row model and the shared :class:`TableSchema` that the
uploader routes through, so a malformed CSV gives a friendly, row-addressed
error instead of crashing a downstream pandas/engine call. Mirrors FMEA's
``schema.py`` discipline, but plugged into the cross-app ``quality_core.io``
validated-ingest boundary (W04-2).

The required columns are the ones *every* chart and capability path consumes:
``stream`` (which process), ``subgroup`` (ordering / grouping), and ``value``
(the measurement or count). ``sample_size`` is deliberately NOT required — it is
only meaningful for p/u attribute charts, so demanding it would reject perfectly
valid continuous-measurement uploads (Xbar/I-MR/capability). ``sample_size`` /
``lsl`` / ``usl`` / ``chart_type`` / ``parameter`` pass through unvalidated; the
chart that needs one fails friendly later (the page wraps compute errors).
"""

from __future__ import annotations

from typing import Annotated, BinaryIO

import pandas as pd
import pydantic
from quality_core.io import IngestError, TableSchema, load_table

__all__ = ["SPCRow", "SPC_SCHEMA", "load_spc_csv", "IngestError"]


class SPCRow(pydantic.BaseModel):
    """One row of an SPC dataset.

    Non-strict on purpose: a CSV read by pandas yields numpy scalars (and the
    occasional string), so values are coerced (e.g. ``"5"``/``5.0`` → ``5``)
    rather than rejected for not being a native Python type. Blank cells arrive
    as ``None`` (the ingest boundary normalises NaN→None) and are rejected with a
    clear "valid number/integer" message.
    """

    stream: Annotated[str, pydantic.Field(min_length=1, max_length=200)]
    subgroup: Annotated[int, pydantic.Field(ge=1)]
    # allow_inf_nan=False rejects an 'inf' cell (NaN is already normalised to None
    # by the ingest boundary) so a non-finite value fails cleanly instead of
    # poisoning the chart math with inf/NaN control limits.
    value: Annotated[float, pydantic.Field(allow_inf_nan=False)]

    @pydantic.field_validator("stream", mode="before")
    @classmethod
    def reject_blank_stream(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            raise ValueError("stream must not be blank or whitespace-only")
        return v.strip() if isinstance(v, str) else v


SPC_SCHEMA = TableSchema(
    name="SPC",
    row_model=SPCRow,
    required_columns=("stream", "subgroup", "value"),
    template_hint="data/demo_composites_aerospace.csv",
)


def load_spc_csv(source: str | BinaryIO) -> pd.DataFrame:
    """Read + validate an uploaded SPC ``.csv`` against :data:`SPC_SCHEMA`.

    Returns the validated DataFrame unchanged. Raises :class:`IngestError` (a
    ``ValueError`` subclass) with a user-safe message on a malformed upload, for
    the page to surface via ``st.error``.
    """
    return load_table(source, SPC_SCHEMA)
