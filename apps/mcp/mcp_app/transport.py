"""Transport selection and HTTP auth for the quality-platform MCP server (#267, M1-8; #355, M6).

stdio stays the default and stays unauthenticated: a local host (Claude Desktop / Cursor /
Claude Code) launching ``quality-mcp`` with no environment set gets exactly today's
behaviour. Setting ``MCP_TRANSPORT=http`` opts into FastMCP's Streamable HTTP transport,
which is **always** authenticated — there is no unauthenticated HTTP mode.

Environment variables, read only at startup (the ``os.environ.get`` shape follows
``fmea_app._logging``; no config framework, no ``.env`` loader):

=============================  ==========================================================
``MCP_TRANSPORT``              ``"stdio"`` (default) or ``"http"``; anything else is fatal
``MCP_HOST``                   bind address, default ``127.0.0.1`` (loopback)
``MCP_PORT``                   bind port, default ``8000``
``MCP_AUTH_MODE``              ``"bearer"`` (default) or ``"oauth"``; anything else is fatal
``MCP_AUTH_TOKEN``             shared secret; **required** in ``bearer`` mode over ``http``
``MCP_OAUTH_AUTHKIT_DOMAIN``   WorkOS AuthKit domain; **required** in ``oauth`` mode
``MCP_OAUTH_BASE_URL``         this server's public URL; **required** in ``oauth`` mode
=============================  ==========================================================

Fail-closed everywhere: HTTP mode with no token (or ``oauth`` mode with incomplete WorkOS
config) refuses to start rather than binding an open port, and an unrecognised
``MCP_TRANSPORT``/``MCP_AUTH_MODE`` raises instead of silently falling back to something the
operator did not ask for. The default bind is loopback-only; exposing the server publicly is
an explicit opt-in (``MCP_HOST=0.0.0.0``). The token value is never logged and never appears
in an exception message — mirroring ``server._call``'s "a client never sees anything it
shouldn't" convention.

``bearer`` mode is one shared secret, compared with ``hmac.compare_digest`` — correct and
sufficient while remote mode is private to the M5 web API, and it stays the zero-config
default: unset ``MCP_AUTH_MODE`` is byte-for-byte today's behaviour.

``oauth`` mode (#355) is for web hosts (Claude.ai / ChatGPT connectors), which cannot hold a
shared secret. It makes this server an OAuth *resource server* only: FastMCP's
``AuthKitProvider`` validates WorkOS AuthKit-issued JWTs against the AuthKit JWKS and serves
RFC 9728 protected-resource metadata. No authorization server is hand-rolled here — token
issuance, Dynamic Client Registration and the auth-code/PKCE dance all stay with WorkOS.

ponytail: exactly two modes, mutually exclusive, one IdP. ``MultiAuth`` (accept either token
type at once) and other FastMCP provider wrappers (Auth0, Clerk, …) are deliberately NOT
wired — the upgrade path is still "swap the ``AuthProvider`` returned by
:func:`build_auth_provider`", nothing else in the server knows about auth.
"""

from __future__ import annotations

import hmac
import os

from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, AuthProvider, TokenVerifier
from fastmcp.server.auth.providers.workos import AuthKitProvider

TRANSPORT_ENV = "MCP_TRANSPORT"
HOST_ENV = "MCP_HOST"
PORT_ENV = "MCP_PORT"
TOKEN_ENV = "MCP_AUTH_TOKEN"
AUTH_MODE_ENV = "MCP_AUTH_MODE"
OAUTH_AUTHKIT_DOMAIN_ENV = "MCP_OAUTH_AUTHKIT_DOMAIN"
OAUTH_BASE_URL_ENV = "MCP_OAUTH_BASE_URL"

DEFAULT_TRANSPORT = "stdio"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "8000"
DEFAULT_AUTH_MODE = "bearer"
OAUTH_AUTH_MODE = "oauth"


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


def build_auth_provider() -> AuthProvider:
    """Build the HTTP auth provider selected by ``MCP_AUTH_MODE`` (default ``bearer``).

    Raises:
        RuntimeError: for an unrecognised ``MCP_AUTH_MODE``, or for any variable the
            selected mode requires being unset or empty. HTTP mode fails closed — the
            server refuses to start rather than serving an open endpoint. Messages name
            the variable, never a value.
    """
    mode = os.environ.get(AUTH_MODE_ENV, DEFAULT_AUTH_MODE)
    if mode == DEFAULT_AUTH_MODE:
        return _build_bearer_provider()
    if mode != OAUTH_AUTH_MODE:
        raise RuntimeError(
            f"Unrecognised {AUTH_MODE_ENV}={mode!r}; expected 'bearer' or 'oauth'."
        )
    return _build_oauth_provider()


def _build_bearer_provider() -> SharedSecretVerifier:
    """Build the shared-secret verifier from ``MCP_AUTH_TOKEN`` (unchanged since #267)."""
    token = os.environ.get(TOKEN_ENV, "")
    if not token:
        raise RuntimeError(
            f"{TOKEN_ENV} must be set to a non-empty shared secret when "
            f"{TRANSPORT_ENV}=http; refusing to start an unauthenticated HTTP server."
        )
    return SharedSecretVerifier(token)


def _build_oauth_provider() -> AuthKitProvider:
    """Build FastMCP's WorkOS ``AuthKitProvider`` from the ``MCP_OAUTH_*`` variables.

    ``AuthKitProvider`` is a ``RemoteAuthProvider``: it validates AuthKit-issued JWTs
    against ``<authkit_domain>/oauth2/jwks`` and advertises AuthKit as the authorization
    server in RFC 9728 protected-resource metadata. Nothing is configured here that the
    provider does not require — audience binding is automatic (it is set to the resource
    URL this server advertises, which WorkOS must also list as a Resource Indicator), and
    scopes are left unrestricted rather than inventing a scope model no tool checks.

    Both variables are required and neither is a secret (a public domain and this
    server's own public URL), so an invalid *value* is surfaced by ``AnyHttpUrl``'s own
    validation error at startup — the same "loud on operator config error" treatment
    ``int(MCP_PORT)`` already gets in :func:`run_server`.

    Raises:
        RuntimeError: if either variable is unset or empty; the message names it.
    """
    domain = os.environ.get(OAUTH_AUTHKIT_DOMAIN_ENV, "")
    base_url = os.environ.get(OAUTH_BASE_URL_ENV, "")
    for name, value in (
        (OAUTH_AUTHKIT_DOMAIN_ENV, domain),
        (OAUTH_BASE_URL_ENV, base_url),
    ):
        if not value:
            raise RuntimeError(
                f"{name} must be set to a non-empty URL when "
                f"{AUTH_MODE_ENV}=oauth; refusing to start with incomplete OAuth config."
            )
    return AuthKitProvider(authkit_domain=domain, base_url=base_url)


def run_server(app: FastMCP) -> None:
    """Run ``app`` on the env-selected transport (default stdio).

    ``stdio`` calls ``app.run()`` with no arguments — byte-identical to the pre-#267 entry
    point, and no auth variable is ever read. ``http`` attaches the provider chosen by
    ``MCP_AUTH_MODE`` before starting; ``FastMCP.auth`` is a plain mutable attribute, so the
    module-level ``app`` singleton needs no restructuring.

    Raises:
        RuntimeError: for an unrecognised ``MCP_TRANSPORT`` or ``MCP_AUTH_MODE``, or for
            HTTP mode with incomplete auth config (all before ``app.run`` is reached).
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
