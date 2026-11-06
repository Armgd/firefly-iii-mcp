import ssl

import pytest
from key_value.aio.stores.memory import MemoryStore

from firefly_mcp import auth
from firefly_mcp.auth import FireflyOAuthProxy, FireflyTokenVerifier
from firefly_mcp.client import ssl_verify


@pytest.mark.parametrize(("raw", "expected"), [("true", True), ("false", False), ("0", False)])
def test_verify_flag(monkeypatch, raw, expected):
    monkeypatch.setenv("FIREFLY_III_VERIFY_SSL", raw)

    assert ssl_verify() is expected


def test_verify_defaults_to_on(monkeypatch):
    monkeypatch.delenv("FIREFLY_III_VERIFY_SSL", raising=False)

    assert ssl_verify() is True


def test_ca_file_is_trusted(monkeypatch):
    import certifi

    monkeypatch.setenv("FIREFLY_III_VERIFY_SSL", certifi.where())

    context = ssl_verify()
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED


def test_missing_ca_file_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("FIREFLY_III_VERIFY_SSL", str(tmp_path / "nope.pem"))

    with pytest.raises(RuntimeError, match="nope.pem"):
        ssl_verify()


def test_login_exchange_uses_the_same_tls_setting(monkeypatch):
    seen = {}

    class RecordingClient:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    monkeypatch.setattr(auth.httpx2, "AsyncClient", RecordingClient)
    proxy = FireflyOAuthProxy(
        verify=False,
        upstream_authorization_endpoint="https://firefly.test/oauth/authorize",
        upstream_token_endpoint="https://firefly.test/oauth/token",
        upstream_client_id="9",
        upstream_client_secret="client-secret",
        token_verifier=FireflyTokenVerifier(),
        base_url="http://localhost:8000",
        client_storage=MemoryStore(),
    )

    client = proxy._create_upstream_oauth_client()

    assert seen["verify"] is False
    assert isinstance(client._client, RecordingClient)
