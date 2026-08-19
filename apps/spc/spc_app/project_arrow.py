"""
project_arrow.py
Control Plan → SPC project-file arrow (M3-3, issue #278).

The project-file (#276) face of :mod:`spc_app.control_plan_config`: read
``control-plan/plan.json`` (``quality_core.project.ControlPlanArtifact``), derive one
SPC monitoring config per plan characteristic, and write ``spc/config.json``
(``quality_core.project.SPCConfigArtifact``). No SPC selection logic lives here — the
chart-key normalisation and the spec/sample-plan pass-through are
``control_plan_config``'s (which is itself a pass-through over the connector's AIAG rule
table); this module only moves them between the on-disk contract and the in-memory one.

Direction: ``spc_app`` imports ``quality_core.project`` (downward) and never
``controlplan_app`` — ``ControlPlanArtifactRow``'s field names already match the columns
``control_plan_config`` reads, so the plan rows convert straight to a ``DataFrame`` with
no cross-app type in between (audit A11, #202).

Join key: **exact string match on ``characteristic``**. ``config_for`` filters with
``plan_df["characteristic"] == characteristic`` — no normalisation, no fuzzy match — and
the same string is carried onto ``SPCConfigRow.characteristic``, so a plan row and its
SPC config row share one identifier. Changing that to a fuzzy join is a deliberate
decision, not a drift.

Unknown chart keys: ``recommended_chart`` is a Literal-typed field, so a value that
survived loading is either ``None`` or one of the six ``SPCChart`` keys. ``None`` (what
``build_control_plan`` emits today) is carried through as ``chart_key=None`` — no
exception, no fabricated chart type. ``control_plan_config.chart_type_index`` (the
selectbox preselect that turns that ``None`` into index ``0``) is a UI concern and is
deliberately not called here.

Idempotency: a re-run overwrites ``spc/config.json`` in place — no merge, no history
array. That is ``quality_core.project.io.write_artifact``'s behaviour and M3-1's "git is
the history" resolution (#276), inherited rather than re-implemented.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import cast, get_args

import pandas as pd
from quality_core.project import (
    SCHEMA_VERSION,
    ControlPlanArtifact,
    SPCConfigArtifact,
    SPCConfigRow,
    discover_project,
    load_artifact,
    write_artifact,
)
from quality_core.spc.constants import SPCChart

import spc_app
from spc_app.control_plan_config import config_for, plan_characteristics

__all__ = ["CHART_OPTIONS", "build_spc_config_file"]

#: The chart vocabulary this arrow considers valid, straight from the one source
#: `control_plan_config._VALID_CHART_KEYS` uses.
# ponytail: deliberately NOT the Streamlit page's CHART_OPTIONS dict, which also offers
# EWMA and CUSUM. Those are monitoring-scheme choices a human picks interactively; an
# unattended arrow writing a project file has no one to pick them, and importing a UI
# module here would drag Streamlit into the arrow. Six Shewhart keys is the contract.
CHART_OPTIONS: list[str] = list(get_args(SPCChart))


def build_spc_config_file(project_root: str | os.PathLike[str]) -> SPCConfigArtifact:
    """Read ``control-plan/plan.json``, derive an SPC config, write ``spc/config.json``.

    Raises ``quality_core.project.ProjectError`` if ``control-plan/plan.json`` is missing
    or malformed — propagated as-is, so the caller sees the file and the problem named.
    Overwrites ``spc/config.json`` in place if it already exists (idempotent), creating
    ``spc/`` if it does not. Returns the artifact that was written.
    """
    paths = discover_project(project_root)
    plan = load_artifact(paths.control_plan_json, ControlPlanArtifact)
    rows: list[SPCConfigRow] = []
    # An empty plan short-circuits: pd.DataFrame([]) has no columns at all, so the
    # DataFrame round trip would only be a slower way to reach the same empty list.
    if plan.rows:
        plan_df = pd.DataFrame([row.model_dump() for row in plan.rows])
        for characteristic in plan_characteristics(plan_df):
            config = config_for(plan_df, characteristic)
            rows.append(
                # SPCConfigRow mirrors SPCViewConfig field-for-field. SPCViewConfig types
                # chart_key `str | None` where the artifact narrows it to the SPCChart
                # Literal, so the cast is the honest place that gap lives — pydantic still
                # validates it, and a key outside SPCChart fails loud here rather than
                # being written to the project file.
                SPCConfigRow(
                    characteristic=config.characteristic,
                    chart_key=cast("SPCChart | None", config.chart_key),
                    lsl=config.lsl,
                    usl=config.usl,
                    target=config.target,
                    sample_size=config.sample_size,
                    frequency=config.frequency,
                )
            )
    artifact = SPCConfigArtifact(
        schema_version=SCHEMA_VERSION,
        # ponytail: second precision, matching every committed fixture artifact.
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        generated_by=f"spc_app=={spc_app.__version__}",
        rows=rows,
    )
    write_artifact(paths.spc_config_json, artifact)
    return artifact
