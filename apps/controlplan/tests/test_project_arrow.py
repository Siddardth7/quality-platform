"""Tests for the FMEA → Control Plan project-file arrow (M3-2, #277).

Holds ``controlplan_app.project_arrow.build_control_plan_file`` to 100% line+branch.

Input is the committed project fixture's ``fmea/fmea.json``
(``packages/quality-core/tests/fixtures/project``). It is copied into ``tmp_path`` per
test so writes never touch the committed fixture, and — per spec — no test asserts
equality against the fixture's own hand-authored ``control-plan/plan.json`` (that row was
not produced by running the connector, so it does not match this arrow's output).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from controlplan_app.connector import build_control_plan, source_index
from controlplan_app.project_arrow import build_control_plan_file
from quality_core.project import (
    ControlPlanArtifact,
    FMEAArtifact,
    ProjectError,
    discover_project,
    load_artifact,
)

_FIXTURE_PROJECT = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "quality-core"
    / "tests"
    / "fixtures"
    / "project"
)


def _make_project(tmp_path: Path) -> Path:
    """Copy just the fixture's ``fmea/`` subtree into ``tmp_path`` and return the root."""
    shutil.copytree(_FIXTURE_PROJECT / "fmea", tmp_path / "fmea")
    return tmp_path


def _read_fmea_json(project_root: Path) -> dict:
    return json.loads((project_root / "fmea" / "fmea.json").read_text())


def _write_fmea_json(project_root: Path, payload: dict) -> None:
    (project_root / "fmea" / "fmea.json").write_text(json.dumps(payload))


# A second Function/FailureMode, valid RelationalFMEA shape, distinct ids and component
# so the connector produces a genuinely new characteristic (no collision suffix).
_SECOND_FUNCTION = {
    "id": "F2",
    "process_step": "Deburr",
    "component": "Housing",
    "description": "Remove sharp edges",
    "failure_modes": [
        {
            "id": "F2-M1",
            "description": "Burr remains",
            "effects": [{"id": "F2-M1-E1", "description": "Cut hazard", "severity": 8}],
            "causes": [{"id": "F2-M1-C1", "description": "Dull tool", "occurrence": 6}],
            "controls": [
                {"id": "F2-M1-CT1", "description": "Visual check", "detection": 4}
            ],
            "links": [
                {
                    "row_id": 2,
                    "effect_id": "F2-M1-E1",
                    "cause_id": "F2-M1-C1",
                    "control_id": "F2-M1-CT1",
                    "action": None,
                }
            ],
        }
    ],
}


def test_happy_path_writes_and_reloads(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)
    paths = discover_project(project_root)

    returned = build_control_plan_file(project_root)

    assert paths.control_plan_json.exists()
    # Loads back through the strict project reader without error.
    reloaded = load_artifact(paths.control_plan_json, ControlPlanArtifact)
    assert isinstance(reloaded, ControlPlanArtifact)
    # The returned artifact is what was written.
    assert reloaded.rows == returned.rows


def test_rows_match_connector_one_to_one(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)
    fmea = load_artifact(discover_project(project_root).fmea_json, FMEAArtifact).fmea
    expected = build_control_plan(fmea).rows

    build_control_plan_file(project_root)
    written = load_artifact(
        discover_project(project_root).control_plan_json, ControlPlanArtifact
    ).rows

    # Same count, same characteristic strings in the same (highest-risk-first) order.
    assert len(written) == len(expected)
    assert [r.characteristic for r in written] == [r.characteristic for r in expected]
    # Full field-for-field parity of the connector output.
    assert [r.model_dump() for r in written] == [r.model_dump() for r in expected]


def test_traceability_source_cause_id_against_written_file(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)
    fmea = load_artifact(discover_project(project_root).fmea_json, FMEAArtifact).fmea
    index = source_index(fmea)

    build_control_plan_file(project_root)
    written = load_artifact(
        discover_project(project_root).control_plan_json, ControlPlanArtifact
    ).rows

    assert written  # the fixture has at least one row
    for row in written:
        assert row.source_cause_id is not None
        assert row.source_cause_id == index[row.characteristic]["cause_id"]


def test_idempotency_two_runs_identical_rows(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)

    first = build_control_plan_file(project_root)
    second = build_control_plan_file(project_root)

    # generated_at is a live clock, so compare the deterministic rows payload, not bytes.
    assert second.rows == first.rows
    # Exactly one plan file at the fixed path — no plan-2.json / versioning.
    plan_dir = project_root / "control-plan"
    assert [p.name for p in plan_dir.iterdir()] == ["plan.json"]


def test_rerun_after_fmea_edit_replaces_wholesale(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)

    first = build_control_plan_file(project_root)
    assert len(first.rows) == 1

    # Add a second Function/FailureMode and re-run.
    payload = _read_fmea_json(project_root)
    payload["fmea"]["functions"].append(_SECOND_FUNCTION)
    _write_fmea_json(project_root, payload)

    second = build_control_plan_file(project_root)
    written = load_artifact(
        discover_project(project_root).control_plan_json, ControlPlanArtifact
    ).rows

    # Row set reflects the new FMEA: two rows now, both unique — no incorrect duplication.
    assert len(written) == 2
    characteristics = [r.characteristic for r in written]
    assert len(set(characteristics)) == 2
    assert "Housing — Burr remains" in characteristics
    assert "Bracket — Bore oversize" in characteristics
    assert len(second.rows) == 2
    # Still exactly one file — overwrite in place.
    assert [p.name for p in (project_root / "control-plan").iterdir()] == ["plan.json"]


def test_missing_fmea_raises_and_writes_nothing(tmp_path: Path) -> None:
    # No fmea/ subtree at all.
    paths = discover_project(tmp_path)
    with pytest.raises(ProjectError):
        build_control_plan_file(tmp_path)
    assert not paths.control_plan_json.exists()


def test_malformed_fmea_propagates_project_error(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)
    payload = _read_fmea_json(project_root)
    payload["schema_version"] = 999  # unsupported schema version
    _write_fmea_json(project_root, payload)

    with pytest.raises(ProjectError):
        build_control_plan_file(project_root)


def test_empty_fmea_writes_empty_rows(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)
    payload = _read_fmea_json(project_root)
    payload["fmea"]["functions"] = []
    _write_fmea_json(project_root, payload)

    artifact = build_control_plan_file(project_root)
    assert artifact.rows == []

    reloaded = load_artifact(
        discover_project(project_root).control_plan_json, ControlPlanArtifact
    )
    assert reloaded.rows == []


def test_control_plan_dir_created_when_absent(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)
    plan_dir = project_root / "control-plan"
    assert not plan_dir.exists()

    build_control_plan_file(project_root)

    assert plan_dir.is_dir()
    assert (plan_dir / "plan.json").exists()
