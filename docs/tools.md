# MCP tool catalog

The server exposes **49 tools** in total, grouped below by method. Signatures and parameter
detail live in
[`apps/mcp/README.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/mcp/README.md)
and in the source,
[`apps/mcp/mcp_app/server.py`](https://github.com/Siddardth7/quality-platform/blob/main/apps/mcp/mcp_app/server.py).

## Meta (2)

| Tool | What it does |
|---|---|
| `health` | Server liveness — `{"status": "ok"}`. |
| `version` | The workspace version the server is running. |

## FMEA (5)

| Tool | What it does |
|---|---|
| `fmea_score` | RPN + AIAG-VDA Action Priority for one S/O/D triple. |
| `fmea_run` | The full pipeline (validate → RPN → AP → flags → rank) over a flat list of FMEA rows. |
| `fmea_run_relational` | The same pipeline over a relational FMEA model supplied as inline JSON. |
| `fmea_list_scales` | The built-in rating-scale options. |
| `fmea_get_scale` | One scale's full S/O/D rating text (2019 default, FMEA-4 legacy, or custom JSON). |

## SPC (19)

| Group | Tools |
|---|---|
| Variables charts | `spc_xbar_r`, `spc_xbar_s`, `spc_imr` |
| Attributes charts | `spc_p`, `spc_c`, `spc_u` |
| Time-weighted charts | `spc_ewma`, `spc_cusum` |
| Phase I — freeze limits | `spc_freeze_xbar_r`, `spc_freeze_xbar_s`, `spc_freeze_imr` |
| Phase II — apply frozen limits | `spc_apply_xbar_r`, `spc_apply_xbar_s`, `spc_apply_imr` |
| Rule detection | `spc_detect_we_violations` (Western Electric), `spc_detect_nelson_violations` |
| Capability & diagnostics | `spc_capability` (behind the stability gate), `spc_normality_test`, `spc_assess_stability` |

## Project-file arrows and the loop (4)

These read and write a **project directory on disk**. See [The loop](loop.md).

| Tool | What it does |
|---|---|
| `spc_config_from_project` | Control Plan → SPC: read `control-plan/plan.json`, write `spc/config.json`. |
| `spc_msa_gate_from_project` | MSA → SPC gate: read `spc/config.json` + optional `msa/gage-rr.json`, write `spc/msa-gate.json` (one `pass`/`warn`/`block` row per characteristic). |
| `spc_fmea_feedback_from_project` | SPC → FMEA: read `spc/results/*.json`, write `feedback/spc-to-fmea.json` and attach a **candidate** `Action` on `fmea/fmea.json`. Returns `null` when nothing is out of control. |
| `run_project_loop` | Calls the four arrows in dependency order over one project directory and returns all four results. It does **not** produce `spc/results/*.json` — that is a precondition read off disk. |

The fourth arrow in that order is `controlplan_build_from_project`, listed under Control Plan
below; it runs first.

## Export / report (13)

Every one returns a FastMCP `File`/`Image`, and every CSV/Excel path routes through the
formula-injection sanitizer in `quality_core.io.export` — a cell starting with `= + - @` can
never execute.

| Group | Tools |
|---|---|
| Generic | `export_csv` |
| FMEA | `fmea_export_excel`, `fmea_export_pdf`, `fmea_chart_pareto_png`, `fmea_chart_heatmap_png` |
| SPC | `spc_export_control_chart_excel`, `spc_export_control_chart_pdf`, `spc_export_capability_excel`, `spc_export_capability_pdf` |
| MSA | `msa_export_excel`, `msa_export_pdf`, `msa_export_study_csv`, `msa_export_results_csv` |

## Control Plan (4)

| Tool | What it does |
|---|---|
| `controlplan_build` | Derive a Control Plan (one row per failure mode, highest risk first) from a relational FMEA. |
| `controlplan_recommend_chart` | The AIAG SPC chart-selection rule table. |
| `controlplan_source_index` | Trace every Control Plan row back to its source FMEA failure mode and cause. |
| `controlplan_build_from_project` | The project-file face of `controlplan_build`: read `fmea/fmea.json`, write `control-plan/plan.json`. |

## MSA (1)

| Tool | What it does |
|---|---|
| `msa_gage_rr` | Gage R&R (Average-and-Range or ANOVA), the AIAG %-based metrics, `ndc`, and the accept/marginal/reject verdict. |

## Private-corpus RAG (1)

| Tool | What it does |
|---|---|
| `qdb_answer_question` | Answer a standards question against the private corpus: retrieve → refuse-or-generate → verify every cited locator → enforce the quote cap. The corpus never leaves the server — only the answer and its locator do. |

!!! warning "Not a smoke test"
    `qdb_answer_question` needs a built local corpus index and a configured
    `QDB_GENERATOR_IMPORT_PATH`. Neither CI nor a fresh clone has them, so it is not a fair
    first call — use `health`, `version` or `fmea_score(8, 5, 6)`.

2 + 5 + 19 + 4 + 13 + 4 + 1 + 1 = **49**.
