"""End-to-end loop integration test (W07-4, #90): Control Plan -> SPC -> FMEA.

Walks ONE real dataset through the whole Week-7 loop and proves the seam
between the two halves holds -- that the candidate FMEA feedback produced
from a real SPC out-of-control signal names the *original* FMEA cause the
Control Plan row was derived from (the join-key round-trip), and that the
human-in-the-loop invariant (candidate, never applied) survives the full
chain. The three unit suites (`test_control_plan_config.py`,
`test_fmea_feedback.py`, `apps/controlplan/tests/test_connector.py`) already
cover every unit in isolation with hand-built stubs at the boundary -- this
file does not repeat any of that, it only proves the seam.

Import strategy (load-bearing): `controlplan_app` / `fmea_app` are runnable
app folders on `sys.path` only when their own `conftest.py` runs, i.e. under
the full-workspace `uv run pytest` -- not under the isolated SPC gate
(`pytest apps/spc`). Guard the cross-app imports with `importorskip` so this
module skips cleanly there instead of erroring at collection.
"""

from __future__ import annotations

import pytest

pytest.importorskip("controlplan_app")
pytest.importorskip("fmea_app")

from pathlib import Path  # noqa: E402

import pandas as pd  # noqa: E402
from controlplan_app import connector  # noqa: E402

from fmea_app import rpn_engine  # noqa: E402
from spc_app import control_plan_config, fmea_feedback  # noqa: E402
from spc_app.spc_engine import control_charts, rule_detection, utils  # noqa: E402

# The Control Plan characteristic this test walks end-to-end, and its demo
# chart/stream binding -- mirrors the (streamlit-importing) page constant
# `_CHARACTERISTIC_STREAM_OVERRIDE` in `spc_app/pages/control_charts.py:64`
# (not imported here, per the spec, to avoid pulling in streamlit).
CHAR = "Prepreg Ply — Ply misalignment (>±2°)"
CHART_KEY = "Xbar-R"
STREAM = "ply_misalignment"

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FMEA_DEMO_CSV = _REPO_ROOT / "apps" / "fmea" / "data" / "composite_panel_fmea_demo.csv"
_SPC_DEMO_CSV = _REPO_ROOT / "apps" / "spc" / "data" / "demo_composites_aerospace.csv"


def _build_feedback() -> tuple[object, dict[str, dict[str, object]], dict[str, object] | None]:
    """The production session-state handoff, replayed head-to-tail.

    Returns (plan, source_index, feedback) so both tests can assert on the
    same golden-path walk without repeating the chain.
    """
    fmea_df = pd.read_csv(_FMEA_DEMO_CSV)
    fmea = rpn_engine.dataframe_to_relational(fmea_df)

    plan = connector.build_control_plan(fmea)
    idx = connector.source_index(fmea)

    # The SPC page reads a DataFrame from session state, not the dataset object
    # (controlplan_app/pages/control_plan.py:88 `_plan_to_df`).
    plan_df = pd.DataFrame([r.model_dump() for r in plan.rows])
    cfg = control_plan_config.config_for(plan_df, CHAR)
    assert cfg.chart_key is None  # connector always stamps recommended_chart=None (Q3)

    spc_df = pd.read_csv(_SPC_DEMO_CSV)
    stream_frame = spc_df[spc_df["stream"] == STREAM].copy()
    subgroups = utils.subgroup_rows(stream_frame)
    result = control_charts.compute_xbar_r(subgroups)
    sigma = result["sigma_hat"] / len(subgroups[0]) ** 0.5
    violations = rule_detection.detect_we_violations(
        result["subgroup_means"], cl=result["xbarbar"], sigma=sigma
    )

    # Snapshot the source row BEFORE the only call that could mutate it, so the
    # no-write-back assertion compares against a genuine pre-call copy (a snapshot
    # taken after the call would already carry any mutation and never fail).
    source_before = dict(idx[CHAR])

    feedback = fmea_feedback.build_occurrence_feedback(
        characteristic=CHAR,
        stream=STREAM,
        rule_set="Western Electric",
        violations=violations,
        total_points=len(result["subgroup_means"]),
        source=idx[CHAR],
    )
    return plan, idx, feedback, source_before


def test_loop_join_key_round_trips_on_real_sample_data():
    plan, idx, feedback, _source_before = _build_feedback()

    # Characteristic derivation: the #88/#89 producers agree on the same key
    # (belt-and-suspenders on the shared `_iter_named_modes`).
    assert CHAR in [row.characteristic for row in plan.rows]
    assert CHAR in idx

    # Loop fires on the real OOC stream.
    assert feedback is not None
    assert feedback["ooc"] is True

    # Join-key round-trip -- the core assertion.
    plan_row = next(row for row in plan.rows if row.characteristic == CHAR)
    assert feedback["source_cause_id"] == plan_row.source_cause_id
    assert feedback["source_cause_id"] == "F1::F1-M1::F1-M1-C1"
    assert (
        feedback["source_cause_description"]
        == "Operator error during manual layup — poor template visibility"
    )
    assert feedback["source_failure_mode_id"] == "F1-M1"


def test_loop_human_in_the_loop_invariant_end_to_end():
    _plan, idx, feedback, source_before = _build_feedback()
    assert feedback is not None

    # source_before is a pre-call snapshot (taken inside _build_feedback before
    # build_occurrence_feedback), so line ~125 is a real no-write-back check.
    assert source_before["occurrence"] == 4

    # current_occurrence echoes the FMEA's rating, unchanged by the chain.
    assert feedback["current_occurrence"] == 4

    # suggested_occurrence is a separate, computed candidate -- never applied.
    assert feedback["suggested_occurrence"] != feedback["current_occurrence"]
    assert feedback["suggested_occurrence"] == 10

    # Nothing in the chain writes back into the session-state source mapping.
    assert idx[CHAR] == source_before
