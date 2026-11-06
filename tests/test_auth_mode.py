import pytest

from firefly_mcp.auth import OAuthMode, PatMode, resolve_auth_mode

SECRET = "x" * 32
OAUTH = {
    "FIREFLY_III_URL": "https://firefly.test",
    "FIREFLY_III_OAUTH_CLIENT_ID": "9",
    "FIREFLY_III_OAUTH_CLIENT_SECRET": "client-secret",
    "MCP_BASE_URL": "http://localhost:8000",
}
REMOTE = {
    **OAUTH,
    "MCP_BASE_URL": "https://mcp.example.com",
    "FIREFLY_III_OAUTH_JWT_SIGNING_KEY": "jwt-signing-key-long-enough",
}


def test_pat_mode_with_optional_shared_secret():
    mode = resolve_auth_mode({"FIREFLY_III_ACCESS_TOKEN": "pat", "MCP_AUTH_TOKEN": SECRET})

    assert mode == PatMode(token="pat", shared_secret=SECRET)


def test_short_shared_secret_is_refused():
    with pytest.raises(RuntimeError, match="at least 32"):
        resolve_auth_mode({"FIREFLY_III_ACCESS_TOKEN": "pat", "MCP_AUTH_TOKEN": "short"})


def test_mcp_base_url_alone_keeps_pat_mode():
    mode = resolve_auth_mode({"FIREFLY_III_ACCESS_TOKEN": "pat", "MCP_BASE_URL": "nonsense"})

    assert isinstance(mode, PatMode)


def test_local_oauth_needs_no_keys():
    mode = resolve_auth_mode(OAUTH)

    assert isinstance(mode, OAuthMode)
    assert not mode.is_remote
    assert mode.callback_url == "http://localhost:8000/auth/callback"


def test_remote_oauth_without_redis_is_allowed():
    mode = resolve_auth_mode(REMOTE)

    assert mode.is_remote
    assert mode.redis_url is None


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({}, "FIREFLY_III_ACCESS_TOKEN"),
        ({**OAUTH, "FIREFLY_III_ACCESS_TOKEN": "pat"}, "mutually exclusive"),
        ({**OAUTH, "MCP_AUTH_TOKEN": SECRET}, "MCP_AUTH_TOKEN"),
        ({"FIREFLY_III_OAUTH_CLIENT_ID": "9"}, "FIREFLY_III_OAUTH_CLIENT_SECRET, MCP_BASE_URL"),
        ({**OAUTH, "MCP_BASE_URL": "localhost:8000"}, "MCP_BASE_URL"),
        ({**OAUTH, "MCP_BASE_URL": "https://mcp.example.com"}, "JWT_SIGNING_KEY"),
        (
            {**REMOTE, "FIREFLY_III_OAUTH_REDIS_URL": "redis://r:6379/0"},
            "STORAGE_ENCRYPTION_KEY",
        ),
    ],
)
def test_misconfiguration_fails_loudly(env, message):
    with pytest.raises(RuntimeError, match=message):
        resolve_auth_mode(env)
