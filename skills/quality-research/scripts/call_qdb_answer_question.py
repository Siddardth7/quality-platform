"""Call the quality-platform `qdb_answer_question` MCP tool over HTTP and print the JSON result.

Reads `QDB_MCP_URL` (e.g. "http://<host>:<port>/mcp") and `QDB_MCP_TOKEN` (the bearer secret)
from the environment — the two client-side env vars locked for this skill (#289) and expected
to be reused by M6's remote-host wiring. They are deliberately distinct from the server-side
`MCP_AUTH_TOKEN` that `apps/mcp/mcp_app/transport.py` checks incoming tokens against: one is
what the server verifies, these two are what this client sends.

It imports `fastmcp` plus stdlib only — no engine package, no arithmetic, no retrieval logic.
The endpoint decides refuse-vs-answer; this script only calls it and prints what came back.
Both env lookups are `os.environ[...]`, not `.get` — an unset variable raises `KeyError`
immediately rather than sending an anonymous request, the same fail-loud posture as
`transport.py`'s own env handling. SKILL.md's step 2c is what catches any failure this raises
and routes to the local fallback; the script itself swallows nothing.

    QDB_MCP_URL=... QDB_MCP_TOKEN=... python \\
        skills/quality-research/scripts/call_qdb_answer_question.py "why is ndc >= 5?"
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


async def call_qdb_answer_question(question: str) -> object:
    """Answer one question through the hosted MCP server over HTTP with a bearer token."""
    url = os.environ["QDB_MCP_URL"]
    token = os.environ["QDB_MCP_TOKEN"]
    transport = StreamableHttpTransport(url=url, auth=token)
    async with Client(transport) as client:
        result = await client.call_tool("qdb_answer_question", {"question": question})
    return result.data


def main() -> int:
    """Parse one positional question, call the tool, print the result as JSON."""
    if len(sys.argv) != 2:
        print("usage: call_qdb_answer_question.py QUESTION", file=sys.stderr)
        return 2
    print(json.dumps(asyncio.run(call_qdb_answer_question(sys.argv[1]))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
