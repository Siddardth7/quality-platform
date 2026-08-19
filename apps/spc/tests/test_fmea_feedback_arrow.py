"""Tests for the SPC → FMEA project-file arrow (M3-4, #279) — the "living FMEA" leg.

Holds ``spc_app.fmea_feedback_arrow`` to 100% line+branch.

The committed project fixture (``packages/quality-core/tests/fixtures/project``) is copied
into ``tmp_path`` per test (``fmea/`` + ``control-plan/`` + ``spc/``), so writes and the
in-place ``fmea/fmea.json`` mutation never touch the committed fixture. The oracle for the
feedback rows is ``build_occurrence_feedback`` computed directly, exactly as M3-3's arrow
test uses ``control_plan_config`` as its oracle.

SME decision Q1 (spec top block) OVERRODE the spec body's OPEN-QUESTION #1 recommendation:
multiple simultaneously-OOC characteristics EXTEND the schema into N rows — they do NOT
raise ``ProjectError``. ``test_multiple_ooc_writes_multiple_rows`` pins the approved
behaviour; the spec body's obligation #3 ("more than one OOC → ProjectError") is superseded.
"""
from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest
from quality_core.project import (
    ProjectError,
    SPCToFMEAFeedbackArtifact,
    SPCToFMEAFeedbackRow,
    discover_project,
    load_artifact,
)
from quality_core.schema.relational import (
    Cause,
    Control,
    Effect,
    FailureLink,
    FailureMode,
    Function,
    RelationalFMEA,
)

from spc_app.fmea_feedback import build_occurrence_feedback
from spc_app.fmea_feedback_arrow import (
    _FEEDBACK_ACTION_OWNER,
    _resolve_source_cause,
    build_feedback_file,
)

_FIXTURE_PROJECT = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "quality-core"
    / "tests"
    / "fixtures"
    / "project"
)

_SENTINEL_TS = "1999-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# Fixture-project helpers — copy the committed subtree, read/write its JSON.
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path, *, subtrees: tuple[str, ...] = ("fmea", "control-plan", "spc")) -> Path:
    for sub in subtrees:
        shutil.copytree(_FIXTURE_PROJECT / sub, tmp_path / sub)
    return tmp_path


def _read(path: Path) -> dict:
    return json.loads(path.read_text())


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload))


def _fmea_path(root: Path) -> Path:
    return root / "fmea" / "fmea.json"


def _plan_path(root: Path) -> Path:
    return root / "control-plan" / "plan.json"


def _result_path(root: Path, name: str = "example-characteristic") -> Path:
    return root / "spc" / "results" / f"{name}.json"


def _link_action(root: Path) -> dict | None:
    """The single fixture link's ``action`` dict (or None) in fmea/fmea.json."""
    fmea = _read(_fmea_path(root))
    return fmea["fmea"]["functions"][0]["failure_modes"][0]["links"][0]["action"]


def _cause_occurrence(root: Path) -> int:
    fmea = _read(_fmea_path(root))
    return fmea["fmea"]["functions"][0]["failure_modes"][0]["causes"][0]["occurrence"]


# The oracle: what build_occurrence_feedback produces for the fixture's one OOC row.
_FIXTURE_SOURCE: dict[str, object] = {
    "failure_mode_id": "F1-M1",
    "cause_id": "F1::F1-M1::F1-M1-C1",
    "cause_description": "Tool wear",
    "occurrence": 4,
    "component": "Bracket",
}


def _fixture_oracle() -> dict[str, object]:
    payload = build_occurrence_feedback(
        characteristic="Example Characteristic",
        stream="Example Characteristic",
        rule_set="Western Electric",
        violations=[{"index": 3, "rule": "Rule 1"}],
        total_points=5,
        source=_FIXTURE_SOURCE,
    )
    assert payload is not None
    return payload


# ---------------------------------------------------------------------------
# 1. Happy path — one OOC characteristic
# ---------------------------------------------------------------------------


def test_happy_path_writes_feedback_and_applies_action(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    paths = discover_project(root)

    artifact = build_feedback_file(root)

    # Feedback file written and reloadable.
    assert artifact is not None
    assert paths.feedback_json.exists()
    reloaded = load_artifact(paths.feedback_json, SPCToFMEAFeedbackArtifact)
    assert reloaded.rows == artifact.rows

    # Rows match the independent build_occurrence_feedback oracle exactly.
    oracle = _fixture_oracle()
    assert len(artifact.rows) == 1
    assert artifact.rows[0].model_dump() == SPCToFMEAFeedbackRow.model_validate(oracle).model_dump()
    # The fixture's hand-authored suggested_occurrence (6) is illustrative; the real
    # engine maps ooc_rate 0.2 → 9. Pin the engine value, not the fixture's.
    assert artifact.rows[0].suggested_occurrence == 9

    # Candidate Action landed on the affected FailureLink in fmea/fmea.json.
    action = _link_action(root)
    assert action is not None
    assert action["o_after"] == 9
    assert action["status"] == "Open"
    assert action["owner"] == _FEEDBACK_ACTION_OWNER
    # Cause.occurrence is NEVER overwritten — the "candidate, never applied" discipline.
    assert _cause_occurrence(root) == 4


def test_happy_path_provenance_recorded(tmp_path: Path) -> None:
    # Acceptance criterion: which chart (stream/characteristic), which rule (rule_set/rules),
    # which period (violating_points / ooc_rate) live in the feedback row.
    root = _make_project(tmp_path)
    row = build_feedback_file(root).rows[0]  # type: ignore[union-attr]
    assert row.stream == "Example Characteristic"
    assert row.characteristic == "Example Characteristic"
    assert row.rule_set == "Western Electric"
    assert row.rules == ["Rule 1"]
    assert row.violating_points == 1
    assert row.ooc_rate == pytest.approx(0.2)
    assert row.source_failure_mode_id == "F1-M1"
    assert row.source_cause_id == "F1::F1-M1::F1-M1-C1"
    assert row.current_occurrence == 4


def test_both_files_stamped_with_spc_app_provenance(tmp_path: Path) -> None:
    # Coder flag #2: when the arrow rewrites fmea/fmea.json it stamps a FULL fresh
    # envelope — generated_by="spc_app==<ver>" as well as generated_at. Pin both the
    # feedback file's and the rewritten fmea.json's generated_by.
    root = _make_project(tmp_path)
    artifact = build_feedback_file(root)
    assert artifact is not None
    assert artifact.generated_by.startswith("spc_app==")
    fmea = _read(_fmea_path(root))
    assert fmea["generated_by"].startswith("spc_app==")


# ---------------------------------------------------------------------------
# 2. Multi-OOC (SME-approved schema extension) → multiple rows, one file
# ---------------------------------------------------------------------------


def _add_second_ooc_characteristic(root: Path) -> None:
    """Add function F2 (Shaft runout), its plan row and an OOC spc result."""
    fmea = _read(_fmea_path(root))
    fmea["fmea"]["functions"].append(
        {
            "id": "F2",
            "process_step": "Grinding",
            "component": "Shaft",
            "description": "Hold runout within print",
            "failure_modes": [
                {
                    "id": "F2-M1",
                    "description": "Runout high",
                    "effects": [{"id": "F2-M1-E1", "description": "Vibration", "severity": 6}],
                    "causes": [{"id": "F2-M1-C1", "description": "Wheel wear", "occurrence": 3}],
                    "controls": [{"id": "F2-M1-CT1", "description": "Dial check", "detection": 4}],
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
    )
    _write(_fmea_path(root), fmea)

    plan = _read(_plan_path(root))
    second = copy.deepcopy(plan["rows"][0])
    second["characteristic"] = "Shaft runout"
    second["source_cause_id"] = "F2::F2-M1::F2-M1-C1"
    plan["rows"].append(second)
    _write(_plan_path(root), plan)

    result = _read(_result_path(root))
    result["characteristic"] = "Shaft runout"
    result["control_chart"]["stream"] = "Shaft runout"
    # 2 distinct violating points of 5 → ooc_rate 0.4 → occurrence 10 (distinct from 9).
    result["control_chart"]["violations"] = [
        {"index": 1, "rule": "Rule 1"},
        {"index": 2, "rule": "Rule 1"},
    ]
    _write(_result_path(root, "shaft-runout"), result)


def test_multiple_ooc_writes_multiple_rows(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    _add_second_ooc_characteristic(root)

    artifact = build_feedback_file(root)
    assert artifact is not None

    by_name = {row.characteristic: row for row in artifact.rows}
    assert set(by_name) == {"Example Characteristic", "Shaft runout"}
    assert by_name["Example Characteristic"].suggested_occurrence == 9
    assert by_name["Shaft runout"].suggested_occurrence == 10

    # Both causes got their own candidate Action on the matching link.
    fmea = _read(_fmea_path(root))
    actions = {
        fn["id"]: fn["failure_modes"][0]["links"][0]["action"]
        for fn in fmea["fmea"]["functions"]
    }
    assert actions["F1"]["o_after"] == 9
    assert actions["F2"]["o_after"] == 10


# ---------------------------------------------------------------------------
# 3. No OOC anywhere → None, stale feedback deleted, fmea untouched
# ---------------------------------------------------------------------------


def test_no_ooc_returns_none_and_deletes_stale_feedback(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    result = _read(_result_path(root))
    result["control_chart"]["violations"] = []
    _write(_result_path(root), result)

    paths = discover_project(root)
    paths.feedback_json.parent.mkdir(parents=True, exist_ok=True)
    paths.feedback_json.write_text('{"stale": true}')
    before = _read(_fmea_path(root))

    assert build_feedback_file(root) is None
    assert not paths.feedback_json.exists()
    # No Action to set/clear → fmea.json left byte-identical (no generated_at bump).
    assert _read(_fmea_path(root)) == before


def test_no_spc_results_at_all_returns_none(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    shutil.rmtree(root / "spc" / "results")
    assert build_feedback_file(root) is None


# ---------------------------------------------------------------------------
# 4/5. Unresolvable / None source_cause_id → feedback written, fmea untouched
# ---------------------------------------------------------------------------


def test_unresolvable_source_cause_writes_feedback_without_applying(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    plan = _read(_plan_path(root))
    # Real format, but names a cause absent from fmea.json.
    plan["rows"][0]["source_cause_id"] = "F1::F1-M1::F1-M1-CNOPE"
    _write(_plan_path(root), plan)
    before = _read(_fmea_path(root))

    artifact = build_feedback_file(root)
    assert artifact is not None
    assert artifact.rows[0].source_cause_id is None
    assert artifact.rows[0].current_occurrence is None
    # Nothing resolved → no Action anywhere, fmea.json byte-identical.
    assert _read(_fmea_path(root)) == before


def test_none_source_cause_writes_feedback_without_applying(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    plan = _read(_plan_path(root))
    plan["rows"][0]["source_cause_id"] = None
    _write(_plan_path(root), plan)
    before = _read(_fmea_path(root))

    artifact = build_feedback_file(root)
    assert artifact is not None
    assert artifact.rows[0].source_cause_id is None
    assert _read(_fmea_path(root)) == before


# ---------------------------------------------------------------------------
# 6/7/8. Missing / malformed required inputs → ProjectError, nothing written
# ---------------------------------------------------------------------------


def test_missing_fmea_raises_and_writes_nothing(tmp_path: Path) -> None:
    root = _make_project(tmp_path, subtrees=("control-plan", "spc"))
    paths = discover_project(root)
    with pytest.raises(ProjectError):
        build_feedback_file(root)
    assert not paths.feedback_json.exists()


def test_missing_control_plan_raises_and_writes_nothing(tmp_path: Path) -> None:
    root = _make_project(tmp_path, subtrees=("fmea", "spc"))
    paths = discover_project(root)
    before = _read(_fmea_path(root))
    with pytest.raises(ProjectError):
        build_feedback_file(root)
    assert not paths.feedback_json.exists()
    assert _read(_fmea_path(root)) == before


def test_malformed_fmea_raises(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    fmea = _read(_fmea_path(root))
    fmea["schema_version"] = 999
    _write(_fmea_path(root), fmea)
    with pytest.raises(ProjectError):
        build_feedback_file(root)


# ---------------------------------------------------------------------------
# 9. Human-authored Action left untouched
# ---------------------------------------------------------------------------


def test_human_authored_action_left_untouched(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    fmea = _read(_fmea_path(root))
    human = {"owner": "Jane Doe", "status": "In-Progress", "due": None,
             "s_after": None, "o_after": 2, "d_after": None}
    fmea["fmea"]["functions"][0]["failure_modes"][0]["links"][0]["action"] = human
    _write(_fmea_path(root), fmea)
    before = _read(_fmea_path(root))

    artifact = build_feedback_file(root)
    # Feedback still written (the arrow does not raise); fmea.json's human Action survives.
    assert artifact is not None
    assert _read(_fmea_path(root)) == before
    assert _link_action(root) == human


# ---------------------------------------------------------------------------
# 10. Idempotency — a second identical run does not rewrite fmea.json
# ---------------------------------------------------------------------------


def test_idempotency_second_run_does_not_rewrite_fmea(tmp_path: Path) -> None:
    root = _make_project(tmp_path)

    first = build_feedback_file(root)
    assert first is not None
    action_after_first = _link_action(root)

    # Stamp a sentinel generated_at into fmea.json. A truly idempotent second run leaves
    # the Action unchanged → _apply_or_clear_actions reports no change → fmea.json is NOT
    # rewritten → the sentinel survives. (Robust against same-second clock granularity,
    # unlike a raw byte-compare.)
    fmea = _read(_fmea_path(root))
    fmea["generated_at"] = _SENTINEL_TS
    _write(_fmea_path(root), fmea)

    second = build_feedback_file(root)
    assert second is not None
    assert second.rows == first.rows
    assert _read(_fmea_path(root))["generated_at"] == _SENTINEL_TS  # no rewrite happened
    assert _link_action(root) == action_after_first

    # Exactly one feedback file at the fixed path — no accumulation.
    feedback_dir = root / "feedback"
    assert [p.name for p in feedback_dir.iterdir()] == ["spc-to-fmea.json"]


# ---------------------------------------------------------------------------
# 11. Stabilization — OOC applied, then violations clear → Action cleared, file deleted
# ---------------------------------------------------------------------------


def test_stabilization_clears_prior_action_and_feedback(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    paths = discover_project(root)

    build_feedback_file(root)
    assert _link_action(root) is not None  # our candidate Action is there
    assert paths.feedback_json.exists()

    # Characteristic stabilises: its chart trips no rule this run.
    result = _read(_result_path(root))
    result["control_chart"]["violations"] = []
    _write(_result_path(root), result)

    assert build_feedback_file(root) is None
    assert _link_action(root) is None  # our Action cleared back to None
    assert not paths.feedback_json.exists()
    # Cause.occurrence was never touched throughout.
    assert _cause_occurrence(root) == 4


# ---------------------------------------------------------------------------
# 12. _resolve_source_cause unit cases — every branch directly
# ---------------------------------------------------------------------------


def _one_cause_fmea() -> RelationalFMEA:
    return RelationalFMEA(
        functions=[
            Function(
                id="F1",
                process_step="Final machining",
                component="Bracket",
                description="Hold the bore",
                failure_modes=[
                    FailureMode(
                        id="F1-M1",
                        description="Bore oversize",
                        effects=[Effect(id="F1-M1-E1", description="Loose fit", severity=7)],
                        causes=[Cause(id="F1-M1-C1", description="Tool wear", occurrence=4)],
                        controls=[Control(id="F1-M1-CT1", description="Gauge", detection=5)],
                        links=[
                            FailureLink(
                                row_id=1,
                                effect_id="F1-M1-E1",
                                cause_id="F1-M1-C1",
                                control_id="F1-M1-CT1",
                            )
                        ],
                    )
                ],
            )
        ]
    )


def test_resolve_source_cause_valid() -> None:
    fmea = _one_cause_fmea()
    resolved = _resolve_source_cause(fmea, "F1::F1-M1::F1-M1-C1")
    assert resolved is not None
    function, failure_mode, cause = resolved
    assert (function.id, failure_mode.id, cause.id) == ("F1", "F1-M1", "F1-M1-C1")


def test_resolve_source_cause_wrong_part_count() -> None:
    assert _resolve_source_cause(_one_cause_fmea(), "F1-M1-C1") is None  # no "::" → 1 part


def test_resolve_source_cause_unknown_function() -> None:
    assert _resolve_source_cause(_one_cause_fmea(), "FX::F1-M1::F1-M1-C1") is None


def test_resolve_source_cause_unknown_failure_mode() -> None:
    assert _resolve_source_cause(_one_cause_fmea(), "F1::F1-MX::F1-M1-C1") is None


def test_resolve_source_cause_unknown_cause() -> None:
    assert _resolve_source_cause(_one_cause_fmea(), "F1::F1-M1::F1-M1-CX") is None


# ---------------------------------------------------------------------------
# 13. Capability-only result present → skipped, no crash; multi-cause link skip
# ---------------------------------------------------------------------------


def test_capability_result_is_skipped(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    capability = {
        "schema_version": 1,
        "generated_at": "2026-08-13T12:00:00Z",
        "generated_by": "spc_app==0.14.0",
        "kind": "capability",
        "characteristic": "Cap Char",
        "control_chart": None,
        "capability": {
            "stream_label": "Cap Char",
            "values": [10.0, 10.1, 9.9],
            "capability": {"cp": 1.2},
            "lsl": None,
            "usl": None,
            "normality": {"w_stat": 0.98, "p_value": 0.6, "is_normal": True},
            "oos_signal_count": 0,
        },
    }
    _write(_result_path(root, "cap-char"), capability)

    # The OOC control chart still drives a row; the capability file is silently skipped.
    artifact = build_feedback_file(root)
    assert artifact is not None
    assert [r.characteristic for r in artifact.rows] == ["Example Characteristic"]


def test_second_cause_link_skipped_when_iterating_other_cause(tmp_path: Path) -> None:
    # A failure mode with TWO causes and TWO links: iterating cause C1 must `continue`
    # past C2's link (link.cause_id != cause.id) and vice-versa, so only C1's link (the
    # OOC one) gets the Action. Exercises the inner-loop skip branch end-to-end.
    root = _make_project(tmp_path)
    fmea = _read(_fmea_path(root))
    fm = fmea["fmea"]["functions"][0]["failure_modes"][0]
    fm["causes"].append({"id": "F1-M1-C2", "description": "Fixture slip", "occurrence": 5})
    fm["effects"].append({"id": "F1-M1-E2", "description": "Scrap", "severity": 8})
    fm["controls"].append({"id": "F1-M1-CT2", "description": "SPC chart", "detection": 3})
    fm["links"].append(
        {
            "row_id": 2,
            "effect_id": "F1-M1-E2",
            "cause_id": "F1-M1-C2",
            "control_id": "F1-M1-CT2",
            "action": None,
        }
    )
    _write(_fmea_path(root), fmea)

    build_feedback_file(root)

    fmea_out = _read(_fmea_path(root))
    links = {lk["row_id"]: lk["action"] for lk in fmea_out["fmea"]["functions"][0]["failure_modes"][0]["links"]}
    # Only C1's link (row 1, the plan-joined OOC cause) carries our candidate.
    assert links[1] is not None and links[1]["o_after"] == 9
    assert links[2] is None
