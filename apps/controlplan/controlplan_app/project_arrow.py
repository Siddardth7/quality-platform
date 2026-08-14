"""
project_arrow.py
FMEA → Control Plan project-file arrow (M3-2, issue #277).

The project-file (#276) face of the existing connector: read ``fmea/fmea.json``
(``quality_core.project.FMEAArtifact``), run :func:`controlplan_app.connector.build_control_plan`
on the ``RelationalFMEA`` it carries, and write the derived rows to
``control-plan/plan.json`` (``quality_core.project.ControlPlanArtifact``). No Control
Plan logic lives here — the mapping rules, defaults and the ``source_cause_id`` join key
are the connector's (see ``connector.py`` and ``docs/ASSUMPTIONS_LOG.md``); this module
only moves them between the on-disk contract and the in-memory one.

Direction: ``controlplan_app`` imports ``quality_core.project`` (downward), never the
reverse — ``quality_core`` holds ``ControlPlanArtifactRow`` as an independent mirror of
``controlplan_app.schema.ControlPlanRow`` precisely so it never has to import an app
(see ``quality_core/project/schema.py``'s module docstring).

Idempotency: a re-run overwrites ``control-plan/plan.json`` in place — no merge, no run
id, no history array. That is ``quality_core.project.io.write_artifact``'s behaviour and
M3-1's "git is the history" resolution (#276), inherited rather than re-implemented.

Traceability: every row this arrow writes carries the connector's ``source_cause_id``,
which equals ``connector.source_index(fmea)[row.characteristic]["cause_id"]`` (both come
from the connector's shared ``_iter_named_modes`` traversal). SPC (M3-3) joins on that
field straight out of ``plan.json``.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from quality_core.project import (
    SCHEMA_VERSION,
    ControlPlanArtifact,
    ControlPlanArtifactRow,
    FMEAArtifact,
    discover_project,
    load_artifact,
    write_artifact,
)

import controlplan_app
from controlplan_app.connector import build_control_plan

__all__ = ["build_control_plan_file"]


def build_control_plan_file(project_root: str | os.PathLike[str]) -> ControlPlanArtifact:
    """Read ``fmea/fmea.json``, derive a Control Plan, write ``control-plan/plan.json``.

    Raises ``quality_core.project.ProjectError`` if ``fmea/fmea.json`` is missing or
    malformed — propagated as-is, so the caller sees the file and the problem named.
    Overwrites ``control-plan/plan.json`` in place if it already exists (idempotent),
    creating ``control-plan/`` if it does not. Returns the artifact that was written.
    """
    paths = discover_project(project_root)
    fmea = load_artifact(paths.fmea_json, FMEAArtifact).fmea
    dataset = build_control_plan(fmea)
    artifact = ControlPlanArtifact(
        schema_version=SCHEMA_VERSION,
        # ponytail: second precision, matching every committed fixture artifact.
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        generated_by=f"controlplan_app=={controlplan_app.__version__}",
        # ControlPlanArtifactRow mirrors ControlPlanRow field-for-field, so this is a
        # straight copy. It is a StrictModel: a connector field added without a matching
        # mirror field fails loud here rather than being silently dropped.
        rows=[ControlPlanArtifactRow(**row.model_dump()) for row in dataset.rows],
    )
    write_artifact(paths.control_plan_json, artifact)
    return artifact
