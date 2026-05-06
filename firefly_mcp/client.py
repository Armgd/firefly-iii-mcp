"""Async HTTP client and request helper for the Firefly III API.

The client is built lazily on first use so that importing tool modules at module
load time does not require the Firefly III env vars to be set (handy for tests
and code inspection).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import httpx

_TIMEOUT = 30.0


class FireflyAPIError(Exception):
    """Raised when the Firefly III API returns a non-2xx response.

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
        super().__init__(f"Firefly III API error {status_code}: {message}")
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
    response = await client.request(method, path, params=params, json=json)

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
