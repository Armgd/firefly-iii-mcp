"""Async HTTP client and request helper for the Firefly III API.

The client is built lazily on first use so that importing tool modules at module
load time does not require the Firefly III env vars to be set (handy for tests
and code inspection).
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

import httpx
from fastmcp.exceptions import ToolError

_TIMEOUT = 30.0

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


@lru_cache(maxsize=1)
def get_client() -> httpx.AsyncClient:
    """Return a process-wide ``httpx.AsyncClient`` bound to the Firefly III API.

    Reads ``FIREFLY_III_URL`` and ``FIREFLY_III_ACCESS_TOKEN`` from the
    environment. Raises ``KeyError`` if either is missing.

    Set ``FIREFLY_III_VERIFY_SSL=false`` to disable TLS verification (useful for
    self-signed certificates on a private Firefly III instance). Defaults to on.
    """
    base = os.environ["FIREFLY_III_URL"].rstrip("/")
    token = os.environ["FIREFLY_III_ACCESS_TOKEN"]
    verify_raw = os.environ.get("FIREFLY_III_VERIFY_SSL", "true").strip().lower()
    verify = verify_raw not in {"false", "0", "no", "off"}
    return httpx.AsyncClient(
        base_url=f"{base}/api",
        timeout=_TIMEOUT,
        verify=verify,
        headers={
            "Authorization": f"Bearer {token}",
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
    client = get_client()
    if params:
        params = {k: v for k, v in params.items() if v is not None}
    try:
        response = await client.request(method, path, params=params, json=json)
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
