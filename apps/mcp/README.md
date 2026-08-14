# MCP Server

The quality-platform MCP server (#260, M1-1). It is a FastMCP app served over
stdio. Two meta tools describe the server process itself — `health` and
`version` — the FMEA (#262, M1-3), SPC (#263, M1-4), MSA (#264, M1-5) and Control Plan (#265, M1-6) engines are exposed, and M1-7 (#266) adds the export/report tools:

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
- `spc_config_from_project(project_root)` — the Control Plan → SPC arrow (#278): read
  `<project_root>/control-plan/plan.json`, write `<project_root>/spc/config.json` (which
  characteristics SPC watches and with which chart), return the written artifact.
- `spc_fmea_feedback_from_project(project_root)` — the SPC → FMEA arrow (#279): read
  `<project_root>/spc/results/*.json` (joined to FMEA causes through
  `control-plan/plan.json`), write `<project_root>/feedback/spc-to-fmea.json` and the
  candidate `Action` on `fmea/fmea.json`; returns `null` when nothing is out of control.

**Export/report tools (#266)** — every one returns a FastMCP `File`/`Image` (no base64 hand-rolling), and every CSV/Excel path routes through the formula-injection sanitizer in `quality_core.io.export` (a cell starting with `= + - @` can never execute):

- `export_csv(table)` — any tabular result → injection-safe CSV.
- `fmea_export_excel(rows)` / `fmea_export_pdf(rows)` — FMEA report artifacts.
- `fmea_chart_pareto_png(rows)` / `fmea_chart_heatmap_png(rows)` — FMEA chart PNGs.
- `spc_export_control_chart_excel|pdf(...)`, `spc_export_capability_excel|pdf(...)` — SPC report artifacts from a chart/capability result.
- `msa_export_excel|pdf(...)`, `msa_export_study_csv(study)`, `msa_export_results_csv(results)` — Gage R&R report artifacts.

- `msa_gage_rr(study, method, tolerance=None)` — Gage R&R (Average-and-Range or ANOVA), both AIAG %-based metrics, ndc and the accept/marginal/reject verdict.
- `controlplan_build(fmea_model)` — derive a Control Plan (one row per failure mode, highest-risk first) from a relational FMEA.
- `controlplan_recommend_chart(data_type, subgroup_size, ...)` — the AIAG SPC chart-selection rule table (bounded per #196).
- `controlplan_source_index(fmea_model)` — trace every Control Plan row back to its source FMEA failure mode and cause.
- `controlplan_build_from_project(project_root)` — the project-file (#276) face of `controlplan_build`: read `<project_root>/fmea/fmea.json`, write `<project_root>/control-plan/plan.json` (overwritten in place on a re-run), return the written artifact.

The SECOM tools arrive in a later M1 issue on the same `app` object in `mcp_app/server.py`. (SPC-chart PNGs are deferred to a future issue — they need a headless image renderer beyond the existing exporters.)

```bash
uv run python -m mcp_app.server    # from the workspace root
cd apps/mcp && uvx --from . quality-mcp   # via the console entry point
```

`uvx --from .` must run from `apps/mcp` — the workspace root is a coordinator
(`package = false`) and has no distribution to build.

## Transport (#267, M1-8)

stdio is the default and is unauthenticated — a local host launching `quality-mcp`
with no environment set behaves exactly as before. `MCP_TRANSPORT=http` opts into
FastMCP's Streamable HTTP transport, which is **always** authenticated with a shared
secret bearer token:

```bash
MCP_TRANSPORT=http MCP_AUTH_TOKEN="$(openssl rand -hex 32)" uv run python -m mcp_app.server
```

| Variable | Default | Meaning |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` or `http`; any other value is a startup error |
| `MCP_HOST` | `127.0.0.1` | bind address — loopback only unless you opt into `0.0.0.0` |
| `MCP_PORT` | `8000` | bind port |
| `MCP_AUTH_TOKEN` | *(none)* | shared secret, **required** in `http` mode |

HTTP mode fails closed: with no `MCP_AUTH_TOKEN` the server refuses to start rather
than binding an open port, and there is no way to serve HTTP unauthenticated. Clients
send `Authorization: Bearer <token>`; a missing, malformed or wrong token gets a 401.
The token is compared in constant time and is never logged.

### Connecting a remote host

*Stub — full instructions land in M6, when hosting/deployment is decided.* Today the
endpoint is `http://<host>:<port>/mcp` and any MCP client that supports Streamable
HTTP with a bearer token can connect. The default loopback bind means "remote" means
"another process on this machine" until M6 adds a real deployment (TLS termination,
process supervision, secret management) — do not expose this port publicly with the
single shared token as the only control. Per-client tokens / OAuth are deferred to M6.

Coverage for `mcp_app.server` and `mcp_app.transport` is gated at 100% line+branch in
CI — see the gate table in the root `CLAUDE.md`.
