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

## The matrix

Skills are the four **shipped** skills. `example-skill/` is the authoring template, not a
shipped skill, so it is not a row. Cells: `PASS ✓` (evidence linked) · `PENDING` (needs a
host run) · `N/A`.

| Skill | Real MCP tool exercised | Claude Code | Codex CLI | Cursor | Gemini CLI |
|---|---|---|---|---|---|
| `control-plan` | `controlplan_build` | **PASS ✓** [evidence](compat-evidence/claude-code-column.txt) | PENDING | PENDING | PENDING |
| `fmea` | `fmea_score` | **PASS ✓** [evidence](compat-evidence/claude-code-column.txt) | PENDING | PENDING | PENDING |
| `spc` | spc capability | **PASS ✓** [evidence](compat-evidence/claude-code-column.txt) | PENDING | PENDING | PENDING |
| `msa` | `msa_gage_rr` | **PASS ✓** [evidence](compat-evidence/claude-code-column.txt) | PENDING | PENDING | PENDING |
| `example-skill` | — (template) | N/A | N/A | N/A | N/A |

### What the Claude Code `PASS ✓` means — and does not

Each Claude Code cell is backed by a **real MCP tool call** in
[`compat-evidence/claude-code-column.txt`](compat-evidence/claude-code-column.txt): the
skill's own shipped `scripts/*.py` launches the `quality-platform` FastMCP server over stdio
(`python -m mcp_app.server`) and calls the tool. That is genuine MCP-protocol traffic to the
real server returning the real result (control-plan's row is byte-identical to the SKILL.md
worked example, em dash included).

It does **not** additionally assert host-native auto-discovery of an `npx`-installed
`SKILL.md` inside a fresh Claude Code session — that was not separately captured in the build
environment. So: **(a) real MCP tool call → PASS ✓ (evidenced); (b) npx-install +
host-native activation → still worth a clean-room confirmation** when convenient. The other
three hosts are `PENDING` end-to-end.

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
| Codex CLI | — | pending run |
| Cursor | — | pending run |
| Gemini CLI | — | pending run |

_Fill rows as hosts are exercised. The install-from-default-branch caveat above applies to
every host until the skills are promoted past `test`._
