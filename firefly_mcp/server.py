"""FastMCP server assembly: load env, register all tool modules, attach
prompts and the ``/health`` route, and expose ``app`` for uvicorn."""

from __future__ import annotations

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .prompts import baseline as prompts_baseline, macro as prompts_macro
from .tools import (
    accounts,
    attachments,
    autocomplete,
    bills,
    budgets,
    categories,
    currencies,
    exchange_rates,
    insights,
    object_groups,
    piggy_banks,
    recurrences,
    rule_groups,
    rules,
    system,
    tags,
    transactions,
)

load_dotenv()

mcp: FastMCP = FastMCP(
    name="Firefly III MCP server",
    instructions=(
        "Tools to read and write a personal Firefly III instance: accounts, "
        "transactions, budgets (+ limits), bills, piggy banks, categories, "
        "tags, attachments, object groups, rules and rule groups, recurrences, "
        "currencies and exchange rates, autocomplete lookups, and "
        "pre-aggregated insight summaries. All money values are decimal "
        "strings; all dates are ISO YYYY-MM-DD."
    ),
)

for module in (
    system,
    accounts,
    transactions,
    budgets,
    bills,
    piggy_banks,
    categories,
    tags,
    attachments,
    insights,
    object_groups,
    autocomplete,
    rules,
    rule_groups,
    recurrences,
    currencies,
    exchange_rates,
):
    module.register(mcp)

prompts_baseline.register(mcp)
prompts_macro.register(mcp)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """Liveness probe — does not call the upstream Firefly III API."""
    return JSONResponse({"status": "ok", "service": "Firefly III MCP"})


app = mcp.http_app()
