"""Call the quality-platform `msa_gage_rr` MCP tool over stdio and print the JSON result.

Runnable form of the `msa` skill's Gage R&R path (#273), for when a shell call is cheaper than
a tool call. It starts the MCP server as a subprocess, calls one tool, and prints what came
back. It imports `fastmcp` plus stdlib only — no engine package, no arithmetic. If you need a
number this script does not already receive, the fix is a tool call, not a formula.

Pass the study as one JSON array in long/tidy form (one object per measurement, keys `part`,
`appraiser`, `trial`, `measurement`), then the method, then the tolerance — the literal `none`
for a study with no tolerance, in which case the four tolerance-basis keys come back null.

    python skills/msa/scripts/call_msa_gage_rr.py \\
        '[{"part":1,"appraiser":"A","trial":1,"measurement":10.0}]' average_and_range 2.0
    python skills/msa/scripts/call_msa_gage_rr.py "$(cat study.json)" anova none
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


async def call_msa_gage_rr(
    study: list[dict[str, Any]], method: str, tolerance: float | None
) -> object:
    """Run one Gage R&R study through the MCP server launched over stdio."""
    transport = StdioTransport(command=sys.executable, args=["-m", "mcp_app.server"])
    async with Client(transport) as client:
        result = await client.call_tool(
            "msa_gage_rr",
            {"study": study, "method": method, "tolerance": tolerance},
        )
    return result.data


def parse_tolerance(argument: str) -> float | None:
    """Parse the tolerance, treating the literal `none` as a study with no tolerance."""
    return None if argument.lower() == "none" else float(argument)


def main() -> int:
    """Parse the study JSON, the method and the tolerance, call the tool, print the result."""
    if len(sys.argv) != 4:
        print("usage: call_msa_gage_rr.py STUDY_JSON METHOD TOLERANCE", file=sys.stderr)
        return 2
    study = json.loads(sys.argv[1])
    tolerance = parse_tolerance(sys.argv[3])
    print(json.dumps(asyncio.run(call_msa_gage_rr(study, sys.argv[2], tolerance))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
