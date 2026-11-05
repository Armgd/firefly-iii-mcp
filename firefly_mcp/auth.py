"""Shared-secret protection for the HTTP endpoint.

Interim measure until the OAuth design lands: when ``MCP_AUTH_TOKEN`` is set,
every MCP request must carry ``Authorization: Bearer <MCP_AUTH_TOKEN>``.
This secret is only checked here and is never forwarded to Firefly III."""

from __future__ import annotations

import hmac
import logging
import os

from fastmcp.server.auth import AccessToken, TokenVerifier

logger = logging.getLogger(__name__)

MIN_SECRET_LENGTH = 32


class SharedSecretVerifier(TokenVerifier):
    def __init__(self, secret: str) -> None:
        super().__init__()
        self._secret = secret.encode()

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(token.encode(), self._secret):
            return None
        return AccessToken(token=token, client_id="mcp-client", scopes=[])


def auth_from_env() -> SharedSecretVerifier | None:
    secret = os.environ.get("MCP_AUTH_TOKEN", "").strip()
    if not secret:
        logger.warning(
            "MCP_AUTH_TOKEN is not set: the HTTP endpoint accepts unauthenticated "
            "requests with full access to Firefly III. Set it unless the server "
            "is only reachable from a trusted machine."
        )
        return None
    if len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"MCP_AUTH_TOKEN must be at least {MIN_SECRET_LENGTH} characters "
            "(e.g. `openssl rand -hex 32`)."
        )
    return SharedSecretVerifier(secret)
