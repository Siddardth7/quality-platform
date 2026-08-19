"""Tests for the Control Plan → SPC project-file arrow (M3-3, #278).

Holds ``spc_app.project_arrow.build_spc_config_file`` to 100% line+branch.

Input is the committed project fixture's ``control-plan/plan.json``
(``packages/quality-core/tests/fixtures/project``). It is copied into ``tmp_path`` per
test so writes never touch the committed fixture. Per spec, no test asserts equality
against the fixture's own hand-authored ``spc/config.json`` beyond the fields the arrow
actually derives — the oracle is ``control_plan_config``'s own output, computed directly.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from quality_core.project import (
    ControlPlanArtifact,
    ProjectError,
    SPCConfigArtifact,
    discover_project,
    load_artifact,
)

from spc_app.control_plan_config import config_for, plan_characteristics
from spc_app.project_arrow import build_spc_config_file

_FIXTURE_PROJECT = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "quality-core"
    / "tests"
    / "fixtures"
    / "project"
)


def _make_project(tmp_path: Path) -> Path:
    """Copy just the fixture's ``control-plan/`` subtree into ``tmp_path``."""
    shutil.copytree(_FIXTURE_PROJECT / "control-plan", tmp_path / "control-plan")
    return tmp_path


def _read_plan(project_root: Path) -> dict:
    return json.loads((project_root / "control-plan" / "plan.json").read_text())


def _write_plan(project_root: Path, payload: dict) -> None:
    (project_root / "control-plan").mkdir(exist_ok=True)
    (project_root / "control-plan" / "plan.json").write_text(json.dumps(payload))


def _plan_row(**overrides: object) -> dict:
    """A valid ControlPlanArtifactRow payload; override any field per test."""
    base: dict = {
        "characteristic": "Bore diameter",
        "lsl": 9.5,
        "usl": 10.5,
        "target": 10.0,
        "measurement_method": "Bore gauge",
        "sample_size": 5,
        "frequency": "per shift",
        "recommended_chart": "Xbar-R",
        "reaction_plan": "Quarantine the lot.",
        "source_cause_id": "F1-M1-C1",
        "sample_plan_is_placeholder": True,
    }
    base.update(overrides)
    return base


def _plan_payload(rows: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "generated_at": "2026-08-13T12:00:00Z",
        "generated_by": "controlplan_app==0.14.0",
        "rows": rows,
    }


def test_happy_path_writes_and_reloads(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)
    paths = discover_project(project_root)

    returned = build_spc_config_file(project_root)

    assert paths.spc_config_json.exists()
    reloaded = load_artifact(paths.spc_config_json, SPCConfigArtifact)
    assert isinstance(reloaded, SPCConfigArtifact)
    assert reloaded.rows == returned.rows
    assert returned.generated_by.startswith("spc_app==")


def test_rows_match_config_for_one_to_one(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)
    plan = load_artifact(discover_project(project_root).control_plan_json, ControlPlanArtifact)
    plan_df = pd.DataFrame([row.model_dump() for row in plan.rows])
    expected = [config_for(plan_df, c) for c in plan_characteristics(plan_df)]

    build_spc_config_file(project_root)
    written = load_artifact(
        discover_project(project_root).spc_config_json, SPCConfigArtifact
    ).rows

    assert len(written) == len(expected)
    for got, exp in zip(written, expected):
        assert got.characteristic == exp.characteristic
        assert got.chart_key == exp.chart_key
        assert got.lsl == exp.lsl
        assert got.usl == exp.usl
        assert got.target == exp.target
        assert got.sample_size == exp.sample_size
        assert got.frequency == exp.frequency


def test_known_chart_key_preserved(tmp_path: Path) -> None:
    # The fixture's single row carries recommended_chart "Xbar-R" — it must survive.
    project_root = _make_project(tmp_path)

    artifact = build_spc_config_file(project_root)

    assert [r.chart_key for r in artifact.rows] == ["Xbar-R"]


def test_unknown_placeholder_chart_key_handled_gracefully(tmp_path: Path) -> None:
    # recommended_chart null (what build_control_plan emits today) → chart_key None,
    # no exception, no fabricated chart type. This is the named acceptance criterion.
    project_root = tmp_path
    _write_plan(project_root, _plan_payload([_plan_row(recommended_chart=None)]))

    artifact = build_spc_config_file(project_root)

    assert len(artifact.rows) == 1
    assert artifact.rows[0].chart_key is None
    assert artifact.rows[0].characteristic == "Bore diameter"


def test_join_key_is_exact_string_match(tmp_path: Path) -> None:
    # Two substring-related names with DISTINCT chart keys. An exact-match join maps each
    # name to its own row; a `.str.contains` join would collapse "Bore" onto the first
    # row that contains it ("Bore diameter"), swapping its chart key. This test pins the
    # exact-match rule the arrow's docstring names.
    project_root = tmp_path
    _write_plan(
        project_root,
        _plan_payload(
            [
                _plan_row(characteristic="Bore diameter", recommended_chart="Xbar-R"),
                _plan_row(characteristic="Bore", recommended_chart="I-MR"),
            ]
        ),
    )

    artifact = build_spc_config_file(project_root)
    by_name = {r.characteristic: r for r in artifact.rows}

    assert set(by_name) == {"Bore diameter", "Bore"}
    assert by_name["Bore diameter"].chart_key == "Xbar-R"
    assert by_name["Bore"].chart_key == "I-MR"
    # A name absent from the plan produces no config row.
    assert "Housing" not in by_name


def test_idempotency_two_runs_identical_rows(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)

    first = build_spc_config_file(project_root)
    second = build_spc_config_file(project_root)

    # generated_at is a live clock, so compare the deterministic rows, not bytes.
    assert second.rows == first.rows
    # Exactly one config file at the fixed path — no versioning, no append.
    spc_dir = project_root / "spc"
    assert [p.name for p in spc_dir.iterdir()] == ["config.json"]


def test_rerun_after_plan_edit_replaces_wholesale(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)

    first = build_spc_config_file(project_root)
    assert len(first.rows) == 1

    # Replace the plan with two brand-new characteristics and re-run.
    _write_plan(
        project_root,
        _plan_payload(
            [
                _plan_row(characteristic="Housing width", recommended_chart="I-MR"),
                _plan_row(characteristic="Shaft runout", recommended_chart=None),
            ]
        ),
    )

    second = build_spc_config_file(project_root)
    written = load_artifact(
        discover_project(project_root).spc_config_json, SPCConfigArtifact
    ).rows

    names = [r.characteristic for r in written]
    assert names == ["Housing width", "Shaft runout"]
    # The old "Example Characteristic" row is gone — wholesale replacement, no merge.
    assert "Example Characteristic" not in names
    assert len(second.rows) == 2
    assert [p.name for p in (project_root / "spc").iterdir()] == ["config.json"]


def test_missing_control_plan_raises_and_writes_nothing(tmp_path: Path) -> None:
    paths = discover_project(tmp_path)
    with pytest.raises(ProjectError):
        build_spc_config_file(tmp_path)
    assert not paths.spc_config_json.exists()


def test_malformed_control_plan_propagates_project_error(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)
    payload = _read_plan(project_root)
    payload["schema_version"] = 999  # unsupported schema version
    _write_plan(project_root, payload)

    with pytest.raises(ProjectError):
        build_spc_config_file(project_root)


def test_empty_control_plan_writes_empty_rows(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)
    _write_plan(project_root, _plan_payload([]))

    artifact = build_spc_config_file(project_root)
    assert artifact.rows == []

    reloaded = load_artifact(
        discover_project(project_root).spc_config_json, SPCConfigArtifact
    )
    assert reloaded.rows == []


def test_spc_dir_created_when_absent(tmp_path: Path) -> None:
    project_root = _make_project(tmp_path)
    spc_dir = project_root / "spc"
    assert not spc_dir.exists()

    build_spc_config_file(project_root)

    assert spc_dir.is_dir()
    assert (spc_dir / "config.json").exists()
