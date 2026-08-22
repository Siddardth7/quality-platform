# Skill host-compatibility matrix (M2-6, #275)

"Works everywhere" is a claim until proven. This file records, per shipped skill and per
CLI host, that the skill **installs**, **activates**, and **drives a real MCP tool call** —
with linked evidence, not assertions. Web hosts (Claude.ai / ChatGPT) are out of scope here;
they consume the MCP server directly and are verified in M6.

## Install path

```bash
npx skills add Siddardth7/quality-platform
```

Resolves the repo's root `skills/` directory and offers each subfolder with a valid
`SKILL.md` (see [`CONVENTIONS.md`](CONVENTIONS.md) §5). There is no registry or manifest.

> **Quirk that bites first:** `npx skills add <repo>` pulls the repo's **default branch**.
> These skills land on `test` first and reach the default branch only after promotion, so a
> host run done before promotion must install from the `test` branch or a local checkout
> instead. Not a parity assumption — the actual resolution behaviour.
>
> **Still true as of #293 (M6-2):** `quality-research` (M5-3) is on `test`/`dev` only, so
> until the next `dev -> main` promotion lands it on the default branch, a bare
> `npx skills add Siddardth7/quality-platform` installs only the skills present on `main`.
> Install from the `#test` ref — `npx skills add Siddardth7/quality-platform#test` — to get
> all of them (subject to the per-host branch-ref quirks below).

## The matrix

Skills are the **shipped** skills. `example-skill/` is the authoring template, not a
shipped skill, so it is not a row. Cells: `PASS ✓` (evidence linked) · `PENDING` (needs a
host run) · `N/A`.

`PENDING` means **not yet run**, not failed — the `project-loop` and `quality-research` rows
below carry no live evidence because their multi-host smoke test is a tracked follow-up
(M6-2, #293), run the same way M2-6 produced the four evidenced rows.

| Skill | Real MCP tool exercised | Claude Code | Codex CLI | Cursor | Gemini CLI |
|---|---|---|---|---|---|
| `control-plan` | `controlplan_build` | **PASS ✓** [evidence](compat-evidence/claude-code-column.txt) | **PASS ✓** [evidence](compat-evidence/codex-cli-column.txt) | **PASS ✓** [evidence](compat-evidence/cursor-column.txt) | **PASS ✓** [evidence](compat-evidence/gemini-cli-column.txt) |
| `fmea` | `fmea_score` | **PASS ✓** [evidence](compat-evidence/claude-code-column.txt) | **PASS ✓** [evidence](compat-evidence/codex-cli-column.txt) | **PASS ✓** [evidence](compat-evidence/cursor-column.txt) | **PASS ✓** [evidence](compat-evidence/gemini-cli-column.txt) |
| `spc` | spc capability | **PASS ✓** [evidence](compat-evidence/claude-code-column.txt) | **PASS ✓** [evidence](compat-evidence/codex-cli-column.txt) | **PASS ✓** [evidence](compat-evidence/cursor-column.txt) | **PASS ✓** [evidence](compat-evidence/gemini-cli-column.txt) |
| `msa` | `msa_gage_rr` | **PASS ✓** [evidence](compat-evidence/claude-code-column.txt) | **PASS ✓** [evidence](compat-evidence/codex-cli-column.txt) | **PASS ✓** [evidence](compat-evidence/cursor-column.txt) | **PASS ✓** [evidence](compat-evidence/gemini-cli-column.txt) |
| `project-loop` | `run_project_loop` | PENDING | PENDING | PENDING | PENDING |
| `quality-research` | `qdb_answer_question` | PENDING | PENDING | PENDING | PENDING |
| `example-skill` | — (template) | N/A | N/A | N/A | N/A |

### What `PASS ✓` means — and does not (all four hosts)

Every `PASS ✓` cell is backed by a **real MCP tool call**, evidence linked per column: the skill's own
shipped `scripts/*.py` launches the `quality-platform` FastMCP server over stdio
(`python -m mcp_app.server`) and calls the tool. That is genuine MCP-protocol traffic to the
real server returning the real result (control-plan's row is byte-identical to the SKILL.md
worked example, em dash included). **All four hosts reproduced the reference values exactly**
(`rpn 240` · `cpk 2.1150000000000024` · `ppk 2.8284271247461983` · `verdict Reject` · `ndc 13`
· `grr 0.11126574364256647` · `"Bracket weld — Incomplete weld"`), captured 2026-08-17 against
an isolated clone of `test` at commit `9939575`.

`PASS ✓` is scoped to **(a) the real MCP tool call**. It does **not** assert **(b) host-native
auto-discovery/activation of an `npx`-installed `SKILL.md`** — that dimension is real but
**mixed across hosts**, and is recorded honestly in the quirks table below rather than folded
into the cell:

- **Claude Code** — tool call evidenced; clean-room npx activation not separately captured.
- **Gemini CLI** (Antigravity) — `#test` branch-ref install works; **1/4 skills** (msa)
  followed `SKILL.md` natively; the rest free-formed (native tool invocation needs the stdio
  server registered in `mcp_config.json`).
- **Codex CLI** — local-path install works; **3/4 skills** followed `SKILL.md` (one used bare
  `python` instead of the prescribed `uv run` and failed the FastMCP import).
- **Cursor** — local-path + `--full-depth` install works (GitHub one-liner broken, see quirks);
  native activation did **not** fire in-session (skills added mid-session don't appear in
  `available_skills` until a fresh session).

So: the **cross-host real-tool-call layer of M2-6 is complete and evidenced**; **host-native
activation remains a partial, per-host follow-up** (register each host's MCP server + confirm
in a fresh session), tracked in the quirks table.

## Per-host runbook (how to turn a PENDING cell green)

For host **H** and skill **S**:

1. **Install** — `npx skills add Siddardth7/quality-platform` (or point H at the local
   checkout / `test` branch until the skills are promoted to the default branch).
2. **Activate** — paste a realistic prompt for S and confirm H loads S's `SKILL.md` and
   follows its steps rather than free-forming. Suggested prompts:
   - `control-plan`: "Build a control plan from this FMEA and tell me which chart to use."
   - `fmea`: "Score this failure mode: severity 8, occurrence 5, detection 6."
   - `spc`: "Run a capability study on these 10 readings against LSL 9, USL 11."
   - `msa`: "Run a Gage R&R on this study, average-and-range, tolerance 2.0."
   - `project-loop`: "Refresh the whole quality loop over this project directory."
   - `quality-research`: "Why is the ndc threshold 5?"

   `quality-research` needs `QDB_MCP_URL` and `QDB_MCP_TOKEN` set in the host's sandbox before
   `qdb_answer_question` can reach the hosted endpoint (M5-3, #289); without them the skill
   takes its documented `ASSUMPTIONS_LOG` fallback path rather than making a real tool call.
3. **Real tool call** — confirm H calls S's MCP tool (matrix column 2) and reports the
   **tool's** result, not a number it authored. Reference calls that must reproduce:
   - `fmea_score(8, 5, 6)` → `{"rpn": 240, "action_priority": "Medium"}`
   - `msa_gage_rr(3×2×2 study, average_and_range, tol 2.0)` → `verdict: "Reject"`, `ndc: 13`
     (msa/spc outputs depend on the exact measurements — use the verbatim inputs recorded in
     [`compat-evidence/claude-code-column.txt`](compat-evidence/claude-code-column.txt) to
     reproduce these specific numbers; fmea and control-plan are deterministic on the inputs shown)
4. **Evidence** — save a short transcript to `skills/compat-evidence/<host>-<skill>.txt`,
   link it in the matrix, flip the cell to `PASS ✓`.
5. **Quirks** — log any Dec-2025-spec lag (discovery mechanics, MCP-server config format,
   activation differences) in the section below. Record actual behaviour; do not assume
   parity across hosts.

The MCP tool names in this runbook match the `@app.tool` registrations in
`apps/mcp/mcp_app/server.py`; if a host reports a different signature, that is the quirk to
record.

## Per-host quirks

| Host | Observed | Status |
|---|---|---|
| Claude Code | MCP tool calls succeed over stdio via the shipped scripts; server is `quality-platform` (FastMCP 3.4.6). | real-tool-call verified; clean-room npx activation pending |
| Gemini CLI (Antigravity `agy 1.1.13`) | `npx skills add <repo>#test` works (branch ref via `#`); installs to `.agents/skills/`. Real tool calls PASS. Native activation 1/4 (msa). Non-interactive `agy -p` needs `--dangerously-skip-permissions` **before** `-p`. Native tool invocation in free-text needs the stdio server in `mcp_config.json`. | real-tool-call verified; native activation partial |
| Codex CLI (`0.147.0`) | Local-path `npx skills add /tmp/.../skills` works (→ `.agents/skills/`). Real tool calls PASS. Native activation 3/4 — one skill ran the script with bare `python` and failed the FastMCP import (SKILL.md prescribes `uv run`). Sandbox needed `UV_CACHE_DIR` override (default `~/.cache/uv` unwritable). | real-tool-call verified; native activation partial |
| Cursor (`cursor-agent 2026.08.11`) | GitHub one-liner **broken** for this repo (both default and `@test` — note `@test` fails where Gemini's `#test` works); local path + `--full-depth` required. Installs to `~/.agents/skills/`, **not** `~/.cursor/skills/`. Real tool calls PASS via the shipped scripts (~38 s stdio cold-start). No qp MCP server in Cursor config; mid-session skills absent from `available_skills` (need a fresh session). | real-tool-call verified; native activation did not fire in-session |

**Cross-host takeaways (actionable follow-ups):** (1) `npx skills add` branch-ref syntax differs
by host — `#test` (Gemini) vs `@test` (Cursor, failed); local-path install is the reliable path
until skills reach the default branch. (2) All hosts install to the agentskills.io standard
`.agents/skills/`. (3) The shipped `SKILL.md` scripts must be run with **`uv run`** — a host that
uses bare `python` fails the FastMCP import (Codex); make that instruction unmissable in each
`SKILL.md`. (4) Native tool invocation needs each host's MCP-server registration — the next layer
of M2-6 beyond this PR's real-tool-call evidence.

_The install-from-default-branch caveat above applies to every host until the skills are promoted
past `test`._
