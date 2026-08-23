# Two ways to use it

The same engines, the same `quality_core` ingest/export path, two front doors. Nothing is
reimplemented on either side — the UI and the MCP tools call the same functions, so they
cannot drift apart.

| | Streamlit UI | MCP server + Agent Skills |
|---|---|---|
| How you drive it | Point and click in a browser | Ask an agent in plain language |
| Where it runs | `uv run streamlit run app.py`, locally or on Streamlit Cloud | Locally over stdio, launched by your host |
| Best for | Exploring a dataset, tuning a chart, showing someone a result | Repeatable analysis inside a wider task; running the loop over a project directory |
| Surfaces | FMEA, SPC, Control Plan, Gage R&R | 49 tools, [grouped by method](tools.md) |
| Data movement | Your browser to your own process | None — stdio keeps the process and the files on your machine |

## The skill layer vs. the MCP-server layer

These are two different integration layers and they are often conflated:

- **MCP-server registration** — the host launches or dials the server itself and calls tools
  by name. Config per host is on [Hosts](hosts.md).
- **Agent Skills** — a shipped `SKILL.md` under `skills/` whose own scripts spawn the same
  server over stdio. This layer has real tool-call evidence on Claude Code, Codex CLI, Cursor
  and Gemini CLI, recorded in
  [`skills/COMPATIBILITY.md`](https://github.com/Siddardth7/quality-platform/blob/main/skills/COMPATIBILITY.md).

The engine skills are `fmea`, `spc`, `msa`, `control-plan` and `project-loop`. A sixth,
`quality-research`, is deliberately **not** an engine: it answers *"why does the standard say
X"* by calling `qdb_answer_question` over HTTP for a cited, page-located answer, falling back
to this project's public `ASSUMPTIONS_LOG.md` citations when that endpoint is unreachable.

| What you're asking | Which skill |
|---|---|
| "Score this failure mode / chart this data / run a Gage R&R" | `fmea`, `spc`, `msa`, `control-plan` |
| "Run the whole loop over this project" | `project-loop` |
| "Why is the ndc threshold 5?" | `quality-research` |
