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
- Optional self-signed-cert support via `FIREFLY_III_VERIFY_SSL=false`.

## Requirements

- Python **3.12+** (the Docker image ships 3.13)
- A running Firefly III instance
- A Firefly III Personal Access Token

## Configuration

Copy `.env.example` to `.env` and fill in:

```dotenv
FIREFLY_III_URL=https://your-firefly-iii-instance.example.com
FIREFLY_III_ACCESS_TOKEN=your_personal_access_token
# FIREFLY_III_VERIFY_SSL=false   # only if your instance uses a self-signed cert
```

## Running

### Local (uv)

```bash
uv venv && uv sync
fastmcp dev main.py                                       # dev mode (auto-reload + MCP inspector)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4   # production-like
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
# {"status":"ok","service":"Firefly III MCP"}
```

## Development

```bash
ruff check .
ruff format .
```

See [`CLAUDE.md`](./CLAUDE.md) for architecture notes and contribution guidelines.
