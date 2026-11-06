# Firefly III OAuth auth layer for the MCP server

**Date:** 2026-05-06
**Status:** approved (pending implementation plan)
**Author:** brainstormed with @nicolas.gras

## Goal

Add an OAuth 2.1 authentication layer in front of the Firefly III MCP server, with **Firefly III as the identity provider**. MCP clients authenticate against Firefly via FastMCP's `OAuthProxy`, and the MCP server uses each user's Firefly token to call the Firefly API on their behalf. This enables **multi-user** deployments without leaking any single user's Personal Access Token to other users.

The current behavior (single shared `FIREFLY_III_ACCESS_TOKEN` env var) remains supported as a separate, equally-first-class mode for solo `uvx`-style deployments — it is not deprecated.

## Non-goals

- Per-tool OAuth scopes (any valid Firefly token = full MCP access in this version).
- A `MultiAuth` PAT-fallback alongside OAuth (rejected as a footgun in multi-user mode).
- `client_credentials`-grant single-identity OAuth (defeats the multi-user goal).
- Token-exchange (RFC 8693) for downstream-non-Firefly APIs (we only call Firefly).
- Retrofitting tests for the existing 16 tool modules.
- Any deployment-process automation (Docker image, k8s manifests, Caddyfile snippets).

## Modes

The server runs in exactly **one** of two modes, fixed at startup, never switched at runtime.

| Mode | Activated by | FastMCP `auth=` provider | Firefly token used per call | Typical deployment |
|---|---|---|---|---|
| **PAT** (today's behavior, unchanged) | `FIREFLY_III_ACCESS_TOKEN` | none | the env PAT | local stdio (`uvx`), or LAN HTTP for solo |
| **OAuth** (new) | `FIREFLY_III_OAUTH_CLIENT_ID` + `_SECRET` + `MCP_BASE_URL` | `OAuthProxy` pointed at Firefly's `/oauth/authorize` and `/oauth/token` | the per-request user's Firefly token (from `fastmcp.dependencies.get_access_token()`) | local HTTP single-user, or remote HTTPS multi-user |

OAuth mode is further classified at startup as **local** (`MCP_BASE_URL` host is `localhost` / `127.0.0.1` / `[::1]`) or **remote** (anything else), which gates whether the JWT-signing/storage-encryption keys are required.

### Mode resolution rules (all enforced at server import; all loud)

OAuth mode is **triggered** by either `FIREFLY_III_OAUTH_CLIENT_ID` or `FIREFLY_III_OAUTH_CLIENT_SECRET` being set in the environment. `MCP_BASE_URL` alone does **not** trigger OAuth mode — it is ignored if no OAuth-specific var is set, allowing PAT-mode operators to leave it in their env without consequence.

| Condition | Behavior |
|---|---|
| `FIREFLY_III_ACCESS_TOKEN` set AND any of (`OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`) set | `RuntimeError`: PAT and OAuth modes are mutually exclusive. |
| Neither PAT nor any OAuth-trigger var set | `RuntimeError` listing the two valid env shapes. |
| OAuth triggered but partial (missing client_id, client_secret, or `MCP_BASE_URL`) | `RuntimeError` listing exactly which keys are missing. |
| `MCP_BASE_URL` set without any OAuth-trigger var | Ignored. PAT mode still applies. |
| `MCP_BASE_URL` malformed (no scheme, or unparseable) when OAuth triggered | `RuntimeError`. |
| Remote OAuth without `FIREFLY_III_OAUTH_JWT_SIGNING_KEY` | `RuntimeError`. |
| Remote OAuth without `FIREFLY_III_OAUTH_STORAGE_ENCRYPTION_KEY` | `RuntimeError`. |
| Local OAuth without those keys | OK — `OAuthProxy` defaults are acceptable for solo. |
| Public `http://` (non-loopback) `MCP_BASE_URL` | `RuntimeWarning` at startup. Don't refuse to start (LAN/dev flexibility). |

Firefly URL unreachability is **not** a startup error — lazy, surfaces on first request. Same as today.

## Architecture & file layout

### New files

- **`firefly_mcp/auth.py`** (~150 lines, single file, no cross-cutting deps)
  - `AuthMode` — frozen dataclass discriminated union: `PatMode(token: str)` | `OAuthMode(client_id, client_secret, mcp_base_url, firefly_url, deployment: Literal["local","remote"], jwt_signing_key, storage_encryption_key, redis_url, validation_ttl_s, allowed_redirect_uris)`.
  - `resolve_auth_mode() -> AuthMode` — pure function over `os.environ`, raises with clear messages on misconfiguration.
  - `build_auth_provider(mode: AuthMode) -> AuthProvider | None` — returns an `OAuthProxy` for `OAuthMode`, `None` for `PatMode`.
  - `get_current_token() -> str` — the abstraction the request helper depends on. PAT mode: returns the env token. OAuth mode: reads `fastmcp.server.dependencies.get_access_token().token`. Single touch point for the rest of the codebase.
  - `FireflyTokenVerifier` — custom `TokenVerifier` subclass with TTL+single-flight cache, validating against `GET /api/v1/about/user`.

- **`tests/test_auth.py`**, **`tests/test_token_verifier.py`**, **`tests/test_request_integration.py`**, **`tests/test_server.py`** — first test files in the repo.

- **`docs/oauth-setup.md`** — operator runbook for OAuth modes (created only if README section exceeds ~40 lines; otherwise inline in README).

### Modified files

- **`firefly_mcp/client.py`** — surgical refactor:
  - `get_client()` returns an `httpx.AsyncClient` with **no** `Authorization` header (only `Accept`, `Content-Type`, base URL, timeout, `verify`). Connection pool is still process-wide cached via `lru_cache`.
  - `request()` calls `get_current_token()` and merges `Authorization: Bearer <token>` into the per-call request headers.
  - Net effect: same connection-reuse efficiency, but the token is per-call, not per-client.
- **`firefly_mcp/server.py`** — three changes:
  - Import `resolve_auth_mode` and `build_auth_provider`.
  - Call them once at module load.
  - Pass the optional provider to `FastMCP(auth=...)`.
  - Tool registration, prompts, `app = mcp.http_app()` all unchanged.
  - `/health` extended to include `"auth_mode": "pat"|"oauth"`.
  - One log line at startup: `[firefly-mcp] auth mode: <mode> (issuer=..., callback=...)`.
- **`.env.example`** — add OAuth block with comments documenting mutual exclusivity.
- **`pyproject.toml`** — verify `fastmcp>=3.0.0` includes `OAuthProxy` (it does) and add dev deps (`pytest`, `pytest-asyncio`, `respx`).
- **`CLAUDE.md`** — short addition documenting the two modes, env vars, and how to switch.
- **`README.md`** — split deployment recipes into "Mode 1: stdio/PAT", "Mode 2: local HTTP/OAuth", "Mode 3: remote HTTP/OAuth".
- **`.github/workflows/`** — new workflow `03-test.yaml` running `pytest --cov`.

### Untouched

- All 16 tool modules in `firefly_mcp/tools/` — `request()` signature unchanged. **Tool-module diff = 0 lines.**
- `main.py` — still 5 lines.
- `firefly_mcp/prompts/`.
- `Dockerfile` — env vars are runtime, no image change.

## Request flow

### Initial OAuth handshake (once per MCP-client session, OAuth mode)

```
MCP client                OAuthProxy (FastMCP)             Firefly III
    │  GET /mcp (no auth)        │                              │
    ├───────────────────────────►│                              │
    │  401 + resource_metadata   │                              │
    │◄───────────────────────────┤                              │
    │  POST /register (DCR)      │                              │
    ├───────────────────────────►│  (proxy fakes DCR)           │
    │◄───────────────────────────┤                              │
    │  GET /authorize            │                              │
    ├───────────────────────────►│  consent screen (built-in)   │
    │  user approves             │                              │
    │                            │  302 to Firefly /authorize   │
    │                            ├─────────────────────────────►│
    │  user logs in, consents    │                              │
    │                            │  302 to /auth/callback       │
    │                            │◄─────────────────────────────┤
    │                            │  POST /oauth/token (code)    │
    │                            ├─────────────────────────────►│
    │                            │  upstream tokens             │
    │                            │◄─────────────────────────────┤
    │  302 to client redirect    │                              │
    │◄───────────────────────────┤                              │
    │  POST /token (code)        │                              │
    ├───────────────────────────►│                              │
    │  FastMCP-issued JWT        │                              │
    │◄───────────────────────────┤                              │
```

The MCP client receives a **FastMCP-issued JWT**, not the upstream Firefly token. The upstream token is encrypted and stored server-side (linked by JTI), and is retrieved inside tool functions via `get_access_token()`. This is the documented [token factory pattern](https://gofastmcp.com/servers/auth/oauth-proxy#token-architecture).

Dual PKCE (`forward_pkce=True`, default): client↔proxy leg and proxy↔Firefly leg each use their own PKCE pair. End-to-end PKCE security at both layers.

### Authenticated tool call (every subsequent request)

```
MCP client → MCP server: POST /mcp  Authorization: Bearer <FASTMCP_JWT>
   │
   ├─ FastMCP auth middleware:
   │     1. Validates <FASTMCP_JWT> signature/expiry/issuer/audience  (built-in)
   │     2. Extracts JTI, looks up encrypted upstream Firefly token
   │     3. Decrypts upstream Firefly token <FF_TOKEN>
   │     4. Calls FireflyTokenVerifier with <FF_TOKEN>:
   │           ├─ SHA-256(<FF_TOKEN>) lookup in TTL cache
   │           ├─ HIT (valid) → return AccessToken
   │           └─ MISS → GET Firefly /api/v1/about/user with Bearer <FF_TOKEN>
   │                 ├─ 200 → cache valid (60s default), return AccessToken
   │                 ├─ 401 → cache invalid (5s), return None         → 401 to client
   │                 └─ network err → return None, no cache write     → 401 to client
   │
   ├─ Tool handler runs: list_accounts(...)
   │     └─ await request("GET", "/v1/accounts")
   │           └─ get_current_token():
   │                 ├─ PAT mode  → os.environ["FIREFLY_III_ACCESS_TOKEN"]
   │                 └─ OAuth mode → fastmcp.dependencies.get_access_token().token  ← <FF_TOKEN>
   │           └─ httpx call to Firefly with that token in headers
   │
   └─ Firefly response → tool handler → MCP response
```

This is **not** token passthrough in the security-anti-pattern sense: the MCP server calls Firefly with the user's Firefly token, and Firefly is the same audience that issued the token. Token passthrough warnings in the FastMCP docs apply to forwarding to a *different* downstream service.

### Token validation cache (`FireflyTokenVerifier`)

- **Key:** `sha256(token).hexdigest()`. Raw tokens never persisted to the cache.
- **Valid TTL:** `FIREFLY_III_OAUTH_VALIDATION_TTL` env, default `60` seconds.
- **Invalid TTL:** `5` seconds (limits revocation latency while absorbing retry bursts).
- **Network error TTL:** none (next call retries, no negative caching of transient failures).
- **Single-flight:** `asyncio.Lock` keyed by token hash. Concurrent verifications of the same token coalesce into one Firefly call.
- **Clock injection:** the cache takes a `clock: Callable[[], float]` parameter defaulting to `time.monotonic` for testability without `freezegun`.

### Refresh & expiry

The MCP client refreshes its FastMCP JWT against `OAuthProxy`. The proxy refreshes the upstream Firefly token internally and re-issues a new FastMCP JWT. The MCP server does **not** track refresh tokens directly. When Firefly's token expires for real, `/api/v1/about/user` returns 401 → verifier returns `None` → MCP returns 401 → client refreshes & retries. End-user transparent.

## Error handling

| Situation | Behavior |
|---|---|
| Misconfiguration at startup | Loud `RuntimeError` from `resolve_auth_mode()`. |
| Invalid/revoked/expired token at validation | `verify_token` returns `None` → 401 to client → client refreshes/retries. |
| Token cached valid but Firefly rejects on a real call | Surfaces as `FireflyAPIError(401, ...)`. Cache entry TTLs out within 60 s. Acceptable per cache trade-off. |
| Firefly down during validation | `verify_token` returns `None`, no cache write. 401 to client. (We don't expose 503 because we can't distinguish "your token is bad" from "Firefly down" without leaking info.) |
| Firefly down during a tool call | `httpx` raises; not currently caught in `request()`. Same as today, no regression. Out of scope. |
| `OAuthProxy` callback failure | Handled by `OAuthProxy` per OAuth spec. |
| `FIREFLY_III_VERIFY_SSL=false` set | Applies to **all** httpx clients (Firefly API + OAuth backchannel + validation). Single source of truth, documented. |

## Security

- **Tokens in memory:** held inside the FastMCP request context for the duration of one call. Validation cache stores only `sha256(token)` keys.
- **Logging:** never include raw tokens, refresh tokens, or auth codes. Verifier and cache log only token-hash 8-char prefixes.
- **TLS for HTTP modes:** non-loopback `MCP_BASE_URL` must be `https://`. Public `http://` triggers a `RuntimeWarning`.
- **PKCE:** dual via `forward_pkce=True` (default).
- **Redirect URI:** operator registers exactly `<MCP_BASE_URL>/auth/callback` in Firefly's OAuth Client. Strict matching at both ends. Optionally pin via `FIREFLY_III_OAUTH_ALLOWED_REDIRECT_URIS` (comma-separated patterns).
- **Consent screen:** `require_authorization_consent=True` (default). First time a given MCP client authorizes, user sees a FastMCP consent page. Approval signed-cookie-bound to defeat confused-deputy attacks.
- **Confused deputy:** prevented at two layers — the consent screen itself, and the consent-binding cookie that links the approving browser to the eventual callback.
- **Mode confusion:** prevented by mode being one-shot at startup. There is no code path that reaches the env PAT in OAuth mode.

### JWT signing key & client storage

`OAuthProxy` issues its own JWTs and stores upstream tokens encrypted at rest. The keys + storage backend matter:

| Deployment | `FIREFLY_III_OAUTH_JWT_SIGNING_KEY` | `FIREFLY_III_OAUTH_STORAGE_ENCRYPTION_KEY` | Storage backend |
|---|---|---|---|
| Local HTTP, single user | optional | optional | `OAuthProxy` default (encrypted disk on Mac/Win, in-memory on Linux) |
| Remote HTTP, multi-user | **required** | **required** | Redis via `FIREFLY_III_OAUTH_REDIS_URL`, wrapped in `FernetEncryptionWrapper` |

Generation recipes:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'                    # JWT signing key
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'  # storage encryption key
```

Without an explicit `JWT_SIGNING_KEY`, `OAuthProxy` derives one from the upstream client secret — meaning rotating the client secret invalidates all existing OAuth client registrations. Setting it explicitly decouples the two.

## Operator setup

### Mode 1 — Local stdio / `uvx` / PAT (unchanged)

Firefly: Profile → OAuth → **Personal Access Tokens** → New Token.

```ini
FIREFLY_III_URL=https://your-firefly.example.com
FIREFLY_III_ACCESS_TOKEN=eyJ0eXAiOi...
```

```bash
uvx firefly-mcp                                      # stdio, spawned by Claude Desktop
uvicorn main:app --host 127.0.0.1 --port 8000        # HTTP, no auth layer
```

Claude Desktop config: `{"mcpServers":{"firefly-iii":{"command":"uvx","args":["firefly-mcp"],"env":{...}}}}`.

### Mode 2 — Local HTTP, OAuth, single user

Firefly: Profile → OAuth → **OAuth Clients** → New OAuth Client.
- Name: `Firefly MCP (local)`
- Redirect URL: `http://localhost:8000/auth/callback`
- Confidential: **yes**

```ini
FIREFLY_III_URL=https://your-firefly.example.com
FIREFLY_III_OAUTH_CLIENT_ID=9
FIREFLY_III_OAUTH_CLIENT_SECRET=Ld5...
MCP_BASE_URL=http://localhost:8000
# Optional: FIREFLY_III_OAUTH_VALIDATION_TTL=60
```

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

Startup log (operator can verify mode at a glance):

```
[firefly-mcp] auth mode: oauth (issuer=https://your-firefly.example.com, callback=http://localhost:8000/auth/callback)
```

MCP client config (HTTP transport):

```json
{ "mcpServers": { "firefly-iii": { "url": "http://localhost:8000/mcp" } } }
```

Client triggers OAuth flow on first connect → browser opens → user logs into Firefly → consent → done.

### Mode 3 — Remote HTTP, OAuth, multi-user

Prereqs: public DNS + TLS terminator, Redis instance with persistence, Firefly III reachable from the MCP server.

Firefly: same as Mode 2 but Redirect URL is `https://mcp.example.com/auth/callback`.

```ini
FIREFLY_III_URL=https://your-firefly.example.com
FIREFLY_III_OAUTH_CLIENT_ID=9
FIREFLY_III_OAUTH_CLIENT_SECRET=Ld5...
MCP_BASE_URL=https://mcp.example.com

# Required for remote (loud startup error if missing):
FIREFLY_III_OAUTH_JWT_SIGNING_KEY=<secrets.token_urlsafe(48)>
FIREFLY_III_OAUTH_STORAGE_ENCRYPTION_KEY=<Fernet.generate_key()>
FIREFLY_III_OAUTH_REDIS_URL=redis://redis.internal:6379/0

# Optional:
# FIREFLY_III_OAUTH_VALIDATION_TTL=60
# FIREFLY_III_OAUTH_ALLOWED_REDIRECT_URIS=https://claude.ai/api/mcp/auth_callback,http://localhost:*
```

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Behind the operator's reverse proxy terminating TLS on `mcp.example.com:443 → 127.0.0.1:8000`.

### Migration: PAT → OAuth

1. Register the OAuth Client in Firefly (steps above).
2. **Remove** `FIREFLY_III_ACCESS_TOKEN` from env. Setting both is a startup error — the safety net.
3. Add OAuth env vars + `MCP_BASE_URL`.
4. Restart server. Startup log confirms `auth mode: oauth`.
5. (Mode 3 only) Generate signing/encryption keys, point at Redis.
6. Reconnect MCP clients — they re-authenticate.
7. Revoke the old PAT in Firefly's UI once verified.

### Operability

- **Mode visibility:** startup log line + `/health` returns `{"status":"ok","service":"...","auth_mode":"pat"|"oauth"}`. No secrets exposed.
- **JWT signing key rotation:** invalidates all FastMCP JWTs → users re-auth. Documented consequence.
- **Client secret rotation:** rotate in Firefly + env, restart. With explicit `JWT_SIGNING_KEY`, OAuth client registrations survive the rotation.
- **Multi-worker validation cache:** per-worker. Worst case `N_WORKERS × 1` Firefly validation calls per token until each warms its cache. Bounded; acceptable.
- **Multi-worker `OAuthProxy` storage:** Redis (Mode 3) is shared. Mode 2 default storage is per-host, fine for single-machine workers.

## Testing strategy

First test suite in this repo. Narrowly scoped to new code; existing tool modules are transparently exercised by the integration test below.

### Suites

- **`tests/test_auth.py`** — `resolve_auth_mode()` env-var permutations (PAT-only, OAuth-full, both, neither, partial, malformed `MCP_BASE_URL`, remote without keys, local without keys, localhost vs non-localhost), `get_current_token()` PAT path, OAuth path with mocked context, OAuth path outside a request → clear error.
- **`tests/test_token_verifier.py`** — cache miss/hit valid/hit invalid, valid TTL expiry, invalid TTL expiry, single-flight (10 concurrent verifies = 1 Firefly call), key is `sha256(token)` not raw, network error → no cache write.
- **`tests/test_request_integration.py`** — `respx`-stubbed Firefly. PAT mode `request()` outgoing has Bearer of env PAT. OAuth mode (patched `get_access_token`) outgoing has Bearer of user token. Indirect coverage of the 16 tool modules.
- **`tests/test_server.py`** — module import in PAT mode → no `auth` attached. Import in OAuth mode → `OAuthProxy` attached with `redirect_path="/auth/callback"`. `/health` returns `auth_mode` field.

### Tooling

- `pytest` + `pytest-asyncio`.
- `respx` for HTTP stubbing.
- Manual clock injection via a `clock` parameter on the cache (more robust than `freezegun` with `monotonic`).
- One autouse `clear_firefly_env` fixture wiping the entire `FIREFLY_III_*` + `MCP_BASE_URL` namespace per test.

### Coverage target

`pytest --cov=firefly_mcp.auth --cov=firefly_mcp.client --cov-fail-under=80`. **80% line coverage on new code only.** Existing tool modules out of denominator.

### CI

New workflow `03-test.yaml` running `pytest --cov` on push/PR. Mirrors the structure of the existing `00-lint.yaml`.

## Open questions / impl-time decisions

- **Firefly token endpoint auth method:** `client_secret_basic` (the `OAuthProxy` default and Passport's standard). Verify at impl time; if Passport pushes back, override via `FIREFLY_III_OAUTH_TOKEN_ENDPOINT_AUTH_METHOD`.
- **Extra authorize/token params:** none expected for vanilla Passport. Verify; add `extra_authorize_params={"audience": ...}` only if tokens come back unusable against `/api/v1/about/user`.
- **Where does `oauth-setup.md` end up?** If the README OAuth section grows past ~40 lines, split it into `docs/oauth-setup.md` and link from README. Otherwise inline.

## Out of scope (explicit)

- Per-tool scope enforcement.
- `MultiAuth` PAT-fallback alongside OAuth.
- `client_credentials` grant.
- Token-exchange (RFC 8693) for non-Firefly downstream APIs.
- Retrofitting tests for the 16 tool modules.
- Caching of Firefly-side rate limits in the MCP layer.
- Distributed validation cache (per-worker is fine).
- Any deployment-process automation (Docker images, k8s manifests, Caddyfile snippets).

## Appendix: env-var matrix

| Var | Mode 1 (PAT) | Mode 2 (local OAuth) | Mode 3 (remote OAuth) |
|---|---|---|---|
| `FIREFLY_III_URL` | required | required | required |
| `FIREFLY_III_ACCESS_TOKEN` | required | **must not be set** | **must not be set** |
| `FIREFLY_III_OAUTH_CLIENT_ID` | must not be set | required | required |
| `FIREFLY_III_OAUTH_CLIENT_SECRET` | must not be set | required | required |
| `MCP_BASE_URL` | ignored | required (`http://localhost:PORT`) | required (`https://...`) |
| `FIREFLY_III_VERIFY_SSL` | optional | optional | optional |
| `FIREFLY_III_OAUTH_VALIDATION_TTL` | n/a | optional (default 60) | optional (default 60) |
| `FIREFLY_III_OAUTH_JWT_SIGNING_KEY` | n/a | optional | **required** |
| `FIREFLY_III_OAUTH_STORAGE_ENCRYPTION_KEY` | n/a | optional | **required** |
| `FIREFLY_III_OAUTH_REDIS_URL` | n/a | optional | **required** |
| `FIREFLY_III_OAUTH_ALLOWED_REDIRECT_URIS` | n/a | optional | optional |
| `FIREFLY_III_OAUTH_TOKEN_ENDPOINT_AUTH_METHOD` | n/a | optional escape hatch | optional escape hatch |
