# MCP Server

The quality-platform MCP server (#260, M1-1). It is a FastMCP app served over
stdio. Two meta tools describe the server process itself — `health` and
`version` — and the FMEA engine is exposed (#262, M1-3):

- `fmea_score(severity, occurrence, detection)` — RPN + AIAG-VDA Action Priority
  for one S/O/D triple.
- `fmea_run(rows)` — the full pipeline (validate → RPN → AP → flags → rank) over
  a flat list of FMEA rows.
- `fmea_run_relational(model)` — the same pipeline over a relational FMEA model
  supplied as inline JSON.
- `fmea_list_scales()` — the built-in rating-scale options.
- `fmea_get_scale(scale_id, custom_json=None)` — a scale's full S/O/D rating text
  (2019 default, FMEA-4 legacy, or a custom JSON scale).

The SPC, MSA, Control Plan, and SECOM tools arrive in later M1 issues on the same
`app` object in `mcp_app/server.py`.

```bash
uv run python -m mcp_app.server    # from the workspace root
cd apps/mcp && uvx --from . quality-mcp   # via the console entry point
```

`uvx --from .` must run from `apps/mcp` — the workspace root is a coordinator
(`package = false`) and has no distribution to build.

Coverage for `mcp_app.server` is gated at 100% line+branch in CI — see the gate
table in the root `CLAUDE.md`.
