"""Tests for the MSA → SPC gate project-file arrow (M3-5, #280).

Holds ``spc_app.msa_gate_arrow.build_msa_gate_file`` to 100% line+branch. Inputs are the
committed project fixture's ``spc/config.json`` and ``msa/gage-rr.json``
(``packages/quality-core/tests/fixtures/project``), copied into ``tmp_path`` per test so
writes never touch the committed fixture.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from quality_core.project import (
    ProjectError,
    SPCMSAGateArtifact,
    discover_project,
    load_artifact,
)

import spc_app
from spc_app.msa_gate_arrow import build_msa_gate_file

_FIXTURE_PROJECT = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "quality-core"
    / "tests"
    / "fixtures"
    / "project"
)
_CHARACTERISTIC = "Example Characteristic"


def _make_project(tmp_path: Path, *, with_gage: bool = True) -> Path:
    """Copy the fixture's ``spc/config.json`` (and optionally the gage study) into tmp."""
    (tmp_path / "spc").mkdir()
    shutil.copy(_FIXTURE_PROJECT / "spc" / "config.json", tmp_path / "spc" / "config.json")
    if with_gage:
        (tmp_path / "msa").mkdir()
        shutil.copy(_FIXTURE_PROJECT / "msa" / "gage-rr.json", tmp_path / "msa" / "gage-rr.json")
    return tmp_path


def _patch_gage(project_root: Path, **overrides: object) -> None:
    path = project_root / "msa" / "gage-rr.json"
    payload = json.loads(path.read_text())
    payload.update(overrides)
    path.write_text(json.dumps(payload))


def _patch_config_rows(project_root: Path, rows: list[dict]) -> None:
    path = project_root / "spc" / "config.json"
    payload = json.loads(path.read_text())
    payload["rows"] = rows
    path.write_text(json.dumps(payload))


def test_happy_path_project_wide_study_gates_every_row(tmp_path: Path) -> None:
    """`characteristic: null` gates every configured characteristic identically."""
    root = _make_project(tmp_path)
    artifact = build_msa_gate_file(root)

    assert [row.characteristic for row in artifact.rows] == [_CHARACTERISTIC]
    row = artifact.rows[0]
    assert (row.verdict, row.gate_status) == ("Accept", "pass")


def test_named_characteristic_gates_only_that_row(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    _patch_config_rows(
        root,
        [{"characteristic": _CHARACTERISTIC}, {"characteristic": "Other"}],
    )
    _patch_gage(root, characteristic=_CHARACTERISTIC, verdict="Reject")

    gates = {row.characteristic: (row.verdict, row.gate_status) for row in build_msa_gate_file(root).rows}
    assert gates == {_CHARACTERISTIC: ("Reject", "block"), "Other": (None, "warn")}


def test_study_naming_an_unconfigured_characteristic_is_simply_unused(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    _patch_gage(root, characteristic="Not monitored")

    rows = build_msa_gate_file(root).rows
    assert [(row.characteristic, row.verdict, row.gate_status) for row in rows] == [
        (_CHARACTERISTIC, None, "warn")
    ]


def test_missing_gage_file_warns_every_row(tmp_path: Path) -> None:
    root = _make_project(tmp_path, with_gage=False)
    row = build_msa_gate_file(root).rows[0]
    assert (row.verdict, row.gate_status) == (None, "warn")
    assert "No Gage R&R study on file" in row.reason


def test_missing_config_raises(tmp_path: Path) -> None:
    with pytest.raises(ProjectError):
        build_msa_gate_file(tmp_path)


def test_malformed_gage_file_raises(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    (root / "msa" / "gage-rr.json").write_text("{ not json")
    with pytest.raises(ProjectError):
        build_msa_gate_file(root)


def test_unrecognised_verdict_raises_project_error(tmp_path: Path) -> None:
    """Negative control for the fixture typo class: a bad verdict fails loud."""
    root = _make_project(tmp_path)
    _patch_gage(root, verdict="Acceptable")
    with pytest.raises(ProjectError, match="Unrecognised Gage R&R verdict"):
        build_msa_gate_file(root)


def test_zero_row_config_writes_empty_artifact(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    _patch_config_rows(root, [])
    artifact = build_msa_gate_file(root)
    assert artifact.rows == []
    assert discover_project(root).msa_gate_json.exists()


def test_writes_file_with_provenance_and_is_idempotent(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    build_msa_gate_file(root)
    written = load_artifact(discover_project(root).msa_gate_json, SPCMSAGateArtifact)
    assert written.generated_by == f"spc_app=={spc_app.__version__}"
    assert written.generated_at.endswith("Z")

    again = build_msa_gate_file(root)
    assert len(again.rows) == len(written.rows) == 1
