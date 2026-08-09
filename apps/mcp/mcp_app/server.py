"""The quality-platform MCP server: FastMCP app, stdio transport, meta tools only.

This module is the M1-1 foundation (#260) — no engine tool lands here. M1-3 onward will
add domain tools (FMEA, SPC, MSA, Control Plan, SECOM) to this same ``app`` object.

Tool namespace convention (fixed now so later tools don't re-litigate it, #260 decision 2):
meta tools that describe the server process itself stay flat and unprefixed (``health``,
``version``); every future engine tool gets a ``<domain>_`` prefix (e.g.
``fmea_action_priority``, ``spc_capability``, ``msa_gage_rr``) so this server's tool list
stays legible when a host also has other MCP servers connected.
"""

from __future__ import annotations

from fastmcp import FastMCP

from mcp_app import __version__

app = FastMCP("quality-platform")


@app.tool
def health() -> dict[str, str]:
    """Liveness probe: proves the request loop is up end-to-end."""
    return {"status": "ok"}


@app.tool
def version() -> dict[str, str]:
    """Report the running quality-platform MCP server build."""
    return {"version": __version__}


def main() -> None:
    """Console-script entry point (``quality-mcp``).

    stdio is FastMCP's default transport — what Claude Desktop / Cursor / Claude Code
    launch (#260 scope: stdio only, HTTP is M1-8).
    """
    app.run()


# pragma: no cover — the module-as-script path can't be exercised from a test without
# starting the blocking stdio loop; `main()` itself is covered directly.
if __name__ == "__main__":  # pragma: no cover
    main()
