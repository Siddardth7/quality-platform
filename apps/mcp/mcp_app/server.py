"""The quality-platform MCP server: FastMCP app, stdio transport, meta + FMEA tools.

This module is the M1-1 foundation (#260); M1-3 (#262) added the FMEA tools. Every later
domain tool (SPC, MSA, Control Plan, SECOM) lands on this same ``app`` object in this same
module — the CI coverage gate targets ``mcp_app.server`` only, so a separate tools module
would silently stop being covered.

``mcp_app`` is the one intentional exception to the workspace's "apps never import each
other" rule (SME sign-off, #262): it is the aggregator whose job is wrapping domain-app
engines. Peer apps still never import peers — see ``tests/test_import_boundary.py``.

Tool namespace convention (fixed now so later tools don't re-litigate it, #260 decision 2):
meta tools that describe the server process itself stay flat and unprefixed (``health``,
``version``); every future engine tool gets a ``<domain>_`` prefix (e.g.
``fmea_action_priority``, ``spc_capability``, ``msa_gage_rr``) so this server's tool list
stays legible when a host also has other MCP servers connected.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import ValidationError
from quality_core.schema import RelationalFMEA
from quality_core.scoring import action_priority, rpn

from fmea_app.rating_scales import (
    load_default_scales,
    load_legacy_fmea4_scales,
    load_scales_from_json,
)
from fmea_app.rpn_engine import run_pipeline, run_pipeline_relational
from mcp_app import __version__

app = FastMCP("quality-platform")

_T = TypeVar("_T")


def _call(fn: Callable[..., _T], /, *args: Any, **kwargs: Any) -> _T:
    """Run an engine function, converting its input errors into a ``ToolError``.

    The FMEA engines raise plain ``ValueError`` for bad input (``validate_input``, ``rpn``,
    ``action_priority``, the scale loaders); ``RelationalFMEA.model_validate`` raises
    pydantic's ``ValidationError``. Both are "the caller sent bad data", so both become
    FastMCP's own structured error type — a client never sees a traceback, and never
    depends on ``mask_error_details`` staying off. (``ValidationError`` subclasses
    ``ValueError`` in pydantic v2, so it is caught either way; naming it is defensive and
    self-documenting.)
    """
    try:
        return fn(*args, **kwargs)
    except (ValueError, ValidationError) as exc:
        raise ToolError(str(exc)) from exc


def _scored_records(scored: pd.DataFrame) -> list[dict[str, Any]]:
    """Add the per-row AIAG-VDA Action Priority to a scored pipeline frame, as records.

    ``run_pipeline`` produces RPN, the criticality flags and ``Risk_Tier`` but no ``AP``
    column, so AP comes from the scalar ``quality_core.scoring.action_priority``. Records
    orientation keeps the payload JSON-friendly — no DataFrame goes over the wire.

    Shared by ``fmea_run`` and ``fmea_run_relational``: the relational pipeline flattens to
    the same frame shape, so the post-processing is byte-identical for both.
    """
    scored["AP"] = [
        _call(action_priority, s, o, d)
        for s, o, d in zip(
            scored["Severity"], scored["Occurrence"], scored["Detection"], strict=True
        )
    ]
    # pandas types record keys as Hashable; every FMEA column name is a str, and the same
    # cast is how rpn_engine.py bridges this (lines 150, 457).
    return cast("list[dict[str, Any]]", scored.to_dict(orient="records"))


@app.tool
def health() -> dict[str, str]:
    """Liveness probe: proves the request loop is up end-to-end."""
    return {"status": "ok"}


@app.tool
def version() -> dict[str, str]:
    """Report the running quality-platform MCP server build."""
    return {"version": __version__}


@app.tool
def fmea_score(severity: int, occurrence: int, detection: int) -> dict[str, int | str]:
    """Score one Severity/Occurrence/Detection triple: RPN + AIAG-VDA Action Priority.

    Pure lookup — the agent never computes RPN/AP itself. Both are scale-independent: the
    2019 AP table is baked into the engine, so the rating scale chosen for *describing*
    S/O/D never changes these numbers. Raises a structured tool error (not a stack trace)
    if any rating is outside the AIAG 1-10 scale.
    """
    return {
        "rpn": _call(rpn, severity, occurrence, detection),
        "action_priority": _call(action_priority, severity, occurrence, detection),
    }


@app.tool
def fmea_run(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run the full FMEA pipeline (validate -> RPN -> AP -> flags -> rank) over rows.

    Each row needs the 11 required FMEA columns (ID, Process_Step, Component, Function,
    Failure_Mode, Effect, Severity, Cause, Occurrence, Current_Control, Detection). Returns
    rows ranked by RPN descending, each with RPN, AP, the three criticality flags and
    Risk_Tier. Raises a structured tool error on invalid input — never a stack trace.
    """
    scored = _call(run_pipeline, pd.DataFrame(rows))
    return _scored_records(scored)


@app.tool
def fmea_run_relational(model: dict[str, Any]) -> list[dict[str, Any]]:
    """Run the full FMEA pipeline over a relational model supplied as a JSON object.

    ``model`` is a RelationalFMEA (Function -> FailureMode -> Effect/Cause/Control, tied
    together by links). It is flattened losslessly and then run through the same
    validate -> RPN -> AP -> flags -> rank pipeline as ``fmea_run``, so the output shape
    matches — plus the action-tracking columns when any link carries an action. Raises a
    structured tool error if the model fails its own validation (duplicate IDs, unknown
    link references) or the flattened rows fail input validation.
    """
    parsed = _call(RelationalFMEA.model_validate, model)
    scored = _call(run_pipeline_relational, parsed)
    return _scored_records(scored)


@app.tool
def fmea_list_scales() -> list[dict[str, str]]:
    """List the built-in FMEA rating-scale options an agent can select.

    Rating scales are reference text only: they document what a score *means*, and never
    change the RPN/AP that ``fmea_score``/``fmea_run`` return. Names come from the bundled
    scale files themselves rather than being restated here, so the menu can't drift from
    what ``fmea_get_scale`` actually returns.
    """
    return [
        {"id": "2019", "name": load_default_scales().name},
        {"id": "fmea4", "name": load_legacy_fmea4_scales().name},
    ]


@app.tool
def fmea_get_scale(scale_id: str = "2019", custom_json: str | None = None) -> dict[str, Any]:
    """Return one S/O/D rating scale's full severity/occurrence/detection text.

    scale_id: "2019" (AIAG & VDA 2019 PFMEA default), "fmea4" (AIAG FMEA-4 legacy), or
    "custom" (requires custom_json: raw JSON text with severity/occurrence/detection keys,
    each mapping ratings 1-10 to a description). Raises a structured tool error for an
    unknown scale_id, a missing custom_json when scale_id="custom", or a custom scale that
    fails validation.
    """
    if scale_id == "2019":
        scale = load_default_scales()
    elif scale_id == "fmea4":
        scale = load_legacy_fmea4_scales()
    elif scale_id == "custom":
        if custom_json is None:
            raise ToolError("scale_id='custom' requires custom_json.")
        scale = _call(load_scales_from_json, custom_json)
    else:
        raise ToolError(f"Unknown scale_id {scale_id!r}. Use '2019', 'fmea4', or 'custom'.")
    return scale.model_dump()


def main() -> None:
    """Console-script entry point (``quality-mcp``).

    stdio is FastMCP's default transport — what Claude Desktop / Cursor / Claude Code
    launch (#260 scope: stdio only, HTTP is M1-8).
    """
    app.run()


# pragma: no cover — the module-as-script path can't be exercised from a test without
# starting the blocking stdio loop; `main()` itself is covered directly.
if __name__ == "__main__":  # pragma: no cover
    main()
