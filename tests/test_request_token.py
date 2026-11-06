import pytest
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken
from starlette.testclient import TestClient

from firefly_mcp import client as firefly_client
from firefly_mcp.server import app

pytestmark = pytest.mark.anyio


async def test_pat_mode_sends_the_env_token(firefly):
    await firefly_client.request("GET", "/v1/about")

    assert firefly.last.headers["Authorization"] == "Bearer test-pat"


async def test_oauth_mode_sends_the_signed_in_users_token(firefly, monkeypatch):
    monkeypatch.delenv("FIREFLY_III_ACCESS_TOKEN")
    user = AccessToken(token="user-token", client_id="c", scopes=[])
    monkeypatch.setattr(firefly_client, "get_access_token", lambda: user)

    await firefly_client.request("GET", "/v1/about")

    assert firefly.last.headers["Authorization"] == "Bearer user-token"


async def test_oauth_mode_without_signed_in_user_fails(firefly, monkeypatch):
    monkeypatch.delenv("FIREFLY_III_ACCESS_TOKEN")
    monkeypatch.setattr(firefly_client, "get_access_token", lambda: None)

    with pytest.raises(ToolError, match="signed in"):
        await firefly_client.request("GET", "/v1/about")
    assert firefly.calls == []


def test_health_reports_the_auth_mode():
    with TestClient(app) as http:
        assert http.get("/health").json()["auth_mode"] == "pat"
