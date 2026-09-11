# Hosts

Copy-paste configuration for every supported host lives in one file, and this page does not
fork it:

**→ [`apps/mcp/docs/HOSTS.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/mcp/docs/HOSTS.md)**

That file holds the per-host config blocks, a runbook for turning a `PENDING` cell green, and
a per-host quirks table. It is the single source of truth for those snippets — copying them
here would let the two versions drift.

Every stdio block invokes the same command, verbatim:

```bash
uv run python -m mcp_app.server    # from the workspace root
```

Hosts launch the server from an arbitrary working directory, so each config block pins the
clone with `uv run --directory /absolute/path/to/quality-platform`.

!!! warning "VS Code's root key is `servers`, not `mcpServers`"
    Three of the four stdio hosts use `mcpServers`; VS Code does not. Pasting an
    `mcpServers` block into `.vscode/mcp.json` silently registers nothing — HOSTS.md calls
    this "the single most likely mistake on this page."

## Status at a glance

Two columns, deliberately separable. **Config verified** means the block matches the host's
documented schema and names a command and tool that really exist. **Worked example run**
means somebody actually invoked a tool through that host and the server returned the value.

| Host | Transport | Config verified | Worked example run |
|---|---|---|---|
| Claude Desktop | stdio | PASS ✓ (shape) | PENDING — GUI app, not launchable headless |
| Cursor | stdio | PASS ✓ (shape) | PENDING — GUI app, not launchable headless |
| VS Code | stdio | PASS ✓ (shape) | PENDING — GUI app, not launchable headless |
| Gemini CLI | stdio | **PASS ✓** — the host spawned the server and enumerated its tools | PENDING — the host's non-interactive permission gate auto-denied the call |
| Claude.ai | http | PASS ✓ (shape only) | PENDING — no hosted endpoint, plus an OAuth-vs-bearer protocol gap ([#355](https://github.com/Siddardth7/quality-platform/issues/355)) |
| ChatGPT | http | PASS ✓ (shape only) | PENDING — same two blockers, plus a paid plan with Developer Mode |
| Claude Code · Codex CLI · Cursor · Gemini CLI (**skill layer**) | stdio via skill scripts | — | **PASS ✓ on all four** — [`skills/COMPATIBILITY.md`](https://github.com/Siddardth7/quality-platform/blob/main/skills/COMPATIBILITY.md) |

A `PASS ✓` in the config column is **not** permission to say the host works. Until a
worked-example cell is green with a linked transcript, the honest statement is "the config is
written and schema-correct."

The last row is the **skill-script** layer, not native MCP-server registration. The two do
not overlap and neither supersedes the other.

## Reference calls

The same calls are used on both layers so results are comparable:

| Call | Expected result |
|---|---|
| `health()` | `{"status": "ok"}` |
| `version()` | `{"version": "1.0.0"}` |
| `fmea_score(8, 5, 6)` | `{"rpn": 240, "action_priority": "Medium"}` |

A host that answers with a number it computed itself is a **fail**, not a pass — the point is
that the agent does not do the arithmetic.

## Remote / HTTP hosts

Both web hosts consume Streamable HTTP at `https://<host>/mcp`. The server side is real, but
**neither web host is usable today, for two independent reasons**:

1. **No hosted endpoint exists.** Fly.io is a recommendation on paper only — no app, no
   deployment manifest, no token issued.
2. **Protocol mismatch on auth.** The consumer connector UIs expose OAuth fields only. The
   opt-in `MCP_AUTH_MODE=oauth` mode (WorkOS AuthKit) adds resource-server support, but a
   live handshake still needs the provisioned endpoint and a configured WorkOS account
   ([#355](https://github.com/Siddardth7/quality-platform/issues/355)).

## Registry listings

`apps/mcp/server.json` (official MCP registry), `apps/mcp/smithery.yaml` and root
`glama.json` exist as manifests. **None of them is live-published**, and nothing is uploaded
to any package index ([#292](https://github.com/Siddardth7/quality-platform/issues/292) is
open). Registry presence is not installability — use the local clone.
