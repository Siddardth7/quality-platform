"""``run_project_loop`` — the M3-6 (#281) loop orchestrator, and the worked example it drives.

Split out of ``test_server.py`` for the same reason ``test_transport.py`` is: this file is
about one tool's *sequencing* behaviour and about the committed
``examples/secom-quality-loop/`` demo, not about the per-tool wrappers. ``mcp_app.server``
is gated at 100% line+branch, and ``run_project_loop`` is covered here.

``@app.tool`` returns the original plain function, so the tool is called directly.

No project directory is ever mutated in place: every test copies its fixture (the shared
``packages/quality-core/tests/fixtures/project/`` one, or the committed example) into
``tmp_path`` first.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastmcp.exceptions import ToolError
from mcp_app.server import run_project_loop

_REPO_ROOT = Path(__file__).resolve().parents[3]

#: Every test here drives the committed worked example rather than
#: ``packages/quality-core/tests/fixtures/project/``. That fixture is a per-file shape
#: fixture, not a loop-coherent project — its hand-written ``control-plan/plan.json`` and
#: ``spc/results/*.json`` name a characteristic its ``fmea/fmea.json`` does not derive, so
#: a full loop re-derives the plan and the SPC result stops joining. The example is the
#: only project in the repo whose five input files agree end to end, which is exactly what
#: an orchestrator test needs — and it means the shipped demo is exercised by every test
#: in this file, not only by the two that name it.
_EXAMPLE_PROJECT = _REPO_ROOT / "examples" / "secom-quality-loop"

#: The owner stamped on every Action the SPC → FMEA arrow writes — the provenance pointer
#: from ``fmea/fmea.json`` back to ``feedback/spc-to-fmea.json``. Duplicated here (not
#: imported from ``spc_app.fmea_feedback_arrow``, where it is private) so this test pins the
#: contract a reader of the FMEA file actually sees.
_FEEDBACK_ACTION_OWNER = "SPC feedback arrow (feedback/spc-to-fmea.json)"

#: The example's monitored characteristic — the one with a committed SPC result.
_EXAMPLE_CHARACTERISTIC = "Etch chamber — Chamber parameter drift"


def _copy_inputs(source: Path, destination: Path) -> Path:
    """Copy a project's *input* files only — the loop must produce the rest itself."""
    for sub in ("fmea", "control-plan", "msa", "spc"):
        if (source / sub).is_dir():
            shutil.copytree(source / sub, destination / sub)
    if (source / "project.yaml").exists():
        shutil.copy(source / "project.yaml", destination / "project.yaml")
    return destination


def _seeded_project(tmp_path: Path) -> Path:
    """A writable copy of the worked example's input files, in ``tmp_path``."""
    return _copy_inputs(_EXAMPLE_PROJECT, tmp_path)


def _links(fmea_json: Path) -> list[dict[str, Any]]:
    payload = json.loads(fmea_json.read_text(encoding="utf-8"))
    return [
        link
        for function in payload["fmea"]["functions"]
        for failure_mode in function["failure_modes"]
        for link in failure_mode["links"]
    ]


# ---------------------------------------------------------------------------
# 1. Happy path — one full loop writes all four files
# ---------------------------------------------------------------------------


def test_run_project_loop_writes_every_downstream_file(tmp_path: Path):
    root = _seeded_project(tmp_path)

    result = run_project_loop(str(root))

    assert set(result) == {"control_plan", "spc_config", "msa_gate", "feedback"}
    assert (root / "control-plan" / "plan.json").exists()
    assert (root / "spc" / "config.json").exists()
    assert (root / "spc" / "msa-gate.json").exists()
    assert (root / "feedback" / "spc-to-fmea.json").exists()
    # Each value is the corresponding arrow tool's own return shape, unwrapped.
    assert result["control_plan"]["generated_by"].startswith("controlplan_app==")
    assert result["spc_config"]["generated_by"].startswith("spc_app==")
    assert [row["characteristic"] for row in result["msa_gate"]["rows"]] == [
        _EXAMPLE_CHARACTERISTIC,
        "Wet bench — Residue left after clean",
    ]
    assert result["feedback"] is not None
    assert [row["characteristic"] for row in result["feedback"]["rows"]] == [
        _EXAMPLE_CHARACTERISTIC
    ]


# ---------------------------------------------------------------------------
# 2. The acceptance criterion: the FMEA actually changes, with provenance
# ---------------------------------------------------------------------------


def test_run_project_loop_attaches_provenance_tracked_action_to_the_fmea(tmp_path: Path):
    root = _seeded_project(tmp_path)
    fmea_json = root / "fmea" / "fmea.json"
    before = json.loads(fmea_json.read_text(encoding="utf-8"))
    # Precondition, asserted rather than assumed: nothing is proposed yet.
    assert all(link["action"] is None for link in _links(fmea_json))
    before_occurrence = before["fmea"]["functions"][0]["failure_modes"][0]["causes"][0][
        "occurrence"
    ]

    result = run_project_loop(str(root))

    after = json.loads(fmea_json.read_text(encoding="utf-8"))
    actions = [link["action"] for link in _links(fmea_json) if link["action"] is not None]
    assert len(actions) == 1
    action = actions[0]
    assert action["owner"] == _FEEDBACK_ACTION_OWNER
    assert action["status"] == "Open"
    # The two files agree — the Action is not trusted on its own.
    feedback_row = json.loads((root / "feedback" / "spc-to-fmea.json").read_text())["rows"][0]
    assert action["o_after"] == feedback_row["suggested_occurrence"]
    assert action["o_after"] == result["feedback"]["rows"][0]["suggested_occurrence"]
    # The candidate discipline: the *rating* is never touched, only the proposal.
    after_occurrence = after["fmea"]["functions"][0]["failure_modes"][0]["causes"][0]["occurrence"]
    assert after_occurrence == before_occurrence
    assert feedback_row["current_occurrence"] == before_occurrence
    # The arrow rewrote the envelope, because something actually changed.
    assert (after["generated_by"], after["generated_at"]) != (
        before["generated_by"],
        before["generated_at"],
    )


# ---------------------------------------------------------------------------
# 3. Idempotency — a second loop is a no-op on fmea.json
# ---------------------------------------------------------------------------


def test_run_project_loop_twice_leaves_the_fmea_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _seeded_project(tmp_path)
    fmea_json = root / "fmea" / "fmea.json"
    feedback_json = root / "feedback" / "spc-to-fmea.json"

    # Pin every artifact-write timestamp to a *distinct, increasing* value. The feedback
    # arrow's _now() is otherwise second-precision, so two back-to-back loops land in the
    # same wall-clock second and a fmea.json that is wrongly *rewritten* on run 2 would
    # still come out byte-identical — hiding exactly the idempotency bug this test exists
    # to catch (weakening ``if link.action != wanted`` to ``if True``). With a moving
    # clock, correct code (which does NOT rewrite fmea.json on run 2) leaves it identical,
    # while any rewrite stamps a new generated_at and fails the byte compare.
    ticks = iter(f"2026-08-15T00:00:{second:02d}Z" for second in range(60))
    monkeypatch.setattr("spc_app.fmea_feedback_arrow._now", lambda: next(ticks))

    run_project_loop(str(root))
    after_first = fmea_json.read_bytes()
    first_rows = json.loads(feedback_json.read_text(encoding="utf-8"))["rows"]

    run_project_loop(str(root))

    # Compared against run 1's output, not the pre-loop original: run 1 is meant to change it.
    assert fmea_json.read_bytes() == after_first
    # The feedback envelope's generated_at legitimately moves; its rows must not.
    assert json.loads(feedback_json.read_text(encoding="utf-8"))["rows"] == first_rows


# ---------------------------------------------------------------------------
# 4. Failure paths that are actually reachable *through the loop*
#
# Not every arrow's required-input failure is reachable from here, and writing a test for
# one that is not would be a dead test dressed up as coverage:
#   - Step 2 reads control-plan/plan.json, which step 1 has just written — it cannot be
#     missing by the time step 2 runs.
#   - Step 3 reads spc/config.json, which step 2 has just written — likewise.
#   - Step 5 reads fmea/fmea.json (step 1 already required it) and control-plan/plan.json
#     (step 1 wrote it) — likewise.
# Each of those arrows' standalone missing-input failures is covered in test_server.py.
# What *is* reachable: a missing fmea.json at step 1 (the loop's only true external
# required input beyond the seeded SPC results), and a malformed pre-existing optional
# input — msa/gage-rr.json, which only step 3 reads.
# ---------------------------------------------------------------------------


def test_run_project_loop_without_an_fmea_fails_at_the_control_plan_step(tmp_path: Path):
    with pytest.raises(ToolError, match="fmea.json"):
        run_project_loop(str(tmp_path))
    assert not (tmp_path / "control-plan" / "plan.json").exists()


def test_run_project_loop_fails_at_the_msa_gate_step_on_a_malformed_gage_study(tmp_path: Path):
    """A malformed msa/gage-rr.json stops the loop at step 3, not earlier and not silently.

    Steps 1 and 2 still succeed and leave their files on disk: a partially-run loop is a
    resumable state, not a broken one (the tool docstring's own claim, asserted).
    """
    root = _seeded_project(tmp_path)
    (root / "msa" / "gage-rr.json").write_text('{"schema_version": 1, "verdict": 4}')

    with pytest.raises(ToolError, match="gage-rr.json"):
        run_project_loop(str(root))

    assert (root / "control-plan" / "plan.json").exists()
    assert (root / "spc" / "config.json").exists()
    assert not (root / "spc" / "msa-gate.json").exists()


# ---------------------------------------------------------------------------
# 4b. A human-authored Action on the OOC link is never clobbered by the loop
#
# The feedback arrow's owner guard (``_apply_or_clear_actions``: skip a link whose
# ``Action`` someone else owns) is what keeps the loop from overwriting a human's work.
# Nothing else in this file authors a human action, so this test exists specifically to
# make that guard load-bearing — drop the guard and this must fail.
# ---------------------------------------------------------------------------


def test_run_project_loop_preserves_a_human_authored_action_on_the_ooc_link(tmp_path: Path):
    root = _seeded_project(tmp_path)
    fmea_json = root / "fmea" / "fmea.json"
    payload = json.loads(fmea_json.read_text(encoding="utf-8"))
    # Put a human-owned Action on the ETCH link — the very link the feedback step targets.
    human_action = {
        "owner": "Jane Doe (process engineer)",
        "status": "In-Progress",
        "due": None,
        "s_after": None,
        "o_after": 5,
        "d_after": None,
    }
    payload["fmea"]["functions"][0]["failure_modes"][0]["links"][0]["action"] = human_action
    fmea_json.write_text(json.dumps(payload), encoding="utf-8")

    result = run_project_loop(str(root))

    # The characteristic is still out of control (the feedback row is still produced) ...
    assert [row["characteristic"] for row in result["feedback"]["rows"]] == [
        _EXAMPLE_CHARACTERISTIC
    ]
    # ... but the human's Action on that link is left exactly as authored, not overwritten
    # with the arrow's candidate.
    actions = [link["action"] for link in _links(fmea_json) if link["action"] is not None]
    assert len(actions) == 1
    assert actions[0] == human_action
    assert actions[0]["owner"] != _FEEDBACK_ACTION_OWNER


# ---------------------------------------------------------------------------
# 5. Zero SPC results — a legal no-op for the feedback step
# ---------------------------------------------------------------------------


def test_run_project_loop_with_no_spc_results_returns_null_feedback(tmp_path: Path):
    root = _seeded_project(tmp_path)
    shutil.rmtree(root / "spc" / "results")

    result = run_project_loop(str(root))

    assert result["feedback"] is None
    assert not (root / "feedback" / "spc-to-fmea.json").exists()
    # The three upstream steps still ran.
    assert (root / "spc" / "msa-gate.json").exists()
    assert all(link["action"] is None for link in _links(root / "fmea" / "fmea.json"))


# ---------------------------------------------------------------------------
# 6. The committed worked example (examples/secom-quality-loop/), tied to CI
# ---------------------------------------------------------------------------


def test_committed_example_spc_result_is_really_out_of_control():
    """The demo's whole point is a real SECOM violation — assert it before running anything.

    A wrong signal choice must fail loudly here, not ship as a quietly broken example.
    """
    result_path = _EXAMPLE_PROJECT / "spc" / "results" / "etch-chamber-chamber-parameter-drift.json"
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    chart = payload["control_chart"]
    assert payload["characteristic"] == _EXAMPLE_CHARACTERISTIC
    assert chart["stream"] == "sensor_220"  # the real SECOM column, empirically chosen
    assert len(chart["violations"]) >= 1
    assert len(chart["points"]) == 226


def test_run_project_loop_on_the_committed_example(tmp_path: Path):
    """The example is exercised, not just described — prose about it cannot rot silently."""
    root = _copy_inputs(_EXAMPLE_PROJECT, tmp_path)
    fmea_json = root / "fmea" / "fmea.json"
    assert all(link["action"] is None for link in _links(fmea_json))

    result = run_project_loop(str(root))

    # Two characteristics are planned and gated; only the one with an SPC result feeds back.
    assert [row["characteristic"] for row in result["spc_config"]["rows"]] == [
        _EXAMPLE_CHARACTERISTIC,
        "Wet bench — Residue left after clean",
    ]
    assert [(row["characteristic"], row["gate_status"]) for row in result["msa_gate"]["rows"]] == [
        (_EXAMPLE_CHARACTERISTIC, "pass"),
        ("Wet bench — Residue left after clean", "warn"),
    ]
    assert [row["characteristic"] for row in result["feedback"]["rows"]] == [
        _EXAMPLE_CHARACTERISTIC
    ]

    # The README's documented diff: Occurrence 3 stays 3; a candidate Action proposes 7.
    row = result["feedback"]["rows"][0]
    assert (row["current_occurrence"], row["suggested_occurrence"]) == (3, 7)
    actions = [link["action"] for link in _links(fmea_json) if link["action"] is not None]
    assert len(actions) == 1
    assert actions[0]["owner"] == _FEEDBACK_ACTION_OWNER
    assert (actions[0]["o_after"], actions[0]["status"]) == (7, "Open")
