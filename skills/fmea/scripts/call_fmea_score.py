"""Call the quality-platform `fmea_score` MCP tool over stdio and print the JSON result.

Runnable form of the `fmea` skill's single-triple path (#271), for when a shell call is
cheaper than a tool call. It starts the MCP server as a subprocess, calls one tool, and
prints what came back. It imports `fastmcp` plus stdlib only — no engine package, no
arithmetic. If you need a number this script does not already receive, the fix is a tool
call, not a formula.

    python skills/fmea/scripts/call_fmea_score.py 9 8 5
"""

from __future__ import annotations

import asyncio
import json
import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


async def call_fmea_score(severity: int, occurrence: int, detection: int) -> object:
    """Score one S/O/D triple through the MCP server launched over stdio."""
    transport = StdioTransport(command=sys.executable, args=["-m", "mcp_app.server"])
    async with Client(transport) as client:
        result = await client.call_tool(
            "fmea_score",
            {"severity": severity, "occurrence": occurrence, "detection": detection},
        )
    return result.data


def main() -> int:
    """Parse three positional ratings, call the tool, print the result as JSON."""
    if len(sys.argv) != 4:
        print("usage: call_fmea_score.py SEVERITY OCCURRENCE DETECTION", file=sys.stderr)
        return 2
    severity, occurrence, detection = (int(argument) for argument in sys.argv[1:])
    print(json.dumps(asyncio.run(call_fmea_score(severity, occurrence, detection))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
