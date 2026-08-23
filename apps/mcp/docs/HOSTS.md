# MCP host-configuration matrix (M6-4, #295)

Copy-paste configuration for connecting an MCP host directly to the `quality-platform`
FastMCP server (`apps/mcp/mcp_app/server.py`), plus an honest record of which of those
configurations has actually been *run* and which has only been *written*.

**This file is the MCP-server layer.** It covers host-native MCP-server registration — the
host launches or dials this server itself and calls its tools by name. That is a different
layer from [`skills/COMPATIBILITY.md`](../../../skills/COMPATIBILITY.md) (M2-6, #275), which
proved the **skill-script** layer: a shipped `SKILL.md`'s own `scripts/*.py` spawning the
same server over stdio. M2-6 said so explicitly — "Native tool invocation needs each host's
MCP-server registration — the next layer of M2-6 beyond this PR's real-tool-call evidence"
— and this file is that next layer. The two do not overlap and neither supersedes the other;
COMPATIBILITY.md's four CLI-skill-host results stand verbatim and are not re-derived here.

## The run command

Every stdio config below invokes the same command, verbatim from
[`../README.md`](../README.md):

```bash
uv run python -m mcp_app.server    # from the workspace root
```

Two notes that decide what goes in a config block:

- **Hosts launch the server from an arbitrary working directory**, so a config block cannot
  rely on "from the workspace root". Every block below passes `uv run --directory
  /absolute/path/to/quality-platform` to pin it. Replace that path with your clone.
- **`uvx quality-mcp` is not usable yet.** The distribution is renamed but **nothing has been
  uploaded to any index** (#292, M6-1 — pending SME pending-publisher registration). Until it
  ships, the local-clone command above is the only one that works. The console-script variant
  that works today is `cd apps/mcp && uvx --from . quality-mcp`, which must run from
  `apps/mcp` because the workspace root is a coordinator with no distribution to build.

stdio is the default transport and is **unauthenticated** — no environment variables, no
token. The bearer gate (#267, M1-8) applies only to `MCP_TRANSPORT=http`.

## The matrix

Cells: `PASS ✓` (evidence linked) · `PENDING (<named blocker>)` · `N/A`. Same taxonomy as
`skills/COMPATIBILITY.md` — do not invent a third meaning for a cell.

| Host | Transport | Config verified | Worked example run | Tool exercised | Caveat |
|---|---|---|---|---|---|
| [Claude Desktop](#claude-desktop) | stdio | **PASS ✓** (shape matches documented schema) | **PENDING** (no GUI host in this environment) | — | GUI app; not launchable in a headless sandbox |
| [Cursor](#cursor-ide) | stdio | **PASS ✓** (shape matches documented schema) | **PENDING** (no GUI host in this environment) | — | M2-6 quirk: "No qp MCP server in Cursor config" — this file supplies it |
| [VS Code](#vs-code) | stdio | **PASS ✓** (shape matches documented schema) | **PENDING** (no GUI host in this environment) | — | Root key is **`servers`**, not `mcpServers` |
| [Gemini CLI](#gemini-cli) | stdio | **PASS ✓** [evidence](host-evidence/gemini-cli.txt) — host spawned the server and resolved `quality-platform/health` | **PENDING** (host permission gate auto-denies MCP calls in non-interactive print mode) | `health` enumerated, not called | The only host actually registered in this environment |
| [Claude.ai](#claudeai-connectors) | http | **PASS ✓** (shape only — URL + OAuth fields) | **PENDING** (1: hosted endpoint not provisioned · 2: OAuth-vs-bearer protocol mismatch, [#355](https://github.com/Siddardth7/quality-platform/issues/355)) | — | Two independent blockers, not one |
| [ChatGPT](#chatgpt-connectors) | http | **PASS ✓** (shape only — URL + connector fields) | **PENDING** (1: hosted endpoint not provisioned · 2: no confirmed static-bearer path, [#355](https://github.com/Siddardth7/quality-platform/issues/355)) | — | Also needs a paid plan with Developer Mode |
| Claude Code · Codex CLI · Cursor · Gemini CLI (**skill layer**) | stdio via skill scripts | — | **PASS ✓ on all four** — see [`skills/COMPATIBILITY.md`](../../../skills/COMPATIBILITY.md) | `fmea_score`, `spc` capability, `msa_gage_rr`, `controlplan_build` | Different layer; not repeated here |

### What `PASS ✓` means — and does not

Two columns, deliberately separable, exactly as `skills/COMPATIBILITY.md` separates its real
tool call from its native activation:

- **Config verified** means the block below matches the host's documented configuration
  schema and names a command and tool that really exist in this repo. For Gemini CLI it
  means more: the host actually loaded the config, spawned the server over stdio and
  enumerated its tools. For every other host it is a schema claim and nothing more.
- **Worked example run** means someone actually invoked a tool through that host and the
  server returned the value. **No row in this file claims that yet.** A config block that was
  never invoked is not a PASS, however correct it looks.

**A PASS in the "config verified" column is not permission to say the host works.** Until a
worked-example cell is green with a linked transcript, the honest statement is "the config is
written and schema-correct."

## Reference calls

Every worked example in this file uses the same reference calls as
`skills/COMPATIBILITY.md` so results are comparable across both layers. Do not invent new
ones — reproducing these byte-for-byte is the point.

| Call | Expected result |
|---|---|
| `health()` | `{"status": "ok"}` |
| `version()` | `{"version": "1.0.0"}` |
| `fmea_score(8, 5, 6)` | `{"rpn": 240, "action_priority": "Medium"}` |

`fmea_score` is deterministic on those inputs and needs no files, no corpus and no
environment — which is exactly why it, `health` and `version` are the worked-example tools.
The server exposes 49 tools in total (see [`../README.md`](../README.md)); of those,
`qdb_answer_question` is **not** a fair smoke test — it has its own deployment
prerequisites (a built local corpus index and `QDB_GENERATOR_IMPORT_PATH`) that neither CI
nor a fresh clone has.

---

## Claude Desktop

**Config file** — `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows). Root key `mcpServers`.

```json
{
  "mcpServers": {
    "quality-platform": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/absolute/path/to/quality-platform",
        "python", "-m", "mcp_app.server"
      ]
    }
  }
}
```

Restart Claude Desktop after editing — it reads the file at launch only.

**Expected result** — the server appears as `quality-platform` in the connectors/tools list,
with `health`, `version`, `fmea_score` and the rest of the 49 tools. Ask *"Score this failure
mode: severity 8, occurrence 5, detection 6"* and the host should call `fmea_score` and report
`rpn 240` / `action_priority "Medium"` as the **tool's** result, not a number it authored.

**Status: worked example PENDING** — Claude Desktop is a GUI application and cannot be
launched in this headless environment. See the [runbook](#runbook-turning-a-pending-cell-green).

## Cursor IDE

**Config file** — `.cursor/mcp.json` in the project (committable) or `~/.cursor/mcp.json`
for the user profile. Root key `mcpServers`.

```json
{
  "mcpServers": {
    "quality-platform": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/absolute/path/to/quality-platform",
        "python", "-m", "mcp_app.server"
      ]
    }
  }
}
```

This block is the direct answer to M2-6's recorded Cursor quirk, *"No qp MCP server in Cursor
config"* — that gap is why Cursor's native tool invocation never fired there.

**Expected result** — as Claude Desktop. Note M2-6's other Cursor finding: things added
mid-session do not appear until a **fresh session**, so restart Cursor before concluding the
server did not load.

**Status: worked example PENDING** — Cursor IDE is a GUI application, not launchable here.
(The separate `cursor-agent` CLI *was* exercised in M2-6, but at the skill-script layer, not
via this config — see `skills/COMPATIBILITY.md`.)

## VS Code

> **Read this before copy-pasting.** VS Code's root key is **`servers`**, **not**
> `mcpServers`. Three of the four stdio hosts on this page use `mcpServers`; VS Code does
> not. Pasting a `mcpServers` block into `.vscode/mcp.json` silently registers nothing, and
> it is the single most likely mistake on this page.

**Config file** — `.vscode/mcp.json` in the workspace (committable) or the user profile.
Root key `servers`.

```json
{
  "servers": {
    "quality-platform": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/absolute/path/to/quality-platform",
        "python", "-m", "mcp_app.server"
      ]
    }
  }
}
```

For the remote (HTTP) transport VS Code takes a different entry shape —
`{"type": "http", "url": "...", "headers": {...}}` — but see
[Remote / HTTP hosts](#remote--http-hosts) before writing one: there is no endpoint to point
it at.

**Expected result** — the server is listed in the MCP view and its tools become available to
agent mode; the same `fmea_score(8, 5, 6)` → `rpn 240` check applies.

**Status: worked example PENDING** — VS Code is a GUI application, not launchable here.

## Gemini CLI

**Config file** — `~/.gemini/settings.json` (user) or `.gemini/settings.json` (project).
Root key `mcpServers`.

```json
{
  "mcpServers": {
    "quality-platform": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/absolute/path/to/quality-platform",
        "python", "-m", "mcp_app.server"
      ]
    }
  }
}
```

The Antigravity build of the CLI (`agy`, the one M2-6 used) writes the same registration from
a subcommand instead of hand-editing the file:

```bash
agy mcp add quality-platform uv run \
    --directory /absolute/path/to/quality-platform \
    python -m mcp_app.server
agy mcp list        # confirm: quality-platform  stdio  enabled
agy mcp remove quality-platform   # to undo
```

**What was actually verified here** ([evidence](host-evidence/gemini-cli.txt), `agy` 1.1.18,
2026-08-22): the registration was made, `agy mcp list` showed it enabled, and a prompt asking
for `health` / `version` / `fmea_score` drove the host far enough to resolve the
fully-qualified tool name `quality-platform/health`. **A host cannot name a tool it never
enumerated** — so the server was spawned, the MCP handshake completed and `tools/list`
returned the real tool set. The config block above is correct and working.

The call itself then failed on the **host's own permission gate**:

```
Error: permission check failed for mcp "quality-platform/health":
user denied permission for mcp(quality-platform/health)
```

Non-interactive print mode has no prompt to answer, so the default is deny, and the
documented bypass flag is not available in this agent sandbox.

**Status: config verified PASS ✓ · worked example PENDING** — tool discovery succeeded,
`tools/call` never ran. Flipping it green needs one interactive session; see the runbook.

## Remote / HTTP hosts

Both web hosts below consume FastMCP's Streamable HTTP transport at `https://<host>/mcp` and
neither launches a local process. The server side is real and works
([`../README.md`](../README.md) §Transport):

```bash
MCP_TRANSPORT=http MCP_AUTH_TOKEN="$(openssl rand -hex 32)" uv run python -m mcp_app.server
```

HTTP mode is **always** bearer-authenticated and fails closed — with no `MCP_AUTH_TOKEN` the
server refuses to start rather than binding an open port. Clients send
`Authorization: Bearer <token>`.

**Neither web host is usable today, for two independent reasons.** Both must be named; the
first alone undersells the problem:

1. **No hosted endpoint exists.** Fly.io is a recommendation on paper only — no app created,
   no deployment manifest in this repo, no `MCP_AUTH_TOKEN` issued
   ([`../README.md`](../README.md) §"Hosting recommendation (on paper — nothing is
   provisioned)", M5-2). This is an SME action item.
2. **Protocol mismatch on auth.** Even once hosted, the M1-8 transport is **shared-secret
   bearer only**. The consumer connector UIs expose **OAuth fields only** (Authorization URL,
   Token URL, Client ID, Client Secret) with no field for a static
   `Authorization: Bearer <token>` header. Hosting the server does not fix this — it is a
   protocol gap, tracked by
   [**#355** (OAuth path for web MCP hosts)](https://github.com/Siddardth7/quality-platform/issues/355).
   No OAuth shim is built here.

Do not read the sections below as "works once deployed." They document the config *shape*
so the work is queued, nothing more.

### Claude.ai (connectors)

Settings → Connectors → Add custom connector → paste the server URL:

```
https://<your-host>/mcp
```

The connector UI then asks for OAuth credentials. There is no static-bearer field. (A
static-header capability does exist as an org-admin beta on the *Claude API's* MCP connector
— that is a different surface from the claude.ai consumer connector UI; do not conflate the
two.)

**Status: PENDING** — blocker 1 (endpoint not provisioned) **and** blocker 2 (OAuth-only UI
vs bearer-only server, #355).

### ChatGPT (connectors)

Settings → Connectors → Developer mode → Add custom connector → paste the same
`https://<your-host>/mcp` URL. Requires a paid plan (Plus/Pro/Business/Enterprise/Edu) with
Developer Mode enabled. Streamable HTTP and SSE are supported; auth is OAuth or none per
current docs, with no confirmed static-bearer path in the consumer UI.

**Status: PENDING** — blocker 1 (endpoint not provisioned) **and** blocker 2 (no confirmed
static-bearer path, #355). "Auth: none" is not a workaround — this server has no
unauthenticated HTTP mode by design.

---

## Runbook: turning a PENDING cell green

For host **H**, if you have H available:

1. **Configure** — paste H's block from above into H's config file, replacing
   `/absolute/path/to/quality-platform` with your clone path. Restart H; several hosts read
   the config at launch only.
2. **Confirm registration** — check that `quality-platform` appears in H's MCP/tools list. If
   it does not, the failure is config-level; do not proceed.
3. **Real tool call** — prompt H with *"Score this failure mode: severity 8, occurrence 5,
   detection 6"* and confirm H calls `fmea_score` and reports **the tool's** result:
   `{"rpn": 240, "action_priority": "Medium"}`. `health` → `{"status": "ok"}` and `version` →
   `{"version": "1.0.0"}` are the cheaper liveness checks. A host that answers with a number
   it computed itself is a **fail**, not a pass — the whole point is that the agent does not
   do the arithmetic.
4. **Evidence** — save the transcript to `apps/mcp/docs/host-evidence/<host>.txt` (mirroring
   `skills/compat-evidence/`), link it in the matrix, and flip that one cell to `PASS ✓`.
   Flip only the cell you evidenced.
5. **Quirks** — record what actually happened in the table below: config-key differences,
   restart requirements, permission prompts, cold-start times. Actual behaviour, not assumed
   parity.

For the two web hosts there is no step 1 you can perform: #355 and the hosting action item
have to land first.

## Per-host quirks

| Host | Observed | Status |
|---|---|---|
| Claude Desktop | Config read at launch only — a restart is required after editing `claude_desktop_config.json`. Not exercised: GUI app, no headless mode. | config written, not run |
| Cursor IDE | M2-6 recorded no `quality-platform` server in Cursor's MCP config, which is why native tool invocation never fired there; this file supplies the block. M2-6 also found mid-session additions absent until a fresh session. | config written, not run |
| VS Code | Root key is `servers`, not `mcpServers` — the outlier among the four stdio hosts. Remote entries use `{"type": "http", "url": ..., "headers": ...}`. | config written, not run |
| Gemini CLI (`agy` 1.1.18) | `agy mcp add/list/remove` registers natively without hand-editing `settings.json`. Registration + `tools/list` confirmed against the real server. `tools/call` blocked by the host's permission gate: non-interactive `agy -p` has no prompt, so it denies by default (M2-6 recorded the same friction — its bypass flag must come **before** `-p`). Config `command`/`args` must pin the clone with `uv run --directory`; the host's cwd is not the workspace root. | registration verified, tool call pending |
| Claude.ai | Connector UI exposes OAuth fields only — no static-bearer field. Distinct surface from the Claude API's MCP connector, which has a separate org-admin static-header beta. | blocked (#355 + no endpoint) |
| ChatGPT | Requires a paid plan with Developer Mode. Consumer connector auth is OAuth or none; no confirmed static-bearer path. | blocked (#355 + no endpoint) |

_Every stdio block on this page runs the server from a local clone. When `quality-mcp` is
actually published (#292), the `command`/`args` pair can shorten to `"command": "uvx",
"args": ["quality-mcp"]` with no clone and no `--directory` — but not before._
