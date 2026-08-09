# MCP Server

Foundation for the quality-platform MCP server (#260, M1-1). It is a FastMCP app
served over stdio, exposing only the two meta tools that describe the server
process itself — `health` and `version`. No engine tool lands here yet; the FMEA,
SPC, MSA, Control Plan, and SECOM tools arrive in M1-3 onward on the same `app`
object in `mcp_app/server.py`.

```bash
uv run python -m mcp_app.server    # from the workspace root
cd apps/mcp && uvx --from . quality-mcp   # via the console entry point
```

`uvx --from .` must run from `apps/mcp` — the workspace root is a coordinator
(`package = false`) and has no distribution to build.

Coverage for `mcp_app.server` is gated at 100% line+branch in CI — see the gate
table in the root `CLAUDE.md`.
