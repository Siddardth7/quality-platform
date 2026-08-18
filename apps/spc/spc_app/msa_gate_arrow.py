"""
msa_gate_arrow.py
MSA → SPC gate project-file arrow (M3-5, issue #280).

The project-file (#276) face of :mod:`spc_app.msa_gate`: read ``spc/config.json``
(``SPCConfigArtifact``, written by M3-3) and ``msa/gage-rr.json``
(``MSAGageRRArtifact``), and write ``spc/msa-gate.json`` (``SPCMSAGateArtifact``) —
one row per *monitored* characteristic saying how far its SPC result may be trusted.
No gate policy lives here; the verdict → status mapping is ``msa_gate.gate_for``'s.

Required vs optional inputs. ``spc/config.json`` is **required** — with no monitored
characteristics there is nothing to gate, and a missing file is a mis-ordered pipeline,
not an empty answer, so its ``ProjectError`` propagates as-is (same discipline as
``fmea_feedback_arrow``'s required inputs). ``msa/gage-rr.json`` is **optional**: a
project that has not run a Gage R&R study yet is a normal state, and every row simply
gates as "no study on file" (``warn``). A gage file that exists but is malformed still
raises.

Join key: **exact string match on ``characteristic``**, no normalisation, no fuzzy match
— same discipline as ``project_arrow``. ``MSAGageRRArtifact.characteristic`` is ``None``
in every study written today, which means "the project's one measurement-system record"
and gates every configured characteristic identically. A named value gates only that
characteristic; a name matching no ``spc/config.json`` row leaves the study simply unused,
since the gate has one row per SPC-config characteristic, not per gage study.

Direction: ``spc_app`` imports ``quality_core.project`` (downward) and never ``msa_app``
— the verdict arrives as a string on ``MSAGageRRArtifact``, so no cross-app type is
needed (audit A11, #202).

Idempotency: a re-run overwrites ``spc/msa-gate.json`` in place — no merge, no history
array (``write_artifact``, #276). Unlike ``feedback/spc-to-fmea.json``, the file is
*always* written, even with zero rows: "nothing is configured to monitor" is a stable
state worth recording, not a transient "nothing to report" one.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from quality_core.project import (
    SCHEMA_VERSION,
    MSAGageRRArtifact,
    ProjectError,
    SPCConfigArtifact,
    SPCMSAGateArtifact,
    SPCMSAGateRow,
    discover_project,
    load_artifact,
    load_optional_artifact,
    write_artifact,
)

import spc_app
from spc_app.msa_gate import gate_for

__all__ = ["build_msa_gate_file"]


def build_msa_gate_file(project_root: str | os.PathLike[str]) -> SPCMSAGateArtifact:
    """Read ``spc/config.json`` + ``msa/gage-rr.json``, write ``spc/msa-gate.json``.

    Returns the artifact that was written (always written, even with zero rows).

    Raises ``quality_core.project.ProjectError`` if ``spc/config.json`` is missing or
    malformed, if ``msa/gage-rr.json`` exists but is malformed, or if a gage study
    carries a ``verdict`` string outside AIAG's ``Accept``/``Marginal``/``Reject`` —
    a gate silently defaulting on an unreadable verdict is worse than a loud failure.
    """
    paths = discover_project(project_root)
    config = load_artifact(paths.spc_config_json, SPCConfigArtifact)
    gage = load_optional_artifact(paths.gage_rr_json, MSAGageRRArtifact)

    rows: list[SPCMSAGateRow] = []
    for config_row in config.rows:
        verdict: str | None = None
        if gage is not None and gage.characteristic in (None, config_row.characteristic):
            verdict = gage.verdict
        try:
            gate_status, reason = gate_for(verdict)
        except ValueError as exc:
            raise ProjectError(f"'{paths.gage_rr_json}' is not usable: {exc}") from exc
        rows.append(
            SPCMSAGateRow(
                characteristic=config_row.characteristic,
                verdict=verdict,
                gate_status=gate_status,
                reason=reason,
            )
        )

    artifact = SPCMSAGateArtifact(
        schema_version=SCHEMA_VERSION,
        # ponytail: second precision, matching every committed fixture artifact.
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        generated_by=f"spc_app=={spc_app.__version__}",
        rows=rows,
    )
    write_artifact(paths.msa_gate_json, artifact)
    return artifact
