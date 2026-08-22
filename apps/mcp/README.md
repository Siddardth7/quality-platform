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
- `spc_msa_gate_from_project(project_root)` — the MSA → SPC gate arrow (#280): read
  `<project_root>/spc/config.json` and `msa/gage-rr.json` (optional), write
  `<project_root>/spc/msa-gate.json` — one `pass`/`warn`/`block` row per monitored
  characteristic. Always written, even with zero rows.
- `run_project_loop(project_root)` — the loop orchestrator (#281): call the four arrows
  above in dependency order (Control Plan → SPC config → MSA gate → SPC feedback) against
  one project directory and return all four results. The one cross-domain tool, hence no
  `<domain>_` prefix. It does **not** produce `spc/results/*.json` — no arrow does; that is
  a precondition read off disk. Worked example: `examples/secom-quality-loop/`.

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

**Private corpus RAG (#288, M5-2)** — one tool over M5-1's query engine:

- `qdb_answer_question(question, k=5, standard=None, source_id=None, region=None)` —
  answer a question against the private corpus: retrieve → refuse-or-generate → verify
  every cited locator → enforce the corpus ledger's quote cap. Returns exactly the
  `CandidateAnswer` fields — `item_id`, `text`, `cited_source_id`, `cited_region`,
  `cited_page`, `refused` — and nothing else: **the corpus never leaves the server**, only
  the answer and its locator do. No retrieval hit list, no raw chunk text, no prompt
  context, no vectors. A refusal comes back as `refused=true` with the fixed
  `"Not found in the corpus."` text. Needs a built index and a configured generator (see
  the env vars below); a structured tool error otherwise. The corpus, the index and the
  generator's own credentials stay server-side — see "Serving the private corpus" below.

The SECOM tools arrive in a later M1 issue on the same `app` object in `mcp_app/server.py`. (SPC-chart PNGs are deferred to a future issue — they need a headless image renderer beyond the existing exporters.)

```bash
uv run python -m mcp_app.server    # from the workspace root
cd apps/mcp && uvx --from . quality-mcp   # via the console entry point
```

`uvx --from .` must run from `apps/mcp` — the workspace root is a coordinator
(`package = false`) and has no distribution to build.

## Publishing to TestPyPI (#292, M6-1)

This app is published as the distribution **`quality-mcp`** (renamed from `mcp-app` in
#292), which is also the console-script name — that pairing is what lets a published
release be run as `uvx quality-mcp`, with no `--from`. The import package is still
`mcp_app`; nothing about `import mcp_app` changed.

`.github/workflows/publish.yml` builds all eight workspace distributions and uploads them
to TestPyPI over PyPI Trusted Publishing (OIDC — no stored token). It is
`workflow_dispatch`-only: nothing publishes on push, on merge or on a tag, and TestPyPI is
the only target offered. Real PyPI comes at v1.0.0, in its own issue.

**Nothing has been uploaded yet, and `uvx quality-mcp` has not been verified against a live
index.** Trusted Publishing is registered index-side, per project, and none of the eight
names exist on TestPyPI. Two manual steps, in order:

1. **Register a "pending" publisher for each of the eight project names** on
   <https://test.pypi.org/manage/account/publishing/> (account sidebar → *Publishing*, not
   a project page — the projects do not exist yet; a pending publisher is converted to a
   normal one on first upload). Per PyPI's
   [docs](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/), the
   GitHub Actions form takes the PyPI project name to be created, the repository owner's
   name, the repository's name, the filename of the workflow authorized to upload, and an
   optional GitHub Actions environment name. For this repo those are:

   | Field | Value |
   |---|---|
   | PyPI project name | one of `quality-core`, `quality-fmea`, `quality-spc`, `quality-msa`, `quality-controlplan`, `quality-secom`, `quality-database`, `quality-mcp` |
   | Owner | `Siddardth7` |
   | Repository name | `quality-platform` |
   | Workflow name | `publish.yml` |
   | Environment name | `testpypi` |

   A pending publisher reserves nothing until it is used — if someone else registers the
   name first, it is invalidated.

2. **Run the workflow once** (Actions → *Publish (TestPyPI)* → *Run workflow*), then verify
   the acceptance criterion from a clean environment:

   ```bash
   uvx --index https://test.pypi.org/simple/ \
       --index https://pypi.org/simple/ \
       --index-strategy unsafe-best-match \
       quality-mcp
   ```

   Both indexes are needed: TestPyPI does not mirror third-party dependencies
   (`fastmcp`, `pandas`, `scipy`, …), and `unsafe-best-match` lets one resolution span
   both indexes instead of the default first-index-wins-per-package.

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

See [`docs/HOSTS.md`](docs/HOSTS.md) for per-host copy-paste config (#295, M6-4) — stdio
blocks for Claude Desktop, Cursor, VS Code and Gemini CLI, and the HTTP shape plus its two
open blockers for Claude.ai and ChatGPT.

## Serving the private corpus (#288, M5-2)

`qdb_answer_question` is the one tool that reads private data, so it is the one tool
with deployment prerequisites. Auth is **not** separate: it is M1-8's transport bearer
token above — with `MCP_TRANSPORT=http` the shared secret gates every tool on this
server, this one included. There is no second auth scheme and no per-tool check.

```bash
# from apps/mcp, with the corpus already indexed locally
# (quality_database_app.index.run()) and a generator module of your own to point at:
uv sync --extra embed
MCP_TRANSPORT=http \
MCP_HOST=0.0.0.0 \
MCP_PORT=8000 \
MCP_AUTH_TOKEN="$(openssl rand -hex 32)" \
QUALITY_DATABASE_CORPUS_OUT=/path/to/private/.corpus_out \
QDB_GENERATOR_IMPORT_PATH="my_deploy_module:generate" \
uv run python -m mcp_app.server
```

| Variable | Default | Meaning |
|---|---|---|
| `QUALITY_DATABASE_CORPUS_OUT` | `apps/quality_database/.corpus_out` | private corpus store location (M4-5) |
| `QDB_GENERATOR_IMPORT_PATH` | *(none — required)* | `"module:function"` resolved with `importlib`; the callable is `(question, context) -> str`, answer text carrying inline `[source_id:region:page]` locators |

`uv sync --extra embed` is required at deploy time only: queries must be embedded with
the same real model that built the index. CI installs neither the extra nor a corpus,
and nothing above is touched at import time — the store, the embedding model and the
generator are each loaded once, lazily, on the first tool call.

**No LLM ships with this repo.** `QDB_GENERATOR_IMPORT_PATH` has no default and no
bundled vendor client: the operator writes a small module wrapping whichever backend
they chose and points the variable at it. Its API key is that module's business and
lives in the host's secret store, never here.

Secrets and paths are environment-only — nothing above is committed, and neither the
corpus nor the index is ever in git (`.corpus_out/` is gitignored; `tests/test_no_corpus_content.py`
is the machine check).

**Known limitation:** the generator is resolved even for a question that would be
refused, so `QDB_GENERATOR_IMPORT_PATH` must be configured to get refusals as well as
answers. Fixing that would mean changing M5-1's `Generator` seam, which #288 does not
touch.

### Hosting recommendation (on paper — nothing is provisioned)

**Fly.io, one `shared-cpu-1x` / 256–512MB machine**, bound with `MCP_HOST=0.0.0.0` and
fronted by Fly's built-in TLS.

- *Why Fly rather than a serverless platform*: FastMCP's Streamable HTTP session manager
  wants a persistent process, which Fly's always-on machine model gives directly. On a
  request-scoped serverless runtime every cold start would re-run the lazy loads —
  re-reading the whole index per invocation.
- *Rough cost*: `shared-cpu-1x`/256MB is Fly's smallest paid tier — single-digit dollars
  a month run continuously, near zero with `auto_stop_machines` (M5's traffic is a
  handful of skill-triggered queries, not sustained load). The index ships to the VM as a
  Fly Volume, never baked into an image and never committed.
- *Not decided here*: which generator backend is deployed and what its per-token API cost
  is — that is the real recurring spend, and it is the operator's call.
- *Open SME action items* (deliberately not done in #288): create the Fly app, store
  `MCP_AUTH_TOKEN` and the generator's credentials in Fly secrets (never in `fly.toml`),
  choose `auto_stop_machines` vs always-on, pick the generator vendor and a budget, and
  write the `fly.toml` itself — no deployment manifest exists in this repo yet, by design.

Coverage for `mcp_app.server` and `mcp_app.transport` is gated at 100% line+branch in
CI — see the gate table in the root `CLAUDE.md`.
