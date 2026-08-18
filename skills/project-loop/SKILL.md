---
name: project-loop
description: Run the full quality loop over a Quality Platform project directory by calling the run_project_loop MCP tool — FMEA to Control Plan to SPC config to MSA gate to SPC feedback, ending in candidate FMEA occurrence actions. Use when the user has a project folder on disk and wants the whole chain refreshed or the loop closed, not when they want a single arrow or a one-off calculation.
---

# project-loop — run the whole loop over a project directory

Refresh every derived file in a Quality Platform project folder by calling the MCP tools in
dependency order. The engine owns every value; this skill decides which tool to call and how
to report what changed. See `skills/CONVENTIONS.md` for the rules this skill is written to.

## When to use

The user points at a **project directory on disk** — one holding `project.yaml`,
`fmea/fmea.json` and friends (`docs/PROJECT_FILE_CONTRACT.md` describes the layout) — and
wants the whole chain brought up to date, or wants to know what the latest SPC results imply
for the FMEA.

Not this skill when the user wants only one leg refreshed (call that arrow's own tool: see the
table below), or wants a calculation on data they are pasting in rather than storing — that is
the `fmea`, `spc`, `msa` or `control-plan` skill.

## The one-call path

1. Connect to the quality-platform MCP server over stdio. The host normally has it configured
   already; if not, it launches as `python -m mcp_app.server` from the workspace root.
2. Call `run_project_loop(project_root)` with the absolute path to the project directory.
3. Report the four keys it returns — `control_plan`, `spc_config`, `msa_gate`, `feedback` —
   **verbatim**. Do not re-derive, round or re-rank anything in them.

## The inspectable path

If the user wants to see each stage land, call the four constituent tools in exactly this
order instead. The order is a data dependency, not a preference — each tool reads the file the
one before it wrote:

| # | Tool | Reads | Writes |
|---|---|---|---|
| 1 | `controlplan_build_from_project` | `fmea/fmea.json` | `control-plan/plan.json` |
| 2 | `spc_config_from_project` | `control-plan/plan.json` | `spc/config.json` |
| 3 | `spc_msa_gate_from_project` | `spc/config.json`, `msa/gage-rr.json` (optional) | `spc/msa-gate.json` |
| 4 | `spc_fmea_feedback_from_project` | `spc/results/*.json`, `control-plan/plan.json`, `fmea/fmea.json` | `feedback/spc-to-fmea.json`, candidate actions on `fmea/fmea.json` |

Step 3 does not have to run before step 4 — the gate and the feedback arrow never read each
other's output. It is placed there so the user knows how far the measurement system can be
trusted before reading numbers that came through it.

## What to tell the user afterwards

- **`spc/results/*.json` is an input, not an output.** No tool in this loop produces it; it
  comes from a prior SPC charting session and must already be on disk. If the project has
  none, `feedback` comes back `null` and that is a correct, complete run — say so rather than
  reporting a failure.
- **The feedback is a candidate, never an applied change.** The loop attaches an `Open` action
  proposing a new occurrence rating on the affected FMEA rows; the cause's own occurrence
  rating is left exactly as it was, for a human to decide. Present the proposal as a proposal,
  and point the user at `feedback/spc-to-fmea.json` for the chart, rules and CAPA prompt behind
  it. Never author the accepted rating yourself.
- **Read the gate next to the feedback.** A characteristic whose `spc/msa-gate.json` row says
  `block` or `warn` still produces feedback — nothing filters one on the other. Flag it when
  reporting, rather than implying the loop already accounted for it.
- **Re-running is safe.** The same inputs produce the same proposal, so a second run leaves
  `fmea/fmea.json` untouched. If the user asks whether it is safe to run again, it is.
- **A failure part-way through leaves earlier files written.** Each step overwrites only its
  own file, so fixing the named input and re-running is the right recovery — there is nothing
  to clean up first.

## Worked reference

[`examples/secom-quality-loop/README.md`](../../examples/secom-quality-loop/README.md) is a
complete project this loop runs against end to end, including which parts of it are real data
and which are illustrative fixtures.
