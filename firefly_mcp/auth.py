"""Who may use the MCP endpoint, and with which Firefly III token.

Two modes, fixed at startup by the environment:

- PAT: one Firefly Personal Access Token for everyone, the HTTP endpoint
  optionally protected by the shared secret ``MCP_AUTH_TOKEN``.
- OAuth: users sign in to Firefly III in their browser (FastMCP ``OAuthProxy``)
  and every tool call runs with that user's own Firefly token.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import ssl
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import urlparse

import httpx
import httpx2
from cryptography.fernet import Fernet
from fastmcp.server.auth import AccessToken, AuthProvider, TokenVerifier
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth.oauth_proxy.upstream import AsyncOAuth2Client
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

from . import client as firefly_client
from .client import ssl_verify

logger = logging.getLogger(__name__)

MIN_SECRET_LENGTH = 32
DEFAULT_VALIDATION_TTL_SECONDS = 60.0
INVALID_TTL_SECONDS = 5.0
CALLBACK_PATH = "/auth/callback"
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
_UPSTREAM_TIMEOUT = 30.0


@dataclass(frozen=True)
class PatMode:
    name: ClassVar[str] = "pat"
    token: str
    shared_secret: str | None = None


@dataclass(frozen=True)
class OAuthMode:
    name: ClassVar[str] = "oauth"
    client_id: str
    client_secret: str
    base_url: str
    firefly_url: str
    is_remote: bool
    jwt_signing_key: str | None = None
    storage_encryption_key: str | None = None
    redis_url: str | None = None
    validation_ttl: float = DEFAULT_VALIDATION_TTL_SECONDS
    allowed_redirect_uris: tuple[str, ...] | None = None
    token_endpoint_auth_method: str | None = None

    @property
    def callback_url(self) -> str:
        return f"{self.base_url}{CALLBACK_PATH}"


AuthMode = PatMode | OAuthMode


def resolve_auth_mode(env: Mapping[str, str] = os.environ) -> AuthMode:
    def get(key: str) -> str | None:
        return env.get(key, "").strip() or None

    pat = get("FIREFLY_III_ACCESS_TOKEN")
    shared_secret = get("MCP_AUTH_TOKEN")
    client_id = get("FIREFLY_III_OAUTH_CLIENT_ID")
    client_secret = get("FIREFLY_III_OAUTH_CLIENT_SECRET")

    if not (client_id or client_secret):
        if not pat:
            raise RuntimeError(
                "Set either FIREFLY_III_ACCESS_TOKEN (PAT mode) or "
                "FIREFLY_III_OAUTH_CLIENT_ID + FIREFLY_III_OAUTH_CLIENT_SECRET + "
                "MCP_BASE_URL (OAuth mode)."
            )
        if shared_secret and len(shared_secret) < MIN_SECRET_LENGTH:
            raise RuntimeError(
                f"MCP_AUTH_TOKEN must be at least {MIN_SECRET_LENGTH} characters "
                "(e.g. `openssl rand -hex 32`)."
            )
        return PatMode(token=pat, shared_secret=shared_secret)

    if pat:
        raise RuntimeError(
            "FIREFLY_III_ACCESS_TOKEN and FIREFLY_III_OAUTH_* are mutually exclusive: "
            "remove the token to use OAuth."
        )
    if shared_secret:
        raise RuntimeError("MCP_AUTH_TOKEN cannot be combined with OAuth mode: remove it.")
    return _oauth_mode(get, client_id, client_secret)


def _oauth_mode(
    get: Callable[[str], str | None], client_id: str | None, client_secret: str | None
) -> OAuthMode:
    required = {
        "FIREFLY_III_URL": get("FIREFLY_III_URL"),
        "FIREFLY_III_OAUTH_CLIENT_ID": client_id,
        "FIREFLY_III_OAUTH_CLIENT_SECRET": client_secret,
        "MCP_BASE_URL": get("MCP_BASE_URL"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"OAuth mode is missing: {', '.join(missing)}")

    base_url = required["MCP_BASE_URL"].rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError(f"MCP_BASE_URL must be an http(s) URL, got {base_url!r}")
    is_remote = parsed.hostname not in LOOPBACK_HOSTS

    jwt_signing_key = get("FIREFLY_III_OAUTH_JWT_SIGNING_KEY")
    storage_key = get("FIREFLY_III_OAUTH_STORAGE_ENCRYPTION_KEY")
    redis_url = get("FIREFLY_III_OAUTH_REDIS_URL")
    if is_remote and not jwt_signing_key:
        raise RuntimeError("Remote OAuth mode requires FIREFLY_III_OAUTH_JWT_SIGNING_KEY.")
    if redis_url and not storage_key:
        raise RuntimeError(
            "FIREFLY_III_OAUTH_REDIS_URL requires FIREFLY_III_OAUTH_STORAGE_ENCRYPTION_KEY."
        )
    if is_remote and parsed.scheme == "http":
        logger.warning("MCP_BASE_URL is public plain http: tokens travel unencrypted.")

    redirects = get("FIREFLY_III_OAUTH_ALLOWED_REDIRECT_URIS")
    return OAuthMode(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        firefly_url=required["FIREFLY_III_URL"].rstrip("/"),
        is_remote=is_remote,
        jwt_signing_key=jwt_signing_key,
        storage_encryption_key=storage_key,
        redis_url=redis_url,
        validation_ttl=float(
            get("FIREFLY_III_OAUTH_VALIDATION_TTL") or DEFAULT_VALIDATION_TTL_SECONDS
        ),
        allowed_redirect_uris=(
            tuple(uri.strip() for uri in redirects.split(",")) if redirects else None
        ),
        token_endpoint_auth_method=get("FIREFLY_III_OAUTH_TOKEN_ENDPOINT_AUTH_METHOD"),
    )


class SharedSecretVerifier(TokenVerifier):
    def __init__(self, secret: str) -> None:
        super().__init__()
        self._secret = secret.encode()

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(token.encode(), self._secret):
            return None
        return AccessToken(token=token, client_id="mcp-client", scopes=[])


@dataclass(frozen=True)
class _Verdict:
    is_valid: bool
    expires_at: float


class FireflyTokenVerifier(TokenVerifier):
    """Accepts a user's Firefly token if Firefly itself still accepts it.

    Verdicts are cached by token hash (valid: ``ttl``, rejected: a few seconds);
    concurrent checks of one token share a single Firefly call.
    """

    def __init__(
        self,
        ttl: float = DEFAULT_VALIDATION_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__()
        self._ttl = ttl
        self._clock = clock
        self._cache: dict[str, _Verdict] = {}
        self._inflight: dict[str, asyncio.Task[bool | None]] = {}

    async def verify_token(self, token: str) -> AccessToken | None:
        key = hashlib.sha256(token.encode()).hexdigest()
        cached = self._cache.get(key)
        if cached is not None and cached.expires_at > self._clock():
            is_valid: bool | None = cached.is_valid
        else:
            task = self._inflight.get(key)
            if task is None:
                task = asyncio.ensure_future(self._ask_firefly(key, token))
                self._inflight[key] = task
                task.add_done_callback(lambda _: self._inflight.pop(key, None))
            is_valid = await task
        if not is_valid:
            return None
        return AccessToken(token=token, client_id="firefly", scopes=[])

    async def _ask_firefly(self, key: str, token: str) -> bool | None:
        try:
            response = await firefly_client.get_client().get(
                "/v1/about/user", headers={"Authorization": f"Bearer {token}"}
            )
        except httpx.TransportError as exc:
            logger.warning("Could not validate token %s…: %r", key[:8], exc)
            return None
        is_valid = response.is_success
        now = self._clock()
        ttl = self._ttl if is_valid else INVALID_TTL_SECONDS
        self._cache = {
            **{k: v for k, v in self._cache.items() if v.expires_at > now},
            key: _Verdict(is_valid=is_valid, expires_at=now + ttl),
        }
        return is_valid


class FireflyOAuthProxy(OAuthProxy):
    """``OAuthProxy`` whose calls to Firefly's token endpoint honour
    ``FIREFLY_III_VERIFY_SSL`` (self-signed or private-CA instances)."""

    def __init__(self, *, verify: bool | ssl.SSLContext, **kwargs) -> None:
        super().__init__(**kwargs)
        self._verify = verify

    def _create_upstream_oauth_client(self) -> AsyncOAuth2Client:
        client = super()._create_upstream_oauth_client()
        client._client = httpx2.AsyncClient(timeout=_UPSTREAM_TIMEOUT, verify=self._verify)
        return client


def _redis_storage(mode: OAuthMode) -> FernetEncryptionWrapper:
    try:
        from key_value.aio.stores.redis import RedisStore
    except ImportError as exc:
        raise RuntimeError(
            "FIREFLY_III_OAUTH_REDIS_URL is set but Redis support is not installed: "
            "install the `redis` extra (uv sync --extra redis)."
        ) from exc
    return FernetEncryptionWrapper(
        key_value=RedisStore(url=mode.redis_url),
        fernet=Fernet(mode.storage_encryption_key),
    )


def build_auth(mode: AuthMode) -> AuthProvider | None:
    verify = ssl_verify()
    if isinstance(mode, PatMode):
        if mode.shared_secret is None:
            logger.warning(
                "MCP_AUTH_TOKEN is not set: the HTTP endpoint accepts unauthenticated "
                "requests with full access to Firefly III. Set it unless the server "
                "is only reachable from a trusted machine."
            )
            return None
        return SharedSecretVerifier(mode.shared_secret)

    return FireflyOAuthProxy(
        verify=verify,
        upstream_authorization_endpoint=f"{mode.firefly_url}/oauth/authorize",
        upstream_token_endpoint=f"{mode.firefly_url}/oauth/token",
        upstream_client_id=mode.client_id,
        upstream_client_secret=mode.client_secret,
        token_verifier=FireflyTokenVerifier(ttl=mode.validation_ttl),
        base_url=mode.base_url,
        redirect_path=CALLBACK_PATH,
        allowed_client_redirect_uris=(
            list(mode.allowed_redirect_uris) if mode.allowed_redirect_uris else None
        ),
        token_endpoint_auth_method=mode.token_endpoint_auth_method,
        jwt_signing_key=mode.jwt_signing_key,
        client_storage=_redis_storage(mode) if mode.redis_url else None,
    )
