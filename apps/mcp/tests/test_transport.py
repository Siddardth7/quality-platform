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
from fastmcp.server.auth.providers.jwt import JWTVerifier, RSAKeyPair
from fastmcp.server.auth.providers.workos import AuthKitProvider
from mcp_app import __version__
from mcp_app.server import app, health, version
from mcp_app.transport import (
    AUTH_MODE_ENV,
    DEFAULT_HOST,
    HOST_ENV,
    OAUTH_AUTH_MODE,
    OAUTH_AUTHKIT_DOMAIN_ENV,
    OAUTH_BASE_URL_ENV,
    PORT_ENV,
    TOKEN_ENV,
    TRANSPORT_ENV,
    SharedSecretVerifier,
    build_auth_provider,
    run_server,
)

TEST_TOKEN = "test-secret-abc123"

# Hermetic OAuth-mode fixtures: fake (never-resolved) URLs and a self-signed keypair.
# No test ever reaches a real WorkOS/JWKS endpoint — token validation is exercised
# offline by injecting a JWTVerifier holding this keypair's public key.
OAUTH_DOMAIN = "https://a.authkit.app"
OAUTH_BASE_URL = "https://mcp.example.com"
OAUTH_RESOURCE_URL = f"{OAUTH_BASE_URL}/mcp"
_PROTECTED_RESOURCE_METADATA = "/.well-known/oauth-protected-resource/mcp"


@pytest.fixture(autouse=True)
def _clean_transport_state(monkeypatch: pytest.MonkeyPatch):
    """Isolate every test: clear MCP_* env and restore the app.auth singleton."""
    for name in (
        TRANSPORT_ENV,
        HOST_ENV,
        PORT_ENV,
        TOKEN_ENV,
        AUTH_MODE_ENV,
        OAUTH_AUTHKIT_DOMAIN_ENV,
        OAUTH_BASE_URL_ENV,
    ):
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


async def _http_call(
    asgi: Any, token: str | None, tool: str, arguments: dict[str, Any] | None = None
) -> Any:
    """Call one tool through the Streamable HTTP transport with the given bearer token."""

    def factory(**kw: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=asgi), **kw)

    http = StreamableHttpTransport(
        url="http://testserver/mcp", auth=token, httpx_client_factory=factory
    )
    async with Client(http) as client:
        return await client.call_tool(tool, arguments or {})


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


def test_qdb_answer_question_rejected_without_valid_token():
    """The M5-2 RAG tool (#288), specifically, is gated by the shared secret.

    Auth is transport-level (``SharedSecretVerifier`` on ``app.auth``), applied to every
    ``@app.tool`` before its body runs — so a wrong or missing token is rejected with 401
    and the corpus is never touched, even though this tool needs a corpus, an embedder
    and a generator none of which exist here. This proves the new tool is not silently
    unauthenticated, not merely that the transport rejects in general.
    """
    app.auth = SharedSecretVerifier(TEST_TOKEN)
    asgi = app.http_app()
    question = {"question": "what is Gage R&R?"}

    async def driver() -> dict[str, str | None]:
        async with asgi.router.lifespan_context(asgi):
            wrong_err: str | None = None
            try:
                await _http_call(asgi, "wrong-token", "qdb_answer_question", question)
            except Exception as exc:  # noqa: BLE001
                wrong_err = f"{type(exc).__name__}: {exc}"
            missing_err: str | None = None
            try:
                await _http_call(asgi, None, "qdb_answer_question", question)
            except Exception as exc:  # noqa: BLE001
                missing_err = f"{type(exc).__name__}: {exc}"
        return {"wrong_err": wrong_err, "missing_err": missing_err}

    out = anyio.run(driver)
    assert out["wrong_err"] is not None and "401" in out["wrong_err"]
    assert out["missing_err"] is not None and "401" in out["missing_err"]


# ---------------------------------------------------------------------------
# build_auth_provider — MCP_AUTH_MODE dispatch (#355)
# ---------------------------------------------------------------------------


def test_build_auth_provider_bearer_explicit(monkeypatch: pytest.MonkeyPatch):
    # MCP_AUTH_MODE=bearer selects the shared-secret verifier (not the OAuth path).
    monkeypatch.setenv(AUTH_MODE_ENV, "bearer")
    monkeypatch.setenv(TOKEN_ENV, TEST_TOKEN)
    provider = build_auth_provider()
    assert isinstance(provider, SharedSecretVerifier)


def test_build_auth_provider_unknown_mode_fails_closed(monkeypatch: pytest.MonkeyPatch):
    # An unrecognised mode raises rather than silently falling back to bearer or oauth.
    monkeypatch.setenv(AUTH_MODE_ENV, "sso")
    monkeypatch.setenv(TOKEN_ENV, TEST_TOKEN)  # present, yet still must not fall through
    with pytest.raises(RuntimeError) as exc:
        build_auth_provider()
    assert AUTH_MODE_ENV in str(exc.value)  # message names the variable
    assert "sso" in str(exc.value)  # ...and the offending value (mode is not a secret)


def test_build_auth_provider_oauth_returns_authkit(monkeypatch: pytest.MonkeyPatch):
    # oauth mode with complete config yields a WorkOS AuthKit resource-server provider.
    monkeypatch.setenv(AUTH_MODE_ENV, OAUTH_AUTH_MODE)
    monkeypatch.setenv(OAUTH_AUTHKIT_DOMAIN_ENV, OAUTH_DOMAIN)
    monkeypatch.setenv(OAUTH_BASE_URL_ENV, OAUTH_BASE_URL)
    provider = build_auth_provider()
    assert isinstance(provider, AuthKitProvider)
    # AuthKit is advertised as the authorization server (RFC 9728 metadata source).
    assert [str(s) for s in provider.authorization_servers] == [f"{OAUTH_DOMAIN}/"]


def test_build_auth_provider_oauth_missing_domain_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
):
    # First loop iteration: the AuthKit domain is required; a missing one fails closed
    # naming that variable (not the base URL, not a value).
    monkeypatch.setenv(AUTH_MODE_ENV, OAUTH_AUTH_MODE)
    monkeypatch.setenv(OAUTH_BASE_URL_ENV, OAUTH_BASE_URL)  # base URL present
    with pytest.raises(RuntimeError) as exc:
        build_auth_provider()
    assert OAUTH_AUTHKIT_DOMAIN_ENV in str(exc.value)
    assert OAUTH_BASE_URL_ENV not in str(exc.value)


def test_build_auth_provider_oauth_missing_base_url_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
):
    # Second loop iteration: domain present, base URL missing -> names the base-URL var.
    monkeypatch.setenv(AUTH_MODE_ENV, OAUTH_AUTH_MODE)
    monkeypatch.setenv(OAUTH_AUTHKIT_DOMAIN_ENV, OAUTH_DOMAIN)  # domain present
    with pytest.raises(RuntimeError) as exc:
        build_auth_provider()
    assert OAUTH_BASE_URL_ENV in str(exc.value)


def test_build_auth_provider_oauth_empty_domain_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
):
    # An explicit empty string is treated as missing (the `not value` branch), same as
    # bearer mode's empty-token handling.
    monkeypatch.setenv(AUTH_MODE_ENV, OAUTH_AUTH_MODE)
    monkeypatch.setenv(OAUTH_AUTHKIT_DOMAIN_ENV, "")
    monkeypatch.setenv(OAUTH_BASE_URL_ENV, OAUTH_BASE_URL)
    with pytest.raises(RuntimeError, match=OAUTH_AUTHKIT_DOMAIN_ENV):
        build_auth_provider()


def test_run_server_http_oauth_mode_attaches_authkit(monkeypatch: pytest.MonkeyPatch):
    # run_server's untouched call site must attach the oauth provider, not the bearer one.
    monkeypatch.setenv(TRANSPORT_ENV, "http")
    monkeypatch.setenv(AUTH_MODE_ENV, OAUTH_AUTH_MODE)
    monkeypatch.setenv(OAUTH_AUTHKIT_DOMAIN_ENV, OAUTH_DOMAIN)
    monkeypatch.setenv(OAUTH_BASE_URL_ENV, OAUTH_BASE_URL)
    calls = _patch_run(monkeypatch)
    run_server(app)
    assert calls == [((), {"transport": "http", "host": DEFAULT_HOST, "port": 8000})]
    assert isinstance(app.auth, AuthKitProvider)


# ---------------------------------------------------------------------------
# OAuth mode over real HTTP (in-process ASGI, no socket, no WorkOS/JWKS network)
# ---------------------------------------------------------------------------


def _oauth_provider(verifier: JWTVerifier) -> AuthKitProvider:
    """AuthKit provider with an injected offline verifier (skips audience auto-bind).

    Passing ``token_verifier`` is AuthKitProvider's documented seam for supplying a
    verifier that validates against a static key instead of fetching AuthKit's JWKS.
    """
    return AuthKitProvider(
        authkit_domain=OAUTH_DOMAIN, base_url=OAUTH_BASE_URL, token_verifier=verifier
    )


def test_http_oauth_metadata_valid_token_and_rejection(caplog: pytest.LogCaptureFixture):
    """oauth mode: RFC 9728 metadata is unauthenticated, a valid JWT works, garbage 401s."""
    kp = RSAKeyPair.generate()
    verifier = JWTVerifier(
        public_key=kp.public_key, issuer=OAUTH_DOMAIN, audience=OAUTH_RESOURCE_URL
    )
    good_jwt = kp.create_token(issuer=OAUTH_DOMAIN, audience=OAUTH_RESOURCE_URL)
    app.auth = _oauth_provider(verifier)
    asgi = app.http_app()

    async def driver() -> dict[str, Any]:
        async with asgi.router.lifespan_context(asgi):
            transport = httpx.ASGITransport(app=asgi)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as raw:
                meta = await raw.get(_PROTECTED_RESOURCE_METADATA)  # no token sent
                garbage = await raw.post(
                    "/mcp",
                    headers={
                        "Authorization": "Bearer not.a.valid.jwt",
                        "Accept": "application/json, text/event-stream",
                        "Content-Type": "application/json",
                    },
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                )
            good_health = await _http_call(asgi, good_jwt, "health")
            missing_err: str | None = None
            try:
                await _http_call(asgi, None, "health")
            except Exception as exc:  # noqa: BLE001
                missing_err = f"{type(exc).__name__}: {exc}"
        return {
            "meta_status": meta.status_code,
            "meta_json": meta.json(),
            "garbage_status": garbage.status_code,
            "garbage_json": garbage.json(),
            "health": good_health.data,
            "missing_err": missing_err,
        }

    with caplog.at_level("DEBUG"):
        out = anyio.run(driver)

    # Metadata endpoint is reachable WITHOUT a token (client discovers the AS this way).
    assert out["meta_status"] == 200
    assert out["meta_json"]["resource"] == OAUTH_RESOURCE_URL
    assert out["meta_json"]["authorization_servers"] == [f"{OAUTH_DOMAIN}/"]
    # A valid, correctly-scoped JWT is accepted and the tool runs (parity with stdio).
    assert out["health"] == health() == {"status": "ok"}
    # A garbage bearer is a 401 invalid_token from the library, never a 500.
    assert out["garbage_status"] == 401
    assert out["garbage_json"]["error"] == "invalid_token"
    # An absent token is also rejected (401), not served.
    assert out["missing_err"] is not None and "401" in out["missing_err"]
    # No JWT and no private key material ever reaches the logs.
    assert good_jwt not in caplog.text
    assert kp.private_key.get_secret_value() not in caplog.text


def test_http_oauth_wrong_audience_rejected():
    """A signature-valid JWT minted for the wrong audience is rejected (aud is enforced)."""
    kp = RSAKeyPair.generate()
    verifier = JWTVerifier(
        public_key=kp.public_key, issuer=OAUTH_DOMAIN, audience=OAUTH_RESOURCE_URL
    )
    wrong_aud_jwt = kp.create_token(
        issuer=OAUTH_DOMAIN, audience="https://attacker.example.com/mcp"
    )
    app.auth = _oauth_provider(verifier)
    asgi = app.http_app()

    async def driver() -> str | None:
        async with asgi.router.lifespan_context(asgi):
            err: str | None = None
            try:
                await _http_call(asgi, wrong_aud_jwt, "health")
            except Exception as exc:  # noqa: BLE001
                err = f"{type(exc).__name__}: {exc}"
        return err

    err = anyio.run(driver)
    assert err is not None and "401" in err
