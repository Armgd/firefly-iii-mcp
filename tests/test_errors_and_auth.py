import httpx
import pytest
from fastmcp import FastMCP
from starlette.testclient import TestClient

from firefly_mcp.auth import SharedSecretVerifier

pytestmark = pytest.mark.anyio


async def test_firefly_validation_errors_reach_the_model(firefly, mcp_client):
    firefly.status = 422
    firefly.payload = {
        "message": "The given data was invalid.",
        "errors": {"name": ["The name has already been taken."]},
    }

    result = await mcp_client.call_tool("create_category", {"name": "Food"}, raise_on_error=False)

    text = result.content[0].text
    assert result.is_error
    assert "The given data was invalid." in text
    assert "The name has already been taken." in text


async def test_unreachable_firefly_gives_clear_message(firefly, mcp_client):
    firefly.exc = httpx.ConnectError("dns failure for internal-host.lan")

    result = await mcp_client.call_tool("get_account", {"id": "1"}, raise_on_error=False)

    text = result.content[0].text
    assert result.is_error
    assert "Could not reach Firefly III" in text
    assert "internal-host.lan" not in text


async def test_unexpected_errors_are_masked(firefly, mcp_client):
    firefly.exc = RuntimeError("secret internal detail")

    result = await mcp_client.call_tool("get_account", {"id": "1"}, raise_on_error=False)

    assert result.is_error
    assert "secret internal detail" not in result.content[0].text


async def test_shared_secret_accepts_only_the_configured_token():
    verifier = SharedSecretVerifier("s3cret-value")

    assert await verifier.verify_token("s3cret-value") is not None
    assert await verifier.verify_token("wrong") is None


def test_http_endpoint_requires_the_shared_secret():
    server = FastMCP("t", auth=SharedSecretVerifier("s3cret-value"))

    @server.custom_route("/health", methods=["GET"])
    async def health(_request):
        from starlette.responses import JSONResponse

        return JSONResponse({"status": "ok"})

    with TestClient(server.http_app()) as http:
        assert http.post("/mcp", json={}).status_code == 401
        assert http.get("/health").status_code == 200
        authed = http.post("/mcp", json={}, headers={"Authorization": "Bearer s3cret-value"})
        assert authed.status_code != 401
