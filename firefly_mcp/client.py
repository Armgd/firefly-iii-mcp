"""Async HTTP client and request helper for the Firefly III API.

The client is built lazily on first use so that importing tool modules at module
load time does not require the Firefly III env vars to be set (handy for tests
and code inspection).
"""

from __future__ import annotations

import logging
import os
import ssl
from functools import lru_cache
from typing import Any

import httpx
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token

_TIMEOUT = 30.0
_FALSE_VALUES = {"false", "0", "no", "off"}
_TRUE_VALUES = {"true", "1", "yes", "on"}

logger = logging.getLogger(__name__)


class FireflyAPIError(ToolError):
    """Raised when the Firefly III API returns a non-2xx response.

    Being a ``ToolError``, its message (including field-level validation
    errors) is shown to the model even when other error details are masked.

    Attributes:
        status_code: HTTP status from the upstream API.
        message: Human-readable error message extracted from the response body.
        errors: Field-level validation errors when available. Firefly returns
            a ``{"errors": {field: [msg, ...]}}`` shape on 422 validation failures.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        errors: dict[str, Any] | None = None,
    ) -> None:
        detail = f" Field errors: {errors}" if errors else ""
        super().__init__(f"Firefly III API error {status_code}: {message}{detail}")
        self.status_code = status_code
        self.message = message
        self.errors = errors


def ssl_verify() -> bool | ssl.SSLContext:
    """TLS verification for every call to Firefly III.

    ``FIREFLY_III_VERIFY_SSL`` accepts ``true`` (default), ``false``, or the path
    to a CA file that signed a private/self-signed Firefly III certificate.
    """
    raw = os.environ.get("FIREFLY_III_VERIFY_SSL", "true").strip()
    if raw.lower() in _FALSE_VALUES:
        return False
    if raw.lower() in _TRUE_VALUES:
        return True
    if not os.path.isfile(raw):
        raise RuntimeError(f"FIREFLY_III_VERIFY_SSL points to a missing CA file: {raw}")
    return ssl.create_default_context(cafile=raw)


def current_token() -> str:
    """Firefly III token for the current call.

    With ``FIREFLY_III_ACCESS_TOKEN`` set (PAT mode) it is that token. Otherwise
    (OAuth mode, enforced exclusive at startup) it is the signed-in user's own
    Firefly token.
    """
    pat = os.environ.get("FIREFLY_III_ACCESS_TOKEN")
    if pat:
        return pat
    access_token = get_access_token()
    if access_token is None:
        raise ToolError("Not signed in to Firefly III. Reconnect the MCP client.")
    return access_token.token


@lru_cache(maxsize=1)
def get_client() -> httpx.AsyncClient:
    """Return a process-wide ``httpx.AsyncClient`` bound to the Firefly III API.

    The client carries no credentials: :func:`request` adds the caller's token
    on each call. Raises ``KeyError`` if ``FIREFLY_III_URL`` is missing.
    """
    base = os.environ["FIREFLY_III_URL"].rstrip("/")
    return httpx.AsyncClient(
        base_url=f"{base}/api",
        timeout=_TIMEOUT,
        verify=ssl_verify(),
        headers={
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/json",
        },
    )


async def request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform a request against the Firefly III API and return parsed JSON.

    - 204 No Content responses return an empty dict.
    - Non-2xx responses are raised as :class:`FireflyAPIError` with the upstream
      ``message`` and ``errors`` fields preserved when present.
    """
    headers = {"Authorization": f"Bearer {current_token()}"}
    client = get_client()
    if params:
        params = {k: v for k, v in params.items() if v is not None}
    try:
        response = await client.request(method, path, params=params, json=json, headers=headers)
    except httpx.TransportError as exc:
        logger.warning("Firefly III request %s %s failed: %r", method, path, exc)
        raise ToolError(
            "Could not reach Firefly III (network error or timeout). Try again later."
        ) from exc

    if response.status_code == 204 or not response.content:
        return {}

    if response.is_error:
        try:
            data = response.json()
        except ValueError:
            raise FireflyAPIError(
                response.status_code,
                response.text or "Unknown error",
            ) from None
        message = data.get("message") or "Request failed"
        raise FireflyAPIError(
            response.status_code,
            message,
            errors=data.get("errors"),
        )

    return response.json()
