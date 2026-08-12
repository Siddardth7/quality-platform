"""Transport selection + shared-secret auth (#267, M1-8) for the MCP server.

No ``pytest-asyncio`` in this workspace, so async coroutines are driven with
``anyio.run`` (fastmcp already depends on anyio). The HTTP side runs in-process over
``httpx.ASGITransport`` — no socket is ever bound — inside the ASGI lifespan, because
FastMCP's Streamable HTTP session manager only starts on lifespan enter.

``app.auth`` is a module-level singleton; the autouse fixture saves and restores it (and
clears the four ``MCP_*`` env vars) so no test leaks auth/config state into the existing
server tests running in the same process.
"""

from __future__ import annotations

import hmac
from typing import Any

import anyio
import httpx
import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server.auth import AccessToken
from mcp_app import __version__
from mcp_app.server import app, health, version
from mcp_app.transport import (
    DEFAULT_HOST,
    HOST_ENV,
    PORT_ENV,
    TOKEN_ENV,
    TRANSPORT_ENV,
    SharedSecretVerifier,
    build_auth_provider,
    run_server,
)

TEST_TOKEN = "test-secret-abc123"


@pytest.fixture(autouse=True)
def _clean_transport_state(monkeypatch: pytest.MonkeyPatch):
    """Isolate every test: clear MCP_* env and restore the app.auth singleton."""
    for name in (TRANSPORT_ENV, HOST_ENV, PORT_ENV, TOKEN_ENV):
        monkeypatch.delenv(name, raising=False)
    saved_auth = app.auth
    yield
    app.auth = saved_auth


def _patch_run(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[Any, ...], dict[str, Any]]]:
    """Replace the blocking ``app.run`` with a recorder; return the recorded calls."""
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    monkeypatch.setattr(app, "run", lambda *a, **k: calls.append((a, k)))
    return calls


# ---------------------------------------------------------------------------
# run_server — transport selection
# ---------------------------------------------------------------------------


def test_run_server_stdio_default_calls_run_with_no_args(monkeypatch: pytest.MonkeyPatch):
    # MCP_TRANSPORT unset -> stdio -> app.run() with no transport args, no token read.
    calls = _patch_run(monkeypatch)
    run_server(app)
    assert calls == [((), {})]


def test_run_server_stdio_explicit_calls_run_with_no_args(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TRANSPORT_ENV, "stdio")
    calls = _patch_run(monkeypatch)
    run_server(app)
    assert calls == [((), {})]


def test_run_server_unknown_transport_raises_naming_value(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TRANSPORT_ENV, "htp")
    calls = _patch_run(monkeypatch)
    with pytest.raises(RuntimeError, match="htp"):
        run_server(app)
    assert calls == []  # fail closed: never fell back to a transport


def test_run_server_http_valid_token_uses_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TRANSPORT_ENV, "http")
    monkeypatch.setenv(TOKEN_ENV, TEST_TOKEN)
    calls = _patch_run(monkeypatch)
    run_server(app)
    assert calls == [((), {"transport": "http", "host": DEFAULT_HOST, "port": 8000})]
    assert isinstance(app.auth, SharedSecretVerifier)


def test_run_server_http_host_port_overrides(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TRANSPORT_ENV, "http")
    monkeypatch.setenv(TOKEN_ENV, TEST_TOKEN)
    monkeypatch.setenv(HOST_ENV, "0.0.0.0")
    monkeypatch.setenv(PORT_ENV, "9443")
    calls = _patch_run(monkeypatch)
    run_server(app)
    assert calls == [((), {"transport": "http", "host": "0.0.0.0", "port": 9443})]


def test_run_server_http_missing_token_fails_closed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TRANSPORT_ENV, "http")  # no MCP_AUTH_TOKEN
    calls = _patch_run(monkeypatch)
    with pytest.raises(RuntimeError, match=TOKEN_ENV):
        run_server(app)
    assert calls == []  # never bound an unauthenticated port


def test_run_server_http_empty_token_fails_closed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TRANSPORT_ENV, "http")
    monkeypatch.setenv(TOKEN_ENV, "")  # explicit empty -> `not token` branch
    calls = _patch_run(monkeypatch)
    with pytest.raises(RuntimeError, match=TOKEN_ENV):
        run_server(app)
    assert calls == []


def test_run_server_http_non_integer_port_raises_valueerror(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TRANSPORT_ENV, "http")
    monkeypatch.setenv(TOKEN_ENV, TEST_TOKEN)
    monkeypatch.setenv(PORT_ENV, "not-a-port")
    _patch_run(monkeypatch)
    with pytest.raises(ValueError):
        run_server(app)


def test_run_server_http_missing_token_message_names_no_value(monkeypatch: pytest.MonkeyPatch):
    # Fail-closed message must name the env var, never a secret; there is no token here,
    # but this pins the "message names the variable" contract.
    monkeypatch.setenv(TRANSPORT_ENV, "http")
    _patch_run(monkeypatch)
    with pytest.raises(RuntimeError) as exc:
        run_server(app)
    assert TOKEN_ENV in str(exc.value)
    assert TRANSPORT_ENV in str(exc.value)


# ---------------------------------------------------------------------------
# build_auth_provider
# ---------------------------------------------------------------------------


def test_build_auth_provider_returns_verifier_when_token_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TOKEN_ENV, TEST_TOKEN)
    provider = build_auth_provider()
    assert isinstance(provider, SharedSecretVerifier)


def test_build_auth_provider_raises_when_token_absent(monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(RuntimeError, match=TOKEN_ENV):
        build_auth_provider()


def test_build_auth_provider_raises_when_token_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TOKEN_ENV, "")
    with pytest.raises(RuntimeError, match=TOKEN_ENV):
        build_auth_provider()


# ---------------------------------------------------------------------------
# SharedSecretVerifier.verify_token
# ---------------------------------------------------------------------------


def test_verify_token_correct_returns_access_token():
    verifier = SharedSecretVerifier(TEST_TOKEN)
    result = anyio.run(verifier.verify_token, TEST_TOKEN)
    assert isinstance(result, AccessToken)
    assert result.client_id == "remote"
    assert result.scopes == []
    assert result.token == TEST_TOKEN


def test_verify_token_wrong_returns_none():
    verifier = SharedSecretVerifier(TEST_TOKEN)
    assert anyio.run(verifier.verify_token, "wrong-token") is None


def test_verify_token_empty_returns_none():
    verifier = SharedSecretVerifier(TEST_TOKEN)
    assert anyio.run(verifier.verify_token, "") is None


def test_verify_token_uses_hmac_compare_digest(monkeypatch: pytest.MonkeyPatch):
    # Negative control: a `==` mutation would not call compare_digest, failing this.
    seen: list[tuple[Any, Any]] = []
    real = hmac.compare_digest

    def spy(a: Any, b: Any) -> bool:
        seen.append((a, b))
        return real(a, b)

    monkeypatch.setattr(hmac, "compare_digest", spy)
    verifier = SharedSecretVerifier(TEST_TOKEN)
    anyio.run(verifier.verify_token, "guess-123")
    assert seen == [("guess-123", TEST_TOKEN)]


# ---------------------------------------------------------------------------
# Parity + auth rejection over real HTTP (in-process ASGI, no socket)
# ---------------------------------------------------------------------------


async def _http_call(asgi: Any, token: str | None, tool: str) -> Any:
    """Call one tool through the Streamable HTTP transport with the given bearer token."""

    def factory(**kw: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=asgi), **kw)

    http = StreamableHttpTransport(
        url="http://testserver/mcp", auth=token, httpx_client_factory=factory
    )
    async with Client(http) as client:
        return await client.call_tool(tool)


def test_http_parity_and_auth(caplog: pytest.LogCaptureFixture):
    """Same tools respond over HTTP as stdio; wrong/absent token is rejected; no secret logged."""
    app.auth = SharedSecretVerifier(TEST_TOKEN)
    asgi = app.http_app()

    async def driver() -> dict[str, Any]:
        async with asgi.router.lifespan_context(asgi):
            good_health = await _http_call(asgi, TEST_TOKEN, "health")
            good_version = await _http_call(asgi, TEST_TOKEN, "version")
            wrong_err: str | None = None
            try:
                await _http_call(asgi, "wrong-token", "health")
            except Exception as exc:  # noqa: BLE001
                wrong_err = f"{type(exc).__name__}: {exc}"
            missing_err: str | None = None
            try:
                await _http_call(asgi, None, "health")
            except Exception as exc:  # noqa: BLE001
                missing_err = f"{type(exc).__name__}: {exc}"
        return {
            "health": good_health.data,
            "version": good_version.data,
            "wrong_err": wrong_err,
            "missing_err": missing_err,
        }

    with caplog.at_level("DEBUG"):
        out = anyio.run(driver)

    # Parity: the HTTP payloads match the direct (stdio-equivalent) function results.
    assert out["health"] == health() == {"status": "ok"}
    assert out["version"] == version() == {"version": __version__}
    # Rejection: wrong token and absent token both fail (401), not a tool result.
    assert out["wrong_err"] is not None and "401" in out["wrong_err"]
    assert out["missing_err"] is not None and "401" in out["missing_err"]
    # No secret ever hits the logs, on success or failure paths.
    assert TEST_TOKEN not in caplog.text
    assert "wrong-token" not in caplog.text
