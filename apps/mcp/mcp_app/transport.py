"""Transport selection and bearer auth for the quality-platform MCP server (#267, M1-8).

stdio stays the default and stays unauthenticated: a local host (Claude Desktop / Cursor /
Claude Code) launching ``quality-mcp`` with no environment set gets exactly today's
behaviour. Setting ``MCP_TRANSPORT=http`` opts into FastMCP's Streamable HTTP transport,
which is **always** authenticated — there is no unauthenticated HTTP mode.

Four environment variables, read only at startup (the ``os.environ.get`` shape follows
``fmea_app._logging``; no config framework, no ``.env`` loader):

============================  ==========================================================
``MCP_TRANSPORT``             ``"stdio"`` (default) or ``"http"``; anything else is fatal
``MCP_HOST``                  bind address, default ``127.0.0.1`` (loopback)
``MCP_PORT``                  bind port, default ``8000``
``MCP_AUTH_TOKEN``            shared secret; **required** when transport is ``http``
============================  ==========================================================

Fail-closed everywhere: HTTP mode with no token refuses to start rather than binding an
open port, and an unrecognised ``MCP_TRANSPORT`` raises instead of silently falling back to
a transport the operator did not ask for. The default bind is loopback-only; exposing the
server publicly is an explicit opt-in (``MCP_HOST=0.0.0.0``). The token value is never
logged and never appears in an exception message — mirroring ``server._call``'s "a client
never sees anything it shouldn't" convention.

ponytail: one shared secret, compared with ``hmac.compare_digest`` — correct and sufficient
while remote mode is private to the M5 web API, which is the only planned caller today.
Per-client tokens, scopes, rotation and OAuth are deliberately NOT built here; FastMCP
already vendors that machinery (``JWTVerifier``, ``OAuthProxy``), so it can be adopted in M6
when actual hosting decides the real trust boundary. Upgrade path: swap the ``AuthProvider``
returned by :func:`build_auth_provider` — nothing else in the server knows about auth.
"""

from __future__ import annotations

import hmac
import os

from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, TokenVerifier

TRANSPORT_ENV = "MCP_TRANSPORT"
HOST_ENV = "MCP_HOST"
PORT_ENV = "MCP_PORT"
TOKEN_ENV = "MCP_AUTH_TOKEN"

DEFAULT_TRANSPORT = "stdio"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "8000"


class SharedSecretVerifier(TokenVerifier):
    """Single-token bearer auth: ``hmac.compare_digest`` against one env-sourced secret.

    Deliberately not ``fastmcp.server.auth.providers.jwt.StaticTokenVerifier``: that one is
    documented as a dev/testing helper that stores tokens in plain text and looks them up
    with ``dict.get``, which is not a constant-time compare. This is the minimal correct
    thing at a trust boundary — one secret, one comparison, no dict, no scopes, no client
    registry.

    Setting this on ``FastMCP.auth`` is all that is needed to reject unauthenticated calls:
    ``AuthProvider.get_middleware`` installs Starlette's ``AuthenticationMiddleware`` with
    the MCP ``BearerAuthBackend``, so a missing, malformed or wrong ``Authorization`` header
    is a 401 from the library. No hand-rolled HTTP handling here.
    """

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return an ``AccessToken`` iff ``token`` matches the shared secret, else ``None``.

        ``compare_digest`` keeps the comparison independent of how many leading characters
        of a guess are correct, so a wrong token leaks no timing signal about the right one.
        """
        if hmac.compare_digest(token, self._token):
            return AccessToken(token=token, client_id="remote", scopes=[])
        return None


def build_auth_provider() -> SharedSecretVerifier:
    """Build the HTTP auth provider from ``MCP_AUTH_TOKEN``.

    Raises:
        RuntimeError: if the variable is unset or empty. HTTP mode fails closed — the
            server refuses to start rather than serving an open endpoint. The message
            names the variable, never a value.
    """
    token = os.environ.get(TOKEN_ENV, "")
    if not token:
        raise RuntimeError(
            f"{TOKEN_ENV} must be set to a non-empty shared secret when "
            f"{TRANSPORT_ENV}=http; refusing to start an unauthenticated HTTP server."
        )
    return SharedSecretVerifier(token)


def run_server(app: FastMCP) -> None:
    """Run ``app`` on the env-selected transport (default stdio).

    ``stdio`` calls ``app.run()`` with no arguments — byte-identical to the pre-#267 entry
    point, and ``MCP_AUTH_TOKEN`` is never read. ``http`` attaches the shared-secret
    verifier before starting; ``FastMCP.auth`` is a plain mutable attribute, so the
    module-level ``app`` singleton needs no restructuring.

    Raises:
        RuntimeError: for an unrecognised ``MCP_TRANSPORT``, or for HTTP mode with no
            configured token (both before ``app.run`` is reached).
        ValueError: if ``MCP_PORT`` is not an integer — an operator config error should be
            loud at startup.
    """
    transport = os.environ.get(TRANSPORT_ENV, DEFAULT_TRANSPORT)
    if transport == DEFAULT_TRANSPORT:
        app.run()
        return
    if transport != "http":
        raise RuntimeError(
            f"Unrecognised {TRANSPORT_ENV}={transport!r}; expected 'stdio' or 'http'."
        )
    app.auth = build_auth_provider()
    app.run(
        transport="http",
        host=os.environ.get(HOST_ENV, DEFAULT_HOST),
        port=int(os.environ.get(PORT_ENV, DEFAULT_PORT)),
    )
