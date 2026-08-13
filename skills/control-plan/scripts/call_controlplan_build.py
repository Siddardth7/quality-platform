"""Call the quality-platform `controlplan_build` MCP tool over stdio and print the JSON result.

Runnable form of the `control-plan` skill's build path (#274), for when a shell call is cheaper
than a tool call. It starts the MCP server as a subprocess, calls one tool, and prints what came
back. It imports `fastmcp` plus stdlib only — no engine package, no arithmetic. If you need a
number this script does not already receive, the fix is a tool call, not a formula.

Pass the relational FMEA as one JSON object — the same `RelationalFMEA` shape
`fmea_run_relational` takes (see `skills/fmea/references/mcp-tool-contract.md`). Every returned
row's `sample_size`, `frequency` and `reaction_plan` are connector defaults whenever
`sample_plan_is_placeholder` is true, and `recommended_chart` is always null: use
`controlplan_recommend_chart` once a characteristic has a data type and a subgroup size.

    python skills/control-plan/scripts/call_controlplan_build.py "$(cat fmea_model.json)"
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


async def call_controlplan_build(fmea_model: dict[str, Any]) -> object:
    """Derive one Control Plan through the MCP server launched over stdio."""
    transport = StdioTransport(command=sys.executable, args=["-m", "mcp_app.server"])
    async with Client(transport) as client:
        result = await client.call_tool("controlplan_build", {"fmea_model": fmea_model})
    return result.data


def main() -> int:
    """Parse the relational FMEA JSON, call the tool, print the returned rows."""
    if len(sys.argv) != 2:
        print("usage: call_controlplan_build.py FMEA_MODEL_JSON", file=sys.stderr)
        return 2
    fmea_model = json.loads(sys.argv[1])
    print(json.dumps(asyncio.run(call_controlplan_build(fmea_model))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
