import anyio
import httpx
import pytest

from firefly_mcp.auth import INVALID_TTL_SECONDS, FireflyTokenVerifier

pytestmark = pytest.mark.anyio


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def verifier(clock) -> FireflyTokenVerifier:
    return FireflyTokenVerifier(ttl=60, clock=clock)


async def test_valid_token_is_checked_against_firefly_once_per_ttl(firefly, verifier, clock):
    assert (await verifier.verify_token("user-token")).token == "user-token"
    assert await verifier.verify_token("user-token") is not None

    assert len(firefly.calls) == 1
    assert firefly.last.url.path == "/api/v1/about/user"
    assert firefly.last.headers["Authorization"] == "Bearer user-token"

    clock.now += 61
    await verifier.verify_token("user-token")
    assert len(firefly.calls) == 2


async def test_rejected_token_is_remembered_briefly(firefly, verifier, clock):
    firefly.status = 401

    assert await verifier.verify_token("revoked") is None
    assert await verifier.verify_token("revoked") is None
    assert len(firefly.calls) == 1

    clock.now += INVALID_TTL_SECONDS + 1
    firefly.status = 200
    assert await verifier.verify_token("revoked") is not None


async def test_network_error_is_not_cached(firefly, verifier):
    firefly.exc = httpx.ConnectError("down")
    assert await verifier.verify_token("t") is None

    firefly.exc = None
    assert await verifier.verify_token("t") is not None
    assert len(firefly.calls) == 2


async def test_concurrent_checks_share_one_firefly_call(firefly, verifier):
    async with anyio.create_task_group() as tg:
        for _ in range(10):
            tg.start_soon(verifier.verify_token, "same-token")

    assert len(firefly.calls) == 1


async def test_raw_token_is_never_a_cache_key(firefly, verifier):
    await verifier.verify_token("secret-token")

    assert "secret-token" not in repr(verifier._cache)
