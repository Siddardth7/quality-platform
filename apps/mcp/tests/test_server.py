"""The MCP server scaffold (#260): meta tool bodies, registration, and the entry point.

``@app.tool`` returns the original plain function, so ``health`` / ``version`` are called
directly here — no fake MCP client needed. ``main()`` is exercised with ``app.run``
patched out: the real call blocks forever serving the stdio protocol loop.
"""

import asyncio
from datetime import date

import pandas as pd
import pytest
from fastmcp.exceptions import ToolError
from mcp_app import __version__
from mcp_app.server import (
    app,
    fmea_get_scale,
    fmea_list_scales,
    fmea_run,
    fmea_run_relational,
    fmea_score,
    health,
    main,
    version,
)
from quality_core.schema import (
    Action,
    ActionStatus,
    FMEADataset,
    FMEARow,
    flat_to_relational,
)

from fmea_app.rpn_engine import ACTION_COLUMNS, dataframe_to_relational

# Reused verbatim from apps/fmea/tests/test_relational_pipeline.py: 3 rows, 2 functions,
# a shared (deduplicated) effect, non-monotonic IDs so ranking + adapter sort both matter.
_ROWS = [
    dict(ID=3, Process_Step="Mix", Component="Resin", Function="Bond layers",
         Failure_Mode="Uncured", Effect="Delamination", Severity=9,
         Cause="Low temperature", Occurrence=8, Current_Control="Oven", Detection=5),
    dict(ID=1, Process_Step="Seal", Component="Edge", Function="Seal edge",
         Failure_Mode="Void", Effect="Leak", Severity=6,
         Cause="Gap", Occurrence=3, Current_Control="Visual", Detection=7),
    dict(ID=2, Process_Step="Mix", Component="Resin", Function="Bond layers",
         Failure_Mode="Uncured", Effect="Delamination", Severity=9,
         Cause="Contamination", Occurrence=2, Current_Control="Oven", Detection=5),
]


def _relational_model_dict() -> dict:
    """The plain-dict form of the _ROWS relational model a JSON-RPC client would send."""
    df = pd.DataFrame(_ROWS)
    return dataframe_to_relational(df).model_dump()


def test_health_reports_ok():
    assert health() == {"status": "ok"}


def test_version_reports_package_version():
    assert version() == {"version": __version__}


def test_exactly_the_expected_tools_are_registered():
    # Proves the decorators registered every tool on the FastMCP app object, and that
    # nothing else crept in — a stray tool would otherwise go unnoticed until a later
    # M1 issue. `list_tools` is async in fastmcp 3.4.6, hence asyncio.run.
    # Naming convention (#260): meta tools unprefixed, domain tools `<domain>_`.
    tools = asyncio.run(app.list_tools())
    assert {tool.name for tool in tools} == {
        "health",
        "version",
        "fmea_score",
        "fmea_run",
        "fmea_run_relational",
        "fmea_list_scales",
        "fmea_get_scale",
    }


def test_main_runs_the_server(monkeypatch: pytest.MonkeyPatch):
    calls: list[bool] = []
    monkeypatch.setattr(app, "run", lambda: calls.append(True))
    main()
    assert calls == [True]


# ---------------------------------------------------------------------------
# fmea_score — golden RPN/AP (verified against quality_core.scoring, scale-independent)
# ---------------------------------------------------------------------------


def test_fmea_score_worst_case():
    assert fmea_score(10, 10, 10) == {"rpn": 1000, "action_priority": "High"}


def test_fmea_score_low():
    assert fmea_score(9, 1, 1) == {"rpn": 9, "action_priority": "Low"}


def test_fmea_score_medium():
    # S 7-8 band, O 4-5 band, D 5-6 column -> Medium in _AP_GRID; 8*4*5 == 160.
    assert fmea_score(8, 4, 5) == {"rpn": 160, "action_priority": "Medium"}


def test_fmea_score_is_scale_independent():
    # Loading/listing any scale must not perturb the pure-math scorers.
    fmea_list_scales()
    fmea_get_scale("2019")
    fmea_get_scale("fmea4")
    assert fmea_score(8, 4, 5) == {"rpn": 160, "action_priority": "Medium"}


# ---------------------------------------------------------------------------
# fmea_run — golden table over the flat pipeline
# ---------------------------------------------------------------------------


def test_fmea_run_golden_table_ranked_flagged_and_scored():
    rows = [
        dict(ID=1, Process_Step="A", Component="C1", Function="F1",
             Failure_Mode="M1", Effect="E1", Severity=9,
             Cause="X", Occurrence=3, Current_Control="V", Detection=4),   # RPN 108, Red
        dict(ID=2, Process_Step="B", Component="C2", Function="F2",
             Failure_Mode="M2", Effect="E2", Severity=2,
             Cause="Y", Occurrence=2, Current_Control="V", Detection=2),   # RPN 8, Green
        dict(ID=3, Process_Step="C", Component="C3", Function="F3",
             Failure_Mode="M3", Effect="E3", Severity=3,
             Cause="Z", Occurrence=5, Current_Control="V", Detection=5),   # RPN 75, Yellow
    ]
    out = fmea_run(rows)
    # RPN descending -> IDs [1, 3, 2]
    assert [r["ID"] for r in out] == [1, 3, 2]
    assert [r["RPN"] for r in out] == [108, 75, 8]
    # AP populated on every row (scalar action_priority per row)
    assert [r["AP"] for r in out] == ["Low", "Low", "Low"]
    # Risk_Tier spans all three tiers; Flag_High_Severity only for S>=9
    assert [r["Risk_Tier"] for r in out] == ["Red", "Yellow", "Green"]
    assert [r["Flag_High_Severity"] for r in out] == [True, False, False]


# ---------------------------------------------------------------------------
# fmea_run_relational — golden table + action-column variance
# ---------------------------------------------------------------------------


def test_fmea_run_relational_golden_table():
    out = fmea_run_relational(_relational_model_dict())
    assert [r["ID"] for r in out] == [3, 1, 2]
    assert [r["RPN"] for r in out] == [360, 126, 90]
    assert [r["AP"] for r in out] == ["High", "Low", "Medium"]
    # An action-free model omits ACTION_COLUMNS entirely.
    assert not any(c in out[0] for c in ACTION_COLUMNS)


def test_fmea_run_relational_action_bearing_model_adds_action_columns():
    dataset = FMEADataset(rows=[FMEARow(**r) for r in _ROWS])  # type: ignore[arg-type]
    model = flat_to_relational(dataset)
    model.functions[0].failure_modes[0].links[0].action = Action(
        owner="Quality Eng", status=ActionStatus.CLOSED, due=date(2026, 8, 1), o_after=1
    )
    out = fmea_run_relational(model.model_dump())
    assert all(c in out[0] for c in ACTION_COLUMNS)


# ---------------------------------------------------------------------------
# fmea_list_scales / fmea_get_scale happy paths (each if/elif arm)
# ---------------------------------------------------------------------------


def test_fmea_list_scales_returns_the_two_builtins():
    scales = fmea_list_scales()
    assert {s["id"] for s in scales} == {"2019", "fmea4"}
    assert all(s["name"] for s in scales)  # names come from the bundled files


def test_fmea_get_scale_default_2019():
    scale = fmea_get_scale("2019")
    assert set(scale) >= {"name", "severity", "occurrence", "detection"}


def test_fmea_get_scale_fmea4():
    scale = fmea_get_scale("fmea4")
    assert set(scale) >= {"name", "severity", "occurrence", "detection"}


def test_fmea_get_scale_custom_valid_json():
    valid = fmea_get_scale("2019")
    import json

    custom = fmea_get_scale(
        "custom",
        json.dumps(
            {
                "severity": valid["severity"],
                "occurrence": valid["occurrence"],
                "detection": valid["detection"],
            }
        ),
    )
    assert set(custom) >= {"severity", "occurrence", "detection"}


# ---------------------------------------------------------------------------
# Edge cases (spec §4) — each engine ValueError/ValidationError flows through as ToolError
# ---------------------------------------------------------------------------


def test_fmea_score_out_of_range_raises_toolerror():
    with pytest.raises(ToolError, match="Severity score 11 is out of range"):
        fmea_score(11, 1, 1)


def test_fmea_score_out_of_range_carries_endash_range():
    # The engine's own message uses an en-dash; _call must not rewrite it.
    with pytest.raises(ToolError, match="Valid range is 1–10"):
        fmea_score(0, 1, 1)


def test_fmea_run_empty_rows_raises_toolerror():
    with pytest.raises(ToolError, match="Input DataFrame is empty"):
        fmea_run([])


def test_fmea_run_missing_column_raises_toolerror():
    with pytest.raises(ToolError, match="Missing required column"):
        fmea_run([{"ID": 1}])


def test_fmea_run_relational_invalid_model_raises_toolerror():
    # Structurally invalid model -> pydantic ValidationError arm of _call.
    with pytest.raises(ToolError, match="validation error"):
        fmea_run_relational({"functions": [{"id": "f1"}]})


def test_fmea_get_scale_custom_without_json_raises_toolerror():
    with pytest.raises(ToolError, match="requires custom_json"):
        fmea_get_scale("custom", None)


def test_fmea_get_scale_custom_bad_json_raises_toolerror():
    with pytest.raises(ToolError, match="Could not parse rating-scale JSON"):
        fmea_get_scale("custom", "not json")


def test_fmea_get_scale_unknown_id_raises_toolerror():
    with pytest.raises(ToolError, match="Unknown scale_id 'bogus'"):
        fmea_get_scale("bogus")
