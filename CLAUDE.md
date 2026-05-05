# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Model Context Protocol (MCP) server that exposes a curated subset of the [Firefly III](https://www.firefly-iii.org/) personal finance REST API to MCP-compatible clients (Claude, etc.). Implemented as explicit `@mcp.tool`-decorated handlers (one Python module per Firefly domain) backed by a single shared async HTTP client. ~160 tools covering accounts, transactions, budgets (+ limits), bills, piggy banks, categories, tags, attachments, object groups, rules and rule groups, recurrences, currencies and exchange rates, autocomplete lookups, and pre-aggregated insight summaries.

## Commands

Dependency management uses **uv** (Python 3.12+).

```bash
uv venv && uv sync          # create venv + install deps
uv sync --frozen --no-dev   # production install (matches Dockerfile)
uv lock                     # regenerate lockfile after editing pyproject.toml
```

Run the server:

```bash
# Dev (auto-reload, MCP inspector)
fastmcp dev main.py

# Production-like (matches Dockerfile CMD)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Docker
docker compose up -d
```

Required env vars (see `.env.example`, loaded via `python-dotenv`):
- `FIREFLY_III_URL` — base URL of the Firefly III instance
- `FIREFLY_III_ACCESS_TOKEN` — Personal Access Token (sent as `Authorization: Bearer ...`)

Lint/format: `ruff check .` / `ruff format .` (ruff is the only dev dep).

Health check: `GET /health` → `{"status": "ok", "service": "Firefly III MCP"}`.

No test suite exists yet.

## Architecture

`main.py` is now a 5-line ASGI entry point that re-exports `app` and `mcp` from `firefly_mcp.server`. Everything substantive lives under the **`firefly_mcp/`** package:

```
firefly_mcp/
├── __init__.py        # __version__ (semantic-release also updates this)
├── client.py          # lazy httpx.AsyncClient + request() helper + FireflyAPIError
├── server.py          # FastMCP() instance, registers all tool modules, /health, prompts, app
└── tools/
    ├── system.py         # get_about
    ├── accounts.py       # accounts CRUD + list_account_{attachments,piggy_banks,transactions}
    ├── transactions.py   # list/get/search/create/create_split/update/delete + attachments + piggy events
    ├── budgets.py        # budgets CRUD + budget limits + transaction views
    ├── bills.py          # bills CRUD + linked rules / attachments / transactions
    ├── piggy_banks.py    # piggy banks CRUD + attachments + events
    ├── categories.py     # categories CRUD + attachments + transactions
    ├── tags.py           # tags CRUD (by name or ID) + attachments + transactions
    ├── attachments.py    # list/get/delete metadata only
    ├── object_groups.py  # list/get
    ├── rules.py          # rules CRUD + test/trigger
    ├── rule_groups.py    # rule groups CRUD + list/test/trigger
    ├── recurrences.py    # recurring-tx templates CRUD + trigger + listing
    ├── currencies.py     # currencies CRUD + enable/disable + primary + linked listings
    ├── exchange_rates.py # rates CRUD (by ID or pair/date) + bulk set
    ├── autocomplete.py   # typeahead lookups for forms (accounts, bills, tags, …)
    └── insights.py       # summary, dashboard charts, expense/income aggregation
```

Each tool module exposes a `register(mcp: FastMCP) -> None` function that defines async handlers decorated with `@mcp.tool(name=..., description=...)`. Handlers use Pydantic `Annotated[..., Field(description=...)]` parameters (FastMCP derives the JSON Schema automatically) and call `firefly_mcp.client.request(method, path, params=..., json=...)`. The shared `request()` helper handles 204 responses, JSON parsing, and converts upstream errors into `FireflyAPIError` with the Firefly `message`/`errors` fields preserved.

To add a new endpoint: pick (or create) the right module under `firefly_mcp/tools/`, define an async function inside `register()`, decorate with `@mcp.tool`, and call `request()` with the OpenAPI path. Then either it gets picked up automatically (existing module) or add the module to the import list at the top of `firefly_mcp/server.py`.

`firefly-iii-openapi.yaml` is kept in the repo as a vendored third-party reference — useful for confirming endpoint shapes when adding tools — but **is no longer loaded at runtime**.

## Releases

Versioning is automated via **python-semantic-release** driven by Conventional Commits (`feat:`, `fix:`, `perf:`, `chore:`, `docs:`, `refactor:`, `test:`, `build:`, `ci:`, `style:`).
- `feat` → minor bump, `fix`/`perf` → patch, others → no bump.
- Version source of truth: `pyproject.toml:project.version`.
- `major_on_zero = true` and `allow_zero_version = false` — once at 1.x, breaking changes (commits with `!` or `BREAKING CHANGE:` footer) bump major.
- Changelog is appended to `CHANGELOG.md` at the `<!-- version list -->` marker.
