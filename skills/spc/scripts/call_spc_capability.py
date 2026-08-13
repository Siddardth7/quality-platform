"""Call the quality-platform `spc_capability` MCP tool over stdio and print the JSON result.

Runnable form of the `spc` skill's capability path (#272), for when a shell call is cheaper
than a tool call. It starts the MCP server as a subprocess, calls one tool, and prints what
came back. It imports `fastmcp` plus stdlib only — no engine package, no arithmetic. If you
need a number this script does not already receive, the fix is a tool call, not a formula.

Pass the measurements as one comma-separated list, then the spec limits; either limit may be
the literal `none` for a one-sided spec. Stability is not assessed here: `violations` is not
sent, so the result's `stable` field comes back null ("not assessed").

    python skills/spc/scripts/call_spc_capability.py 10.2,10.4,10.1,10.3 9.8 10.8
    python skills/spc/scripts/call_spc_capability.py 10.2,10.4,10.1,10.3 none 10.8
"""

from __future__ import annotations

import asyncio
import json
import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


async def call_spc_capability(
    data: list[float], lsl: float | None, usl: float | None
) -> object:
    """Run one capability study through the MCP server launched over stdio."""
    transport = StdioTransport(command=sys.executable, args=["-m", "mcp_app.server"])
    async with Client(transport) as client:
        result = await client.call_tool(
            "spc_capability",
            {"data": data, "lsl": lsl, "usl": usl},
        )
    return result.data


def parse_limit(argument: str) -> float | None:
    """Parse a spec limit, treating the literal `none` as an absent one-sided limit."""
    return None if argument.lower() == "none" else float(argument)


def main() -> int:
    """Parse the data list and both spec limits, call the tool, print the result as JSON."""
    if len(sys.argv) != 4:
        print("usage: call_spc_capability.py V1,V2,V3 LSL USL", file=sys.stderr)
        return 2
    data = [float(value) for value in sys.argv[1].split(",")]
    lsl, usl = (parse_limit(argument) for argument in sys.argv[2:])
    print(json.dumps(asyncio.run(call_spc_capability(data, lsl, usl))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
