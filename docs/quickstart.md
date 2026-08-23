# Quickstart

Clone first — every path below assumes a local clone, because nothing is published to a
package index yet (see the note at the bottom).

```bash
git clone https://github.com/Siddardth7/quality-platform.git
cd quality-platform
uv sync
```

## 1 · As MCP tools in your agent host (recommended)

The server is a FastMCP app. Its default transport is **stdio**, which is unauthenticated
by design: the host launches the process locally and talks to it over pipes, so there is no
port and no token.

```bash
uv run python -m mcp_app.server    # from the workspace root
```

Register it with your host — this is the Claude Desktop shape
(`~/Library/Application Support/Claude/claude_desktop_config.json`, root key `mcpServers`):

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

Cursor and Gemini CLI use the same shape in their own config files. **VS Code does not** —
its root key is `servers`, not `mcpServers`. Per-host blocks, the quirks table and an honest
record of which host has actually been *run* live in
[Hosts](hosts.md).

Then ask your agent for something and watch it call a tool:

> *"Score this failure mode: severity 8, occurrence 5, detection 6."*

The host should call `fmea_score` and report **the tool's** result —
`{"rpn": 240, "action_priority": "Medium"}` — not a number it worked out itself.
`health()` → `{"status": "ok"}` and `version()` → `{"version": "0.16.0"}` are the cheaper
liveness checks.

!!! warning "Don't smoke-test with `qdb_answer_question`"
    The private-corpus RAG tool needs a locally built corpus index and a configured
    `QDB_GENERATOR_IMPORT_PATH` generator. A fresh clone has neither, so it is not a fair
    first call. Use `health`, `version` or `fmea_score`.

### HTTP transport (opt-in, always authenticated)

`MCP_TRANSPORT=http` serves Streamable HTTP and **fails closed** — with no credentials
configured the server refuses to start rather than binding an open port.

```bash
MCP_TRANSPORT=http MCP_AUTH_TOKEN="$(openssl rand -hex 32)" uv run python -m mcp_app.server
```

| Variable | Meaning |
|---|---|
| `MCP_TRANSPORT` | `stdio` (default) or `http` |
| `MCP_HOST` | bind address, default `127.0.0.1` |
| `MCP_PORT` | port, default `8000` |
| `MCP_AUTH_MODE` | `bearer` (default) or `oauth` |
| `MCP_AUTH_TOKEN` | shared secret, required in `bearer` mode |
| `MCP_OAUTH_AUTHKIT_DOMAIN` | WorkOS AuthKit domain, required in `oauth` mode |
| `MCP_OAUTH_BASE_URL` | this server's public base URL, required in `oauth` mode |

OAuth mode is resource-server support only, and no public endpoint is provisioned — see
[Hosts](hosts.md) for what that does and does not unblock.

## 2 · As a local Streamlit app

```bash
uv run streamlit run app.py          # the whole platform, one URL
uv run streamlit run apps/spc/app.py # a single app standalone
```

## 3 · The worked loop

Run the AIAG loop end to end over a committed project directory:

```bash
uv run python -c "from mcp_app.server import run_project_loop; \
    run_project_loop('examples/secom-quality-loop')"
```

What it reads, what it writes and what it deliberately refuses to claim is in
[the worked example](demo.md).

!!! note "`uvx quality-mcp` does not work yet"
    The distribution is named and the registry manifests exist, but **nothing has been
    uploaded to any package index**
    ([#292](https://github.com/Siddardth7/quality-platform/issues/292) is open). The
    console-script form that works today is `cd apps/mcp && uvx --from . quality-mcp`, from
    a local clone.
