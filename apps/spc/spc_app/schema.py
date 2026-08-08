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
valid continuous-measurement uploads (Xbar/I-MR/capability).

``sample_size`` / ``lsl`` / ``usl`` / ``chart_type`` are declared as
``optional_columns`` (#200): not required to be present, but validated by
``SPCRow`` and returned when the upload carries them. They used to pass through
unvalidated straight into the chart/capability math, with only a Streamlit
``try/except`` behind them. ``parameter`` is a demo-dataset label no code reads,
so it is left undeclared and is dropped by the ingest boundary.
"""

from __future__ import annotations

from typing import Annotated, BinaryIO, Literal

import pandas as pd
import pydantic
from quality_core.io import IngestError, TableSchema, load_table, load_table_from_path

__all__ = ["SPCChartKey", "SPCRow", "SPC_SCHEMA", "load_spc_csv", "IngestError"]

#: Chart keys an uploaded ``chart_type`` cell may carry — the internal SPC engine
#: keys emitted by ``spc_engine.data_generator``. Deliberately NOT Control Plan's
#: ``SPCChart`` display labels (``"Xbar-R"``, ``"I-MR"``, ...): that is a
#: human-readable control-method vocabulary for a Control Plan document, this is
#: the engine's dispatch key. The two are kept separate on purpose — do not import
#: one into the other.
SPCChartKey = Literal["xbar_r", "xbar_s", "imr", "p", "u", "c"]


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
    #: Attribute-chart sample size. ``float``/``gt=0``, not ``int``/``ge=1``: for a
    #: u chart ``n`` is the *area of opportunity* (inspection units per sample),
    #: legitimately non-integer and possibly < 1 (AIAG SPC 4th ed.) — only the p
    #: chart's ``n`` is a count, and one column serves both. ``compute_u`` already
    #: takes ``list[float]``, and the bundled demo dataset's u stream carries
    #: 0.8–1.6. Blank (continuous-measurement upload) → ``None``.
    sample_size: Annotated[float | None, pydantic.Field(default=None, gt=0, allow_inf_nan=False)] = (
        None
    )
    # Tolerances: nullable (not every stream is spec'd) and finite, so an 'inf'
    # cell cannot become an infinite capability index.
    lsl: Annotated[float | None, pydantic.Field(default=None, allow_inf_nan=False)] = None
    usl: Annotated[float | None, pydantic.Field(default=None, allow_inf_nan=False)] = None
    # No usl > lsl cross-check on purpose: the capability page treats the two as
    # independent pre-fill defaults, not a paired tolerance band (unlike
    # ControlPlanRow, where the pair *is* the characteristic's specification).
    chart_type: SPCChartKey | None = None

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
    optional_columns=("sample_size", "lsl", "usl", "chart_type"),
    template_hint="data/demo_composites_aerospace.csv",
)


def load_spc_csv(source: str | BinaryIO) -> pd.DataFrame:
    """Read + validate an uploaded SPC ``.csv`` against :data:`SPC_SCHEMA`.

    Returns a DataFrame narrowed to the validated columns — ``stream``,
    ``subgroup``, ``value`` plus whichever of ``sample_size``/``lsl``/``usl``/
    ``chart_type`` the upload carried. Anything else (``parameter``, an exporter's
    ``operator``/``notes``) is dropped. Raises :class:`IngestError` (a
    ``ValueError`` subclass) with a user-safe message on a malformed upload, for
    the page to surface via ``st.error``.
    """
    if isinstance(source, str):
        return load_table_from_path(source, SPC_SCHEMA)
    return load_table(source, SPC_SCHEMA)
