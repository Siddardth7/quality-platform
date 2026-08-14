"""
fmea_feedback_arrow.py
SPC → FMEA project-file arrow (M3-4, issue #279) — the "living FMEA" leg.

The project-file (#276) face of :mod:`spc_app.fmea_feedback`: read every
``spc/results/<characteristic>.json`` plus ``control-plan/plan.json`` (for the join back
to an FMEA cause) and ``fmea/fmea.json``, derive one candidate occurrence-feedback row per
out-of-control characteristic, and write ``feedback/spc-to-fmea.json`` **and** the matching
``Action`` candidates onto ``fmea/fmea.json``. No occurrence math lives here — the rate →
rank mapping is ``fmea_feedback._rate_to_occurrence``'s (AIAG-4 / SAE J1739, ASSUMPTIONS_LOG
RULE 10); this module only moves values between the on-disk contract and that pure engine.

**Candidate, never an applied rating.** ``fmea_feedback``'s discipline ("it NEVER writes a
new rating, it only proposes one for a human to review") survives here: ``Cause.occurrence``
is never touched. The proposal lands as
:class:`quality_core.schema.action.Action` with ``o_after=suggested_occurrence`` and
``status=Open`` on the affected :class:`~quality_core.schema.relational.FailureLink` — the
schema's own before/after mechanism for the AIAG optimization loop. A human reads
``feedback/spc-to-fmea.json`` (which holds the full provenance: chart, rule set, violating
points, CAPA prompt) and decides.

**Loop stability is structural, not guarded.** Because the loop's input
(``Cause.occurrence``, read as ``current_occurrence``) is never written by its output (the
``Action``), a re-run on the same SPC violations recomputes the same ``ooc_rate`` → the same
``suggested_occurrence`` → the same ``Action``. Oscillation cannot occur; there is
deliberately no anti-oscillation mechanism to maintain.

Direction: ``spc_app`` imports ``quality_core`` (downward) and never ``controlplan_app``
(audit A11, #202). The one piece of Control-Plan knowledge this arrow needs — the
``"<function>::<failure_mode>::<cause>"`` shape of ``ControlPlanArtifactRow.source_cause_id``,
written by ``controlplan_app.connector._source_cause_id`` — is re-derived in
:func:`_resolve_source_cause`, the same "duplicate the string contract, not the app"
discipline as ``control_plan_config.PLAN_STATE_KEY`` and
``fmea_feedback.SOURCE_INDEX_STATE_KEY``.

Idempotency: ``feedback/spc-to-fmea.json`` is overwritten in place (no merge, no history
array — git is the history, #276) and deleted outright when nothing is out of control, since
files hold current state only. ``fmea/fmea.json`` is rewritten only when an ``Action`` was
actually set or cleared, so a no-op run leaves it byte-identical.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Mapping

from quality_core.project import (
    SCHEMA_VERSION,
    ControlPlanArtifact,
    FMEAArtifact,
    SPCResultArtifact,
    SPCToFMEAFeedbackArtifact,
    SPCToFMEAFeedbackRow,
    discover_project,
    load_artifact,
    spc_result_paths,
    write_artifact,
)
from quality_core.schema.action import Action, ActionStatus
from quality_core.schema.relational import Cause, FailureMode, Function, RelationalFMEA

import spc_app
from spc_app.fmea_feedback import build_occurrence_feedback

__all__ = ["build_feedback_file"]

#: Owner stamped on every ``Action`` this arrow writes — and the guard that keeps it from
#: clobbering a human-authored one. It is also the pointer from ``fmea/fmea.json`` back to
#: the file holding the provenance (which chart, which rule, which period).
_FEEDBACK_ACTION_OWNER = "SPC feedback arrow (feedback/spc-to-fmea.json)"


def _resolve_source_cause(
    fmea: RelationalFMEA, source_cause_id: str
) -> tuple[Function, FailureMode, Cause] | None:
    """Resolve a ``"<function>::<failure_mode>::<cause>"`` id against a loaded FMEA.

    Mirrors ``controlplan_app.connector._source_cause_id``'s format (duplicated, not
    imported — ``spc_app`` never imports ``controlplan_app``). Returns ``None`` for a
    malformed id or one naming a function / failure mode / cause the FMEA does not hold —
    never raises; the caller treats an unresolved source exactly like ``source=None``.
    """
    parts = source_cause_id.split("::")
    if len(parts) != 3:
        return None
    function_id, failure_mode_id, cause_id = parts
    function = next((fn for fn in fmea.functions if fn.id == function_id), None)
    if function is None:
        return None
    failure_mode = next((fm for fm in function.failure_modes if fm.id == failure_mode_id), None)
    if failure_mode is None:
        return None
    cause = next((c for c in failure_mode.causes if c.id == cause_id), None)
    if cause is None:
        return None
    return (function, failure_mode, cause)


def _apply_or_clear_actions(fmea: RelationalFMEA, candidates: Mapping[str, int]) -> bool:
    """Set our candidate ``Action`` on every link of a currently-OOC cause, clear it
    everywhere else, and report whether anything actually changed.

    ``candidates`` maps ``source_cause_id`` → ``suggested_occurrence``. Every cause in the
    FMEA is visited, not just the OOC ones: a cause that has stabilised must lose the
    ``Action`` a previous run left behind (files hold current state only). Occurrence is a
    cause-level attribute, so all of a cause's links get the same candidate. A link whose
    ``Action`` someone else owns is left strictly alone.
    """
    changed = False
    for function in fmea.functions:
        for failure_mode in function.failure_modes:
            for cause in failure_mode.causes:
                suggested = candidates.get(f"{function.id}::{failure_mode.id}::{cause.id}")
                wanted = (
                    None
                    if suggested is None
                    else Action(
                        owner=_FEEDBACK_ACTION_OWNER,
                        status=ActionStatus.OPEN,
                        due=None,
                        s_after=None,
                        o_after=suggested,
                        d_after=None,
                    )
                )
                for link in sorted(failure_mode.links, key=lambda lk: lk.row_id):
                    if link.cause_id != cause.id:
                        continue
                    if link.action is not None and link.action.owner != _FEEDBACK_ACTION_OWNER:
                        continue  # human-authored — never overwrite it
                    if link.action != wanted:
                        link.action = wanted
                        changed = True
    return changed


def _now() -> str:
    # ponytail: second precision, matching every committed fixture artifact.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_feedback_file(
    project_root: str | os.PathLike[str],
) -> SPCToFMEAFeedbackArtifact | None:
    """Derive SPC → FMEA occurrence feedback for a project and persist both sides of it.

    Reads ``spc/results/*.json``, ``control-plan/plan.json`` and ``fmea/fmea.json``; writes
    ``feedback/spc-to-fmea.json`` (one row per out-of-control characteristic) and attaches
    an ``Action(o_after=suggested_occurrence, status=Open)`` candidate to the affected
    ``FailureLink``s in ``fmea/fmea.json``. ``Cause.occurrence`` is never modified.

    Returns the written feedback artifact, or ``None`` when no characteristic is currently
    out of control — in which case a stale ``feedback/spc-to-fmea.json`` is deleted and any
    ``Action`` this arrow previously wrote is cleared. ``fmea/fmea.json`` is rewritten (with
    a fresh envelope, since this arrow is then its most recent writer) only if an ``Action``
    was actually set or cleared.

    Raises ``quality_core.project.ProjectError`` if ``fmea/fmea.json`` or
    ``control-plan/plan.json`` is missing or malformed — both are required inputs: without
    the plan there is no join key from a monitored characteristic back to an FMEA cause, so
    feedback with no auditable source would be written instead of a loud failure.
    """
    paths = discover_project(project_root)
    fmea_artifact = load_artifact(paths.fmea_json, FMEAArtifact)
    plan = load_artifact(paths.control_plan_json, ControlPlanArtifact)
    plan_sources = {row.characteristic: row.source_cause_id for row in plan.rows}

    rows: list[SPCToFMEAFeedbackRow] = []
    candidates: dict[str, int] = {}
    # spc_result_paths is sorted, so row order is deterministic across runs.
    for path in spc_result_paths(paths):
        result = load_artifact(path, SPCResultArtifact)
        chart = result.control_chart
        if chart is None:
            continue  # a capability result carries no violations to feed back
        source_cause_id = plan_sources.get(result.characteristic)
        resolved = (
            None
            if source_cause_id is None
            else _resolve_source_cause(fmea_artifact.fmea, source_cause_id)
        )
        source: dict[str, object] | None = None
        resolved_key: str | None = None
        if resolved is not None:
            function, failure_mode, cause = resolved
            resolved_key = f"{function.id}::{failure_mode.id}::{cause.id}"
            # Same keys controlplan_app.connector.source_index emits (duplicated contract,
            # no import) — build_occurrence_feedback reads exactly these.
            source = {
                "failure_mode_id": failure_mode.id,
                "cause_id": source_cause_id,
                "cause_description": cause.description,
                "occurrence": cause.occurrence,
                "component": function.component,
            }
        payload = build_occurrence_feedback(
            characteristic=result.characteristic,
            stream=chart.stream,
            rule_set=chart.rule_set,
            violations=[{"index": v.index, "rule": v.rule} for v in chart.violations],
            total_points=len(chart.points),
            source=source,
        )
        if payload is None:
            continue  # in control — nothing to feed back for this characteristic
        row = SPCToFMEAFeedbackRow.model_validate(payload)
        rows.append(row)
        if resolved_key is not None:
            candidates[resolved_key] = row.suggested_occurrence

    if _apply_or_clear_actions(fmea_artifact.fmea, candidates):
        write_artifact(
            paths.fmea_json,
            FMEAArtifact(
                schema_version=SCHEMA_VERSION,
                generated_at=_now(),
                generated_by=f"spc_app=={spc_app.__version__}",
                fmea=fmea_artifact.fmea,
            ),
        )

    if not rows:
        paths.feedback_json.unlink(missing_ok=True)
        return None

    artifact = SPCToFMEAFeedbackArtifact(
        schema_version=SCHEMA_VERSION,
        generated_at=_now(),
        generated_by=f"spc_app=={spc_app.__version__}",
        rows=rows,
    )
    write_artifact(paths.feedback_json, artifact)
    return artifact
