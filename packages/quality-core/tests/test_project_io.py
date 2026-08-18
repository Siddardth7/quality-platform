"""
tests/test_project_io.py
The load/write boundary for a project directory (`quality_core.project.io`, #276).

Covers the whole file graph (`discover_project` / `ProjectPaths`), the generic
load/write pair round-tripping every artifact byte-for-byte against the fixture
project, `load_optional_artifact`'s missing-vs-malformed split, and every
`ProjectError` branch (unreadable file, bad JSON/YAML, non-object top level,
schema_version mismatch, and pydantic errors with and without a field `loc`).
The overwrite-in-place / one-file-per-characteristic rule (SME resolution #1,
git-is-history) is pinned explicitly.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from quality_core.io.validate import IngestError
from quality_core.project.io import (
    CONTROL_PLAN_JSON,
    FEEDBACK_JSON,
    FMEA_JSON,
    GAGE_RR_JSON,
    PROJECT_YAML,
    SPC_CONFIG_JSON,
    SPC_RESULTS_DIR,
    ProjectError,
    discover_project,
    load_artifact,
    load_optional_artifact,
    load_project_meta,
    spc_result_path,
    spc_result_paths,
    write_artifact,
    write_project_meta,
)
from quality_core.project.schema import (
    ControlPlanArtifact,
    FMEAArtifact,
    MSAGageRRArtifact,
    SPCConfigArtifact,
    SPCMSAGateArtifact,
    SPCResultArtifact,
    SPCToFMEAFeedbackArtifact,
)

FIXTURES = Path(__file__).parent / "fixtures" / "project"

# (relative-path-parts, model) for every JSON artifact in the fixture project.
ARTIFACTS = [
    (("fmea", "fmea.json"), FMEAArtifact),
    (("control-plan", "plan.json"), ControlPlanArtifact),
    (("spc", "config.json"), SPCConfigArtifact),
    (("spc", "msa-gate.json"), SPCMSAGateArtifact),
    (("spc", "results", "example-characteristic.json"), SPCResultArtifact),
    (("msa", "gage-rr.json"), MSAGageRRArtifact),
    (("feedback", "spc-to-fmea.json"), SPCToFMEAFeedbackArtifact),
]


# ---------------------------------------------------------------------------
# discover_project / ProjectPaths — pure path arithmetic
# ---------------------------------------------------------------------------


def test_discover_project_builds_canonical_graph(tmp_path: Path) -> None:
    paths = discover_project(tmp_path)
    assert paths.root == tmp_path
    assert paths.project_yaml == tmp_path / PROJECT_YAML
    assert paths.fmea_json == tmp_path.joinpath(*FMEA_JSON)
    assert paths.control_plan_json == tmp_path.joinpath(*CONTROL_PLAN_JSON)
    assert paths.spc_config_json == tmp_path.joinpath(*SPC_CONFIG_JSON)
    assert paths.spc_results_dir == tmp_path.joinpath(*SPC_RESULTS_DIR)
    assert paths.gage_rr_json == tmp_path.joinpath(*GAGE_RR_JSON)
    assert paths.feedback_json == tmp_path.joinpath(*FEEDBACK_JSON)


def test_discover_project_does_not_touch_filesystem(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    paths = discover_project(missing)
    assert paths.root == missing
    assert not missing.exists()  # nothing was created


def test_discover_project_accepts_str_path(tmp_path: Path) -> None:
    paths = discover_project(str(tmp_path))
    assert paths.root == tmp_path


# ---------------------------------------------------------------------------
# spc_result_path / spc_result_paths — one file per characteristic
# ---------------------------------------------------------------------------


def test_spc_result_path_slugifies(tmp_path: Path) -> None:
    paths = discover_project(tmp_path)
    assert spc_result_path(paths, "Bore Diameter (mm)") == paths.spc_results_dir / "bore-diameter-mm.json"


def test_spc_result_path_rejects_punctuation_only_name(tmp_path: Path) -> None:
    paths = discover_project(tmp_path)
    with pytest.raises(ProjectError, match="no letters or digits"):
        spc_result_path(paths, "!!!")


def test_spc_result_paths_empty_when_dir_absent(tmp_path: Path) -> None:
    assert spc_result_paths(discover_project(tmp_path)) == []


def test_spc_result_paths_sorted_when_present(tmp_path: Path) -> None:
    paths = discover_project(tmp_path)
    paths.spc_results_dir.mkdir(parents=True)
    (paths.spc_results_dir / "b.json").write_text("{}", encoding="utf-8")
    (paths.spc_results_dir / "a.json").write_text("{}", encoding="utf-8")
    (paths.spc_results_dir / "ignore.txt").write_text("x", encoding="utf-8")
    assert spc_result_paths(paths) == [
        paths.spc_results_dir / "a.json",
        paths.spc_results_dir / "b.json",
    ]


# ---------------------------------------------------------------------------
# load_artifact — happy path + every error branch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("parts,model", ARTIFACTS)
def test_load_artifact_valid(parts: tuple[str, ...], model: type) -> None:
    art = load_artifact(FIXTURES.joinpath(*parts), model)
    assert art.schema_version == 1


def test_load_artifact_unreadable_path_raises(tmp_path: Path) -> None:
    # Reading a directory raises OSError inside _read_text.
    a_dir = tmp_path / "adir"
    a_dir.mkdir()
    with pytest.raises(ProjectError, match="Could not read"):
        load_artifact(a_dir, FMEAArtifact)


def test_load_artifact_invalid_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ProjectError, match="is not valid JSON"):
        load_artifact(bad, FMEAArtifact)


def test_load_artifact_non_object_top_level_raises(tmp_path: Path) -> None:
    arr = tmp_path / "arr.json"
    arr.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ProjectError, match="must hold a single object"):
        load_artifact(arr, FMEAArtifact)


def test_load_artifact_schema_version_mismatch_raises(tmp_path: Path) -> None:
    data = json.loads(FIXTURES.joinpath("msa", "gage-rr.json").read_text())
    data["schema_version"] = 999
    f = tmp_path / "gage-rr.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProjectError, match="declares schema_version 999.*reads schema_version 1"):
        load_artifact(f, MSAGageRRArtifact)


def test_load_artifact_field_error_names_the_field(tmp_path: Path) -> None:
    # A field-level pydantic error carries a `loc`, so the message names it.
    data = json.loads(FIXTURES.joinpath("msa", "gage-rr.json").read_text())
    data["n_parts"] = 0
    f = tmp_path / "gage-rr.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProjectError, match="at 'n_parts'"):
        load_artifact(f, MSAGageRRArtifact)


def test_load_artifact_model_level_error_has_no_field_locator(tmp_path: Path) -> None:
    # A model-validator error (duplicate characteristics) has an empty `loc`, so the
    # message has no " at '...'" suffix — this exercises the `if where else ""` branch.
    data = json.loads(FIXTURES.joinpath("control-plan", "plan.json").read_text())
    data["rows"] = [data["rows"][0], dict(data["rows"][0])]
    f = tmp_path / "plan.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProjectError) as exc:
        load_artifact(f, ControlPlanArtifact)
    assert "duplicate characteristic rows" in str(exc.value)
    assert " at '" not in str(exc.value)


def test_project_error_is_ingest_error() -> None:
    # A caller that already handles IngestError needs no third exception type.
    assert issubclass(ProjectError, IngestError)
    assert issubclass(ProjectError, ValueError)


# ---------------------------------------------------------------------------
# load_optional_artifact — missing returns None, malformed still raises
# ---------------------------------------------------------------------------


def test_load_optional_artifact_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_optional_artifact(tmp_path / "nope.json", FMEAArtifact) is None


def test_load_optional_artifact_raises_on_malformed_present_file(tmp_path: Path) -> None:
    bad = tmp_path / "present.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ProjectError):
        load_optional_artifact(bad, FMEAArtifact)


# ---------------------------------------------------------------------------
# project.yaml — load / round trip / error branches
# ---------------------------------------------------------------------------


def test_load_project_meta_valid() -> None:
    meta = load_project_meta(discover_project(FIXTURES))
    assert meta.project_id == "example-project"
    assert [c.name for c in meta.characteristics] == ["Example Characteristic"]


def test_load_project_meta_invalid_yaml_raises(tmp_path: Path) -> None:
    (tmp_path / PROJECT_YAML).write_text("a: b: c: :\n  - [", encoding="utf-8")
    with pytest.raises(ProjectError, match="is not valid YAML"):
        load_project_meta(discover_project(tmp_path))


def test_load_project_meta_non_mapping_raises(tmp_path: Path) -> None:
    (tmp_path / PROJECT_YAML).write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(ProjectError, match="must hold a single object"):
        load_project_meta(discover_project(tmp_path))


# ---------------------------------------------------------------------------
# Round trips — fixtures were written by these writers, so bytes must match
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("parts,model", ARTIFACTS)
def test_artifact_round_trip_is_byte_identical(parts: tuple[str, ...], model: type, tmp_path: Path) -> None:
    src = FIXTURES.joinpath(*parts)
    art = load_artifact(src, model)
    out = tmp_path / parts[-1]
    write_artifact(out, art)
    assert out.read_bytes() == src.read_bytes()


def test_project_meta_round_trip_is_byte_identical(tmp_path: Path) -> None:
    src_paths = discover_project(FIXTURES)
    meta = load_project_meta(src_paths)
    out_paths = discover_project(tmp_path)
    write_project_meta(out_paths, meta)
    assert out_paths.project_yaml.read_bytes() == src_paths.project_yaml.read_bytes()


def test_write_artifact_creates_parent_directories(tmp_path: Path) -> None:
    art = load_artifact(FIXTURES.joinpath(*FMEA_JSON), FMEAArtifact)
    target = tmp_path / "deep" / "nested" / "fmea.json"
    write_artifact(target, art)
    assert target.exists()


def test_full_fixture_project_round_trips(tmp_path: Path) -> None:
    """Acceptance criterion: the whole fixture project loads and round-trips."""
    src = discover_project(FIXTURES)
    dst = discover_project(tmp_path)

    write_project_meta(dst, load_project_meta(src))
    assert dst.project_yaml.read_bytes() == src.project_yaml.read_bytes()

    for parts, model in ARTIFACTS:
        art = load_artifact(FIXTURES.joinpath(*parts), model)
        out = tmp_path.joinpath(*parts)
        write_artifact(out, art)
        assert out.read_bytes() == FIXTURES.joinpath(*parts).read_bytes()

    # discover_project finds exactly the one SPC result that exists.
    assert spc_result_paths(dst) == [dst.spc_results_dir / "example-characteristic.json"]


# ---------------------------------------------------------------------------
# SME resolution #1 (git is history): re-run OVERWRITES, does not append/version
# ---------------------------------------------------------------------------


def test_second_write_overwrites_same_characteristic_file(tmp_path: Path) -> None:
    paths = discover_project(tmp_path)
    art = load_artifact(FIXTURES.joinpath("spc", "results", "example-characteristic.json"), SPCResultArtifact)
    dest = spc_result_path(paths, "Example Characteristic")

    write_artifact(dest, art)
    first = dest.read_text(encoding="utf-8")

    # Mutate a field and re-run for the SAME characteristic.
    art2 = art.model_copy(update={"generated_at": "2099-01-01T00:00:00Z"})
    write_artifact(dest, art2)

    # Exactly one file for this characteristic; it was replaced, not versioned.
    assert spc_result_paths(paths) == [dest]
    second = dest.read_text(encoding="utf-8")
    assert second != first
    assert "2099-01-01T00:00:00Z" in second
    assert "2026-08-13T12:00:00Z" not in second  # old content is gone, not appended
