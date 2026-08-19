"""MCP server application package.

``__version__`` is the single source of truth for the mcp-app version, reported by the
``version`` tool (mcp_app/server.py) so a host querying the server always sees the shipped
build, not a hardcoded string that can drift. Keep this in sync with
``apps/mcp/pyproject.toml`` at release; ``tests/test_version.py`` guards against drift.
"""

__version__ = "0.15.0"
