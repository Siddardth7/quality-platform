"""The MCP server scaffold (#260): meta tool bodies, registration, and the entry point.

``@app.tool`` returns the original plain function, so ``health`` / ``version`` are called
directly here — no fake MCP client needed. ``main()`` is exercised with ``app.run``
patched out: the real call blocks forever serving the stdio protocol loop.
"""

import asyncio

import pytest
from mcp_app import __version__
from mcp_app.server import app, health, main, version


def test_health_reports_ok():
    assert health() == {"status": "ok"}


def test_version_reports_package_version():
    assert version() == {"version": __version__}


def test_exactly_the_two_meta_tools_are_registered():
    # Proves the decorator registered both tools on the FastMCP app object, and that
    # nothing else crept in — a stray tool would otherwise go unnoticed until a later
    # M1 issue. `list_tools` is async in fastmcp 3.4.6, hence asyncio.run.
    tools = asyncio.run(app.list_tools())
    assert {tool.name for tool in tools} == {"health", "version"}


def test_main_runs_the_server(monkeypatch: pytest.MonkeyPatch):
    calls: list[bool] = []
    monkeypatch.setattr(app, "run", lambda: calls.append(True))
    main()
    assert calls == [True]
