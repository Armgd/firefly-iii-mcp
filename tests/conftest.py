import os

os.environ.setdefault("FIREFLY_III_URL", "https://firefly.test")
os.environ.setdefault("FIREFLY_III_ACCESS_TOKEN", "test-pat")

import httpx
import pytest
from fastmcp import Client

from firefly_mcp import client as firefly_client
from firefly_mcp.server import mcp


class FakeFirefly:
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.status = 200
        self.payload: dict = {"data": []}
        self.exc: Exception | None = None

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if self.exc is not None:
            raise self.exc
        return httpx.Response(self.status, json=self.payload)

    @property
    def last(self) -> httpx.Request:
        return self.calls[-1]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def firefly(monkeypatch: pytest.MonkeyPatch) -> FakeFirefly:
    fake = FakeFirefly()
    http = httpx.AsyncClient(
        base_url="https://firefly.test/api", transport=httpx.MockTransport(fake.handle)
    )
    monkeypatch.setattr(firefly_client, "get_client", lambda: http)
    return fake


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as c:
        yield c
