"""FastMCP server assembly: load env, register all tool modules, attach
prompts and the ``/health`` route, and expose ``app`` for uvicorn."""

from __future__ import annotations

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

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


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """Liveness probe — does not call the upstream Firefly III API."""
    return JSONResponse({"status": "ok", "service": "Firefly III MCP"})


@mcp.prompt
def get_account_balance_prompt(account_name: str) -> str:
    """Prompt asking for the current balance of a specific account."""
    return f"What is the current balance of the account named '{account_name}'?"


@mcp.prompt
def summarize_spending_by_category_prompt(start_date: str, end_date: str) -> str:
    """Prompt summarizing spending by category between two YYYY-MM-DD dates."""
    return (
        "Please provide a summary of my spending by category from "
        f"{start_date} to {end_date}."
    )


app = mcp.http_app()
