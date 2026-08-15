"""Contract tests that drive every tool through the real FastMCP client layer (#268).

``test_server.py`` calls the tool bodies directly — ``@app.tool`` hands back the plain
function, so nothing there exercises the *protocol*: generated input schemas, argument
binding, or content-block serialization. This module closes that gap with fastmcp's
in-memory transport (``Client(app)``: no subprocess, no network, no auth middleware).

The 13 export tools are the point. A direct call returns a ``File``/``Image`` Python
object; a client call must serialize it into a base64 ``EmbeddedResource`` /
``ImageContent`` block, which nothing tested until now. The other 30 tools get one
compact round-trip each so a serialization regression anywhere is visible.

``list_tools`` / ``call_tool`` are async and no ``pytest-asyncio`` plugin is installed
in the workspace, so every test wraps its body in ``asyncio.run`` — the same pattern as
``test_server.py:114``. Golden inputs and expectations are lifted verbatim from
``test_server.py`` so a mismatch points at the boundary, never at the arithmetic.
"""

import asyncio
import base64
import inspect
import math
import shutil
import tempfile
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcp import types as mcp_types
from mcp_app import __version__
from mcp_app import server as server_module
from mcp_app.server import app, fmea_run, spc_freeze_imr, spc_freeze_xbar_r, spc_freeze_xbar_s

from fmea_app.rpn_engine import dataframe_to_relational

# ---------------------------------------------------------------------------
# Harness — ~10 lines, no class, no plugin. One client per call keeps every test
# independent of event-loop lifecycle (spec §"Edge cases").
# ---------------------------------------------------------------------------


def _run(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run one coroutine to completion (no pytest-asyncio in this workspace)."""
    return asyncio.run(coro)


async def _call(name: str, arguments: dict[str, Any]) -> Any:
    async with Client(app) as client:
        return await client.call_tool(name, arguments)


def _call_tool(name: str, **arguments: Any) -> Any:
    """Invoke a tool through the in-memory MCP transport and return the CallToolResult."""
    return _run(_call(name, arguments))


async def _list() -> list[mcp_types.Tool]:
    async with Client(app) as client:
        return await client.list_tools()


# The client's view of the roster: `mcp.types.Tool` with the generated `inputSchema`,
# not the server-side `FunctionTool` objects `app.list_tools()` hands back.
_TOOLS = {tool.name: tool for tool in _run(_list())}


def _check(actual: Any, expected: Any) -> None:
    """Assert `actual` matches `expected`; dicts compare as subsets, floats approximately."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict)
        for key, value in expected.items():
            _check(actual[key], value)
    elif isinstance(expected, list):
        assert isinstance(actual, list)
        assert len(actual) == len(expected)
        for actual_item, expected_item in zip(actual, expected):
            _check(actual_item, expected_item)
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=1e-3)
    else:
        assert actual == expected


# ---------------------------------------------------------------------------
# Golden inputs (verbatim from test_server.py)
# ---------------------------------------------------------------------------

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
_RELATIONAL_MODEL = dataframe_to_relational(pd.DataFrame(_ROWS)).model_dump()

# A throwaway project dir with the committed fixture's fmea/ subtree, for the
# controlplan_build_from_project round trip (it reads/writes a project directory, so it
# needs a real path rather than an in-memory model). mkdtemp so parametrize can name it at
# collection time; the tool writes control-plan/plan.json into it when it runs.
_FIXTURE_PROJECT = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "quality-core"
    / "tests"
    / "fixtures"
    / "project"
)
_CP_PROJECT_ROOT = Path(tempfile.mkdtemp())
shutil.copytree(_FIXTURE_PROJECT / "fmea", _CP_PROJECT_ROOT / "fmea")

# A second throwaway project dir with the committed fixture's control-plan/ subtree, for
# the spc_config_from_project round trip (M3-3, #278): it reads control-plan/plan.json and
# writes spc/config.json into it when the tool runs.
_SPC_PROJECT_ROOT = Path(tempfile.mkdtemp())
shutil.copytree(_FIXTURE_PROJECT / "control-plan", _SPC_PROJECT_ROOT / "control-plan")

# A third throwaway project dir, for the spc_fmea_feedback_from_project round trip (M3-4,
# #279): that arrow reads spc/results/*.json, control-plan/plan.json and fmea/fmea.json, and
# writes feedback/spc-to-fmea.json plus a candidate Action back into fmea/fmea.json — so it
# gets its own copy rather than mutating either root above.
_FEEDBACK_PROJECT_ROOT = Path(tempfile.mkdtemp())
for _subtree in ("fmea", "control-plan", "spc"):
    shutil.copytree(_FIXTURE_PROJECT / _subtree, _FEEDBACK_PROJECT_ROOT / _subtree)

# A fourth throwaway project dir, for the spc_msa_gate_from_project round trip (M3-5,
# #280): that arrow reads spc/config.json and msa/gage-rr.json and writes
# spc/msa-gate.json, so it gets its own copy too.
_GATE_PROJECT_ROOT = Path(tempfile.mkdtemp())
for _subtree in ("spc", "msa"):
    shutil.copytree(_FIXTURE_PROJECT / _subtree, _GATE_PROJECT_ROOT / _subtree)

# A fifth throwaway project dir, for the run_project_loop round trip (M3-6, #281). It uses
# the committed worked example rather than the shape fixture above: the loop re-derives
# control-plan/plan.json from fmea/fmea.json, and only the example's five input files agree
# end to end (see apps/mcp/tests/test_project_loop.py's note). Inputs only — the loop has to
# produce the rest itself.
_LOOP_PROJECT_ROOT = Path(tempfile.mkdtemp())
_EXAMPLE_PROJECT = Path(__file__).resolve().parents[3] / "examples" / "secom-quality-loop"
for _subtree in ("fmea", "msa", "spc"):
    shutil.copytree(_EXAMPLE_PROJECT / _subtree, _LOOP_PROJECT_ROOT / _subtree)

_FMEA_FLAT_ROWS = [
    dict(ID=1, Process_Step="A", Component="C1", Function="F1",
         Failure_Mode="M1", Effect="E1", Severity=9,
         Cause="X", Occurrence=3, Current_Control="V", Detection=4),
    dict(ID=2, Process_Step="B", Component="C2", Function="F2",
         Failure_Mode="M2", Effect="E2", Severity=2,
         Cause="Y", Occurrence=2, Current_Control="V", Detection=2),
    dict(ID=3, Process_Step="C", Component="C3", Function="F3",
         Failure_Mode="M3", Effect="E3", Severity=3,
         Cause="Z", Occurrence=5, Current_Control="V", Detection=5),
]

XBAR_R_SAMPLE = [[10, 11, 12, 13, 14], [11, 12, 13, 14, 15], [9, 10, 11, 12, 13]]
XBAR_S_SAMPLE = [list(range(1, 13)), list(range(2, 14)), list(range(3, 15))]
IMR_SAMPLE = [10, 12, 11, 15, 14]
XBAR_R_PHASE_II_DATA = [[20, 21, 22, 23, 24], [19, 18, 17, 16, 15]]
XBAR_S_PHASE_II_DATA = [list(range(20, 32)), list(range(30, 18, -1))]
IMR_PHASE_II_DATA = [50, 55, 48, 60, 52, 47]
EWMA_VALUES = [11.0, 9.5, 10.2, 10.8, 9.9]
MU0 = 10.0
SIGMA = 1.0
NORMAL_DATA = np.random.default_rng(0).normal(10.0, 0.5, size=40).tolist()

# Baselines built by direct calls: these are *inputs* to the Phase II tools, not oracles.
_FROZEN_XBAR_R = spc_freeze_xbar_r(XBAR_R_SAMPLE)
_FROZEN_XBAR_S = spc_freeze_xbar_s(XBAR_S_SAMPLE)
_FROZEN_IMR = spc_freeze_imr(IMR_SAMPLE)

_FMEA_SCORED = fmea_run(_ROWS)

_CC_KW: dict[str, Any] = dict(
    chart_label="Xbar-R Chart",
    stream="ply_thickness",
    rule_set="Western Electric",
    points=[10.0, 10.5, 13.9, 9.8, 10.1],
    cl=10.0,
    ucl=12.0,
    lcl=8.0,
    violations=[{"index": 2, "rule": "Rule 1: beyond 3-sigma"}],
    metrics=[("Xbarbar", "10.0000"), ("Rbar", "1.2000")],
)
_CAP_KW: dict[str, Any] = dict(
    stream_label="Ply Thickness",
    values=[10.0, 10.1, 9.9, 10.2, 9.8, 10.05],
    capability={
        "cp": 1.45, "cpk": 1.21, "pp": 1.40, "ppk": 1.18,
        "mean": 10.0, "sigma_hat": 0.05, "sigma_overall": 0.06,
    },
    lsl=9.7,
    usl=10.3,
    normality={"w_stat": 0.98, "p_value": 0.61, "is_normal": True},
    oos_signal_count=0,
)
_MSA_STUDY = [
    {"part": "P01", "appraiser": "A", "trial": 1, "measurement": 10.05},
    {"part": "P01", "appraiser": "A", "trial": 2, "measurement": 10.02},
    {"part": "P02", "appraiser": "B", "trial": 1, "measurement": 9.98},
    {"part": "P02", "appraiser": "B", "trial": 2, "measurement": 10.01},
]
_MSA_RESULTS = {
    "ev": 0.03, "av": 0.02, "grr": 0.036, "pv": 0.5, "tv": 0.501,
    "pev_study": 5.99, "pav_study": 3.99, "pgrr_study": 7.19, "ppv_study": 99.80,
    "pev_tolerance": 10.0, "pav_tolerance": 8.0, "pgrr_tolerance": 12.0,
    "ppv_tolerance": 150.0, "ndc": 6, "verdict": "Accept", "mean": 10.0,
    "n_parts": 2, "n_appraisers": 2, "n_trials": 2, "is_balanced": True,
    "method": "average_and_range",
    "method_note": "Average-and-Range method: the part x appraiser interaction is NOT estimated.",
}

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------------------
# Schema contract — the generated JSON Schema every MCP client reads (new for all 43)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_name", sorted(_TOOLS))
def test_generated_input_schema_matches_the_python_signature(tool_name: str) -> None:
    # The schema is what a client binds arguments against: a parameter missing from
    # `properties` is uncallable, and a defaulted parameter wrongly in `required`
    # makes an otherwise-valid call fail before the tool body ever runs.
    schema = _TOOLS[tool_name].inputSchema
    properties = set(schema.get("properties", {}))
    required = set(schema.get("required", []))
    parameters = inspect.signature(getattr(server_module, tool_name)).parameters
    assert required <= properties
    assert properties == set(parameters)
    assert required == {
        name for name, p in parameters.items() if p.default is inspect.Parameter.empty
    }


def test_fmea_score_input_schema_is_the_declared_json_schema() -> None:
    # One tool pinned exactly: types and required list are inferred from the
    # annotations, so a signature change is a client-visible contract change.
    assert _TOOLS["fmea_score"].inputSchema == {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "severity": {"type": "integer"},
            "occurrence": {"type": "integer"},
            "detection": {"type": "integer"},
        },
        "required": ["severity", "occurrence", "detection"],
    }


# ---------------------------------------------------------------------------
# Round trip through the client — the 30 JSON-returning tools
# ---------------------------------------------------------------------------

_ROUND_TRIPS: list[tuple[str, dict[str, Any], Any]] = [
    ("health", {}, {"status": "ok"}),
    ("version", {}, {"version": __version__}),
    (
        "fmea_score",
        {"severity": 10, "occurrence": 10, "detection": 10},
        {"rpn": 1000, "action_priority": "High"},
    ),
    (
        "fmea_run",
        {"rows": _FMEA_FLAT_ROWS},
        [
            {"ID": 1, "RPN": 108, "Risk_Tier": "Red", "Flag_High_Severity": True},
            {"ID": 3, "RPN": 75, "Risk_Tier": "Yellow"},
            {"ID": 2, "RPN": 8, "Risk_Tier": "Green"},
        ],
    ),
    (
        "fmea_run_relational",
        {"model": _RELATIONAL_MODEL},
        [
            {"ID": 3, "RPN": 360, "AP": "High"},
            {"ID": 1, "RPN": 126, "AP": "Low"},
            {"ID": 2, "RPN": 90, "AP": "Medium"},
        ],
    ),
    (
        "fmea_list_scales",
        {},
        [
            {"id": "2019", "name": "AIAG & VDA 2019 PFMEA (default)"},
            {"id": "fmea4", "name": "AIAG FMEA-4 (legacy)"},
        ],
    ),
    (
        "fmea_get_scale",
        {"scale_id": "2019"},
        {"name": "AIAG & VDA 2019 PFMEA (default)"},
    ),
    (
        "spc_xbar_r",
        {"subgroups": XBAR_R_SAMPLE},
        {
            "subgroup_means": [12.0, 13.0, 11.0],
            "ranges": [4.0, 4.0, 4.0],
            "ucl_x": 14.308,
            "lcl_x": 9.692,
            "ucl_r": 8.456,
        },
    ),
    (
        "spc_xbar_s",
        {"subgroups": XBAR_S_SAMPLE},
        {
            "ucl_x": 7.5 + 0.886 * math.sqrt(13.0),
            "sigma_hat": math.sqrt(13.0) / 0.9776,
        },
    ),
    (
        "spc_imr",
        {"values": IMR_SAMPLE},
        {"moving_ranges": [2.0, 1.0, 4.0, 1.0], "ucl_x": 17.72, "lcl_x": 7.08},
    ),
    (
        "spc_p",
        {"defective_counts": [3, 5, 4], "sample_sizes": [100, 120, 80]},
        {"pbar": 0.04, "proportions": [0.03, 5 / 120, 0.05]},
    ),
    ("spc_c", {"defect_counts": [4, 7, 5, 6]}, {"cbar": 5.5}),
    (
        "spc_u",
        {"defect_counts": [2, 4, 3], "sample_sizes": [1.0, 2.0, 1.5]},
        {"ubar": 2.0},
    ),
    (
        "spc_ewma",
        {"values": EWMA_VALUES, "mu0": MU0, "sigma": SIGMA},
        {
            # z0 seeds from mu0, not x0; z1 recurses on z0 (test_spc_ewma.py:41-54).
            "z": [
                0.2 * 11.0 + 0.8 * MU0,
                0.2 * 9.5 + 0.8 * (0.2 * 11.0 + 0.8 * MU0),
                10.088,
                10.2304,
                10.16432,
            ],
            "lam": 0.20,
            "L": 2.860,
            "pairing_adequate": True,
        },
    ),
    (
        "spc_cusum",
        {"values": [11.0, 9.5, 10.2], "mu0": MU0, "sigma": SIGMA},
        {"c_plus": [0.5, 0.0, 0.0], "k": 0.5, "h": 5.0, "fir": False},
    ),
    (
        "spc_freeze_xbar_r",
        {"baseline": XBAR_R_SAMPLE},
        {"chart_type": "xbar_r", "n": 5, "sigma_method": "Rbar/d2", "baseline_adequate": False},
    ),
    (
        "spc_freeze_xbar_s",
        {"baseline": XBAR_S_SAMPLE},
        {"chart_type": "xbar_s", "n": 12, "sigma_method": "Sbar/c4", "center_line": 7.5},
    ),
    (
        "spc_freeze_imr",
        {"baseline": IMR_SAMPLE},
        {"chart_type": "imr", "sigma_method": "MRbar/d2", "center_line": 12.4},
    ),
    (
        "spc_apply_xbar_r",
        {"subgroups": XBAR_R_PHASE_II_DATA, "frozen": _FROZEN_XBAR_R},
        # Limits come from the frozen baseline; the plotted points are the new data's.
        {
            "subgroup_means": [22.0, 17.0],
            "ucl_x": _FROZEN_XBAR_R["ucl_x"],
            "lcl_x": _FROZEN_XBAR_R["lcl_x"],
        },
    ),
    (
        "spc_apply_xbar_s",
        {"subgroups": XBAR_S_PHASE_II_DATA, "frozen": _FROZEN_XBAR_S},
        {"ucl_x": _FROZEN_XBAR_S["ucl_x"], "ucl_s": _FROZEN_XBAR_S["ucl_disp"]},
    ),
    (
        "spc_apply_imr",
        {"values": IMR_PHASE_II_DATA, "frozen": _FROZEN_IMR},
        {"values": [50.0, 55.0, 48.0, 60.0, 52.0, 47.0], "ucl_x": _FROZEN_IMR["ucl_x"]},
    ),
    (
        "spc_detect_we_violations",
        {"points": [0.1, 0.2, 3.2], "cl": 0.0, "sigma": 1.0},
        [{"index": 2, "rule": "Western Electric Rule 1"}],
    ),
    (
        "spc_detect_nelson_violations",
        {"points": [1.0] * 9, "cl": 0.0, "sigma": 1.0},
        [{"index": 8, "rule": "Nelson Rule 2"}],
    ),
    (
        "spc_capability",
        {"data": NORMAL_DATA, "lsl": 8.0, "usl": 12.0, "force_method": "normal"},
        {"method": "normal", "ci_estimator": "sample_sd_ddof1", "ci_df": 39, "stable": None},
    ),
    ("spc_normality_test", {"data": NORMAL_DATA}, {"is_normal": True}),
    (
        "spc_assess_stability",
        {"values": [1.0, 2.0] * 5, "subgroups": list(range(1, 11)), "chart_type": "I-MR"},
        {"signals": []},
    ),
    (
        "msa_gage_rr",
        {"study": _MSA_STUDY, "tolerance": 4.42},
        {"method": "average_and_range", "n_parts": 2, "n_appraisers": 2, "n_trials": 2},
    ),
    (
        "controlplan_build",
        {"fmea_model": _RELATIONAL_MODEL},
        [
            {
                "characteristic": "Resin — Uncured",
                "measurement_method": "Oven",
                "sample_plan_is_placeholder": True,
                "recommended_chart": None,
            },
            {"characteristic": "Edge — Void", "measurement_method": "Visual"},
        ],
    ),
    (
        "controlplan_recommend_chart",
        {"data_type": "variable", "subgroup_size": 9},
        {"recommended_chart": "Xbar-R"},
    ),
    (
        "controlplan_source_index",
        {"fmea_model": _RELATIONAL_MODEL},
        {
            "Resin — Uncured": {
                "occurrence": 8,
                "cause_description": "Low temperature",
                "component": "Resin",
            }
        },
    ),
    (
        "controlplan_build_from_project",
        {"project_root": str(_CP_PROJECT_ROOT)},
        {
            "schema_version": 1,
            "rows": [
                {
                    "characteristic": "Bracket — Bore oversize",
                    "source_cause_id": "F1::F1-M1::F1-M1-C1",
                    "sample_plan_is_placeholder": True,
                    "recommended_chart": None,
                }
            ],
        },
    ),
    (
        "spc_config_from_project",
        {"project_root": str(_SPC_PROJECT_ROOT)},
        {
            "schema_version": 1,
            "rows": [
                {
                    "characteristic": "Example Characteristic",
                    "chart_key": "Xbar-R",
                    "lsl": 9.5,
                    "usl": 10.5,
                    "sample_size": 5,
                }
            ],
        },
    ),
    (
        "spc_msa_gate_from_project",
        {"project_root": str(_GATE_PROJECT_ROOT)},
        {
            "schema_version": 1,
            "rows": [
                {
                    "characteristic": "Example Characteristic",
                    "verdict": "Accept",
                    "gate_status": "pass",
                }
            ],
        },
    ),
    (
        "spc_fmea_feedback_from_project",
        {"project_root": str(_FEEDBACK_PROJECT_ROOT)},
        {
            "schema_version": 1,
            "rows": [
                {
                    "characteristic": "Example Characteristic",
                    "ooc": True,
                    "violating_points": 1,
                    "source_cause_id": "F1::F1-M1::F1-M1-C1",
                    "current_occurrence": 4,
                    "suggested_occurrence": 9,
                }
            ],
        },
    ),
    (
        "run_project_loop",
        {"project_root": str(_LOOP_PROJECT_ROOT)},
        {
            "control_plan": {
                "rows": [
                    {"characteristic": "Etch chamber — Chamber parameter drift"},
                    {"characteristic": "Wet bench — Residue left after clean"},
                ]
            },
            "spc_config": {
                "rows": [
                    {"characteristic": "Etch chamber — Chamber parameter drift"},
                    {"characteristic": "Wet bench — Residue left after clean"},
                ]
            },
            "msa_gate": {
                "rows": [
                    {"verdict": "Accept", "gate_status": "pass"},
                    {"verdict": None, "gate_status": "warn"},
                ]
            },
            "feedback": {
                "rows": [
                    {
                        "characteristic": "Etch chamber — Chamber parameter drift",
                        "stream": "sensor_220",
                        "ooc": True,
                        "source_cause_id": "ETCH::ETCH-M1::ETCH-M1-C1",
                        "current_occurrence": 3,
                        "suggested_occurrence": 7,
                    }
                ]
            },
        },
    ),
]


@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected"),
    _ROUND_TRIPS,
    ids=[entry[0] for entry in _ROUND_TRIPS],
)
def test_tool_round_trips_through_the_client(
    tool_name: str, arguments: dict[str, Any], expected: Any
) -> None:
    # Same golden inputs as the direct-call tests, so a mismatch is unambiguously
    # a boundary/serialization defect rather than an engine one.
    result = _call_tool(tool_name, **arguments)
    _check(result.data, expected)


def test_round_trip_table_covers_every_non_export_tool() -> None:
    # Tripwire: a new JSON-returning tool must gain a client-level round trip here,
    # not merely a direct-call test in test_server.py.
    export_tools = {name for name, *_ in _FILE_EXPORTS} | {name for name, *_ in _IMAGE_EXPORTS}
    assert {name for name, *_ in _ROUND_TRIPS} == set(_TOOLS) - export_tools


def test_structured_content_carries_the_same_payload_as_data() -> None:
    # `data` is fastmcp's deserialized view; `content` is what crosses the wire.
    result = _call_tool("fmea_score", severity=10, occurrence=10, detection=10)
    (block,) = result.content
    assert isinstance(block, mcp_types.TextContent)
    assert block.text == '{"rpn":1000,"action_priority":"High"}'


# ---------------------------------------------------------------------------
# Export tools — the genuinely untested layer: File/Image -> MCP content blocks
# ---------------------------------------------------------------------------

_FILE_EXPORTS: list[tuple[str, dict[str, Any], str, bytes]] = [
    ("export_csv", {"table": _FMEA_SCORED}, "application/csv", b"ID,"),
    ("fmea_export_excel", {"rows": _FMEA_SCORED}, "application/xlsx", b"PK"),
    ("fmea_export_pdf", {"rows": _FMEA_SCORED}, "application/pdf", b"%PDF"),
    ("spc_export_control_chart_excel", _CC_KW, "application/xlsx", b"PK"),
    ("spc_export_control_chart_pdf", _CC_KW, "application/pdf", b"%PDF"),
    ("spc_export_capability_excel", _CAP_KW, "application/xlsx", b"PK"),
    ("spc_export_capability_pdf", _CAP_KW, "application/pdf", b"%PDF"),
    (
        "msa_export_excel",
        {"study": _MSA_STUDY, "results": _MSA_RESULTS, "usl": 10.5, "lsl": 9.5},
        "application/xlsx",
        b"PK",
    ),
    ("msa_export_pdf", {"study": _MSA_STUDY, "results": _MSA_RESULTS}, "application/pdf", b"%PDF"),
    ("msa_export_study_csv", {"study": _MSA_STUDY}, "application/csv", b"part,"),
    ("msa_export_results_csv", {"results": _MSA_RESULTS}, "application/csv", b"EV,AV,GRR,"),
]

_IMAGE_EXPORTS: list[tuple[str, dict[str, Any]]] = [
    ("fmea_chart_pareto_png", {"rows": _FMEA_SCORED}),
    ("fmea_chart_heatmap_png", {"rows": _FMEA_SCORED}),
]


@pytest.mark.parametrize(
    ("tool_name", "arguments", "mime_type", "magic"),
    _FILE_EXPORTS,
    ids=[entry[0] for entry in _FILE_EXPORTS],
)
def test_file_export_serializes_to_a_blob_resource_block(
    tool_name: str, arguments: dict[str, Any], mime_type: str, magic: bytes
) -> None:
    # A direct call hands back a `File` object; only the client path base64-encodes it
    # into an embedded blob resource. Decoding it proves the bytes survived intact.
    result = _call_tool(tool_name, **arguments)
    (block,) = result.content
    assert isinstance(block, mcp_types.EmbeddedResource)
    resource = block.resource
    assert isinstance(resource, mcp_types.BlobResourceContents)
    assert resource.mimeType == mime_type
    assert base64.b64decode(resource.blob).startswith(magic)


@pytest.mark.parametrize(
    ("tool_name", "arguments"), _IMAGE_EXPORTS, ids=[entry[0] for entry in _IMAGE_EXPORTS]
)
def test_png_chart_serializes_to_an_image_block(
    tool_name: str, arguments: dict[str, Any]
) -> None:
    result = _call_tool(tool_name, **arguments)
    (block,) = result.content
    assert isinstance(block, mcp_types.ImageContent)
    assert block.mimeType == "image/png"
    assert base64.b64decode(block.data).startswith(_PNG_MAGIC)


def test_export_csv_sanitization_survives_the_client_serialization() -> None:
    # The formula-injection escape must still be in the bytes a client actually
    # receives — not only in the File object the direct-call test inspects.
    result = _call_tool("export_csv", table=[{"note": "=cmd|'/bin/calc'", "num": "-3.0000"}])
    (block,) = result.content
    assert isinstance(block, mcp_types.EmbeddedResource)
    resource = block.resource
    assert isinstance(resource, mcp_types.BlobResourceContents)
    text = base64.b64decode(resource.blob).decode("utf-8")
    assert "'=cmd|'/bin/calc'" in text
    assert "-3.0000" in text
    assert "'-3.0000" not in text


# ---------------------------------------------------------------------------
# Error propagation — one representative case each; every tool body's error
# branches are already covered directly in test_server.py.
# ---------------------------------------------------------------------------


def test_tool_error_propagates_through_call_tool() -> None:
    with pytest.raises(ToolError, match="Severity score 11 is out of range"):
        _call_tool("fmea_score", severity=11, occurrence=1, detection=1)


def test_unknown_argument_is_rejected_before_the_tool_body_runs() -> None:
    # Argument binding happens in the MCP layer against the generated schema, so a
    # misnamed parameter fails there — a failure mode a direct call cannot produce.
    with pytest.raises(ToolError, match="Unexpected keyword argument"):
        _call_tool("spc_imr", data=IMR_SAMPLE)


def test_unknown_tool_name_is_rejected_by_the_client() -> None:
    with pytest.raises(ToolError, match="Unknown tool"):
        _call_tool("fmea_scoer", severity=1, occurrence=1, detection=1)
