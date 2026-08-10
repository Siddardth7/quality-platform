# MCP Server

The quality-platform MCP server (#260, M1-1). It is a FastMCP app served over
stdio. Two meta tools describe the server process itself — `health` and
`version` — and the FMEA (#262, M1-3), SPC (#263, M1-4), MSA (#264, M1-5) and
Control Plan (#265, M1-6) engines are exposed:

- `fmea_score(severity, occurrence, detection)` — RPN + AIAG-VDA Action Priority
  for one S/O/D triple.
- `fmea_run(rows)` — the full pipeline (validate → RPN → AP → flags → rank) over
  a flat list of FMEA rows.
- `fmea_run_relational(model)` — the same pipeline over a relational FMEA model
  supplied as inline JSON.
- `fmea_list_scales()` — the built-in rating-scale options.
- `fmea_get_scale(scale_id, custom_json=None)` — a scale's full S/O/D rating text
  (2019 default, FMEA-4 legacy, or a custom JSON scale).
- the `spc_*` tools — control charts, Phase I/II, Western Electric / Nelson rules,
  capability and stability (see the tool list in `mcp_app/server.py`).
- `msa_gage_rr(study, method, tolerance=None)` — Gage R&R (Average-and-Range or
  ANOVA), both AIAG %-bases, ndc and the accept/marginal/reject verdict.
- `controlplan_build(fmea_model)` — derive a Control Plan (one row per failure
  mode, highest-risk first) from a relational FMEA.
- `controlplan_recommend_chart(data_type, subgroup_size, ...)` — the AIAG SPC
  chart-selection rule table (bounded per #196).
- `controlplan_source_index(fmea_model)` — trace every Control Plan row back to its
  source FMEA failure mode and cause.

The SECOM tools arrive in a later M1 issue on the same
`app` object in `mcp_app/server.py`.

```bash
uv run python -m mcp_app.server    # from the workspace root
cd apps/mcp && uvx --from . quality-mcp   # via the console entry point
```

`uvx --from .` must run from `apps/mcp` — the workspace root is a coordinator
(`package = false`) and has no distribution to build.

Coverage for `mcp_app.server` is gated at 100% line+branch in CI — see the gate
table in the root `CLAUDE.md`.
