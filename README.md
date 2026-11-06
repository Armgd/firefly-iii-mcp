# Firefly III MCP Server

A Model Context Protocol (MCP) server that exposes a curated subset of the
[Firefly III](https://www.firefly-iii.org/) personal-finance REST API to
MCP-compatible clients (Claude, etc.).

## Features

- **MCP server** built on [`fastmcp`](https://github.com/jlowin/fastmcp).
- ~160 explicit `@mcp.tool` handlers covering accounts, transactions, budgets
  (+ limits), bills, piggy banks, categories, tags, attachments, object groups,
  rules and rule groups, recurrences, currencies and exchange rates,
  autocomplete lookups, and pre-aggregated insight summaries.
- Single shared async `httpx` client with consistent error handling
  (`FireflyAPIError` preserves Firefly's `message`/`errors` fields).
- Self-signed / private-CA Firefly III support via `FIREFLY_III_VERIFY_SSL` (CA file path or `false`).
- Every tool tells the client whether it only reads, changes, or deletes data,
  so clients can auto-approve reads and ask before destructive calls.
- Optional shared secret (`MCP_AUTH_TOKEN`) protecting the HTTP endpoint.
- Optional OAuth mode: users sign in with their own Firefly III account (multi-user).

## Requirements

- Python **3.12+** (the Docker image ships 3.13)
- A running Firefly III instance, **v6.7 or later** (tools target the v6.7.8 API).
  Upgrading to 6.6+ invalidates existing OAuth tokens: create a new Personal Access Token.
- A Firefly III Personal Access Token, or a Firefly III OAuth Client (OAuth mode)

## Configuration

Copy `.env.example` to `.env` and fill in:

```dotenv
FIREFLY_III_URL=https://your-firefly-iii-instance.example.com
FIREFLY_III_ACCESS_TOKEN=your_personal_access_token
# FIREFLY_III_VERIFY_SSL=/certs/firefly-ca.pem   # self-signed/private CA (or `false`)
MCP_AUTH_TOKEN=                    # openssl rand -hex 32
```

### Securing the HTTP endpoint

The server holds a Firefly token with full read/write access, so anyone who can
reach its port can read and change your finances. Set `MCP_AUTH_TOKEN` (32+
characters) and configure clients to send `Authorization: Bearer <MCP_AUTH_TOKEN>`.
Without it the server logs a warning at startup and accepts every request; only
do that when the port is reachable from a trusted machine alone. `/health`
stays public. This secret is never forwarded to Firefly III.

### Self-signed Firefly III

Point `FIREFLY_III_VERIFY_SSL` at the CA (or the self-signed certificate itself)
in PEM format: connections stay verified, against that CA only. `false` turns
verification off entirely and should be a last resort. The setting covers every
call the server makes to Firefly III, including the OAuth sign-in exchange. The
browser-side sign-in page is your browser's business: trust the CA there too.

### OAuth mode (users sign in with Firefly III)

Instead of one shared token, each MCP user signs in to Firefly III in their
browser and every tool call runs with that user's own Firefly permissions.

1. In Firefly III: Profile → OAuth → **OAuth Clients** → Create, confidential,
   redirect URL `<MCP_BASE_URL>/auth/callback`
   (e.g. `http://localhost:8000/auth/callback`).
2. Configure (and remove `FIREFLY_III_ACCESS_TOKEN` and `MCP_AUTH_TOKEN`: mixing
   modes is a startup error):

   ```dotenv
   FIREFLY_III_URL=https://your-firefly-iii-instance.example.com
   FIREFLY_III_OAUTH_CLIENT_ID=9
   FIREFLY_III_OAUTH_CLIENT_SECRET=...
   MCP_BASE_URL=http://localhost:8000
   ```

3. Point the MCP client at `<MCP_BASE_URL>/mcp`; it opens the Firefly sign-in
   page on first connect.

When `MCP_BASE_URL` is not `localhost`, also set
`FIREFLY_III_OAUTH_JWT_SIGNING_KEY` (`openssl rand -hex 32`) and serve it over
HTTPS. Sign-ins are stored encrypted on disk under `FASTMCP_HOME` (mount a
volume there in Docker so they survive restarts), which suits one worker. To run
several workers or replicas, share them through Redis:

```dotenv
FIREFLY_III_OAUTH_REDIS_URL=redis://redis:6379/0
FIREFLY_III_OAUTH_STORAGE_ENCRYPTION_KEY=...   # python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Locally, install Redis support with `uv sync --extra redis` (the Docker image
includes it). Optional knobs: `FIREFLY_III_OAUTH_VALIDATION_TTL` (seconds a
user's token is trusted before Firefly is asked again, default 60),
`FIREFLY_III_OAUTH_ALLOWED_REDIRECT_URIS` (comma-separated client redirect
patterns), `FIREFLY_III_OAUTH_TOKEN_ENDPOINT_AUTH_METHOD`
(`client_secret_post` if Firefly rejects the default).

## Running

### Local (uv)

```bash
uv venv && uv sync
fastmcp dev main.py                                       # dev mode (auto-reload + MCP inspector)
uvicorn main:app --host 0.0.0.0 --port 8000                # production-like
```

### Docker

```bash
docker build -t firefly-mcp .
docker run --rm -p 8000:8000 --env-file .env firefly-mcp
```

For non-native architectures (e.g. building `amd64` from an Apple Silicon host):

```bash
docker build --platform=linux/amd64 -t firefly-mcp .
```

The container runs as a non-root `app` user and ships a `HEALTHCHECK` that
polls `GET /health`.

## Health check

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"Firefly III MCP","auth_mode":"pat"}
```

## Development

```bash
ruff check .
ruff format .
```

See [`CLAUDE.md`](./CLAUDE.md) for architecture notes and contribution guidelines.
