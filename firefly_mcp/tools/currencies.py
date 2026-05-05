"""Currency tools — manage currencies (ISO-4217 codes) used by Firefly III."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..client import request


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_currencies",
        description="List all currencies known to Firefly III (enabled and disabled).",
    )
    async def list_currencies(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            "/v1/currencies",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="get_primary_currency",
        description="Fetch the user's primary (default) currency.",
    )
    async def get_primary_currency() -> dict:
        return await request("GET", "/v1/currencies/primary")

    @mcp.tool(
        name="create_currency",
        description=(
            "Create a new currency. ``code`` is a 3-character identifier "
            "(typically ISO-4217, e.g. ``EUR``). Pass ``primary=True`` to "
            "make it the new primary currency on creation."
        ),
    )
    async def create_currency(
        code: Annotated[
            str,
            Field(min_length=3, max_length=3, description="3-char currency code."),
        ],
        name: Annotated[str, Field(description="Human-readable name.")],
        symbol: Annotated[str, Field(description="Display symbol, e.g. '$'.")],
        decimal_places: Annotated[
            int | None,
            Field(ge=0, le=16, description="Decimals to display (0-16)."),
        ] = None,
        enabled: Annotated[
            bool | None,
            Field(description="Whether the currency is enabled (default True)."),
        ] = None,
        primary: Annotated[
            bool | None,
            Field(description="Make this the primary currency."),
        ] = None,
    ) -> dict:
        body = {
            "code": code,
            "name": name,
            "symbol": symbol,
            "decimal_places": decimal_places,
            "enabled": enabled,
            "primary": primary,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("POST", "/v1/currencies", json=body)

    @mcp.tool(
        name="get_currency",
        description="Fetch a single currency by its 3-character code.",
    )
    async def get_currency(
        code: Annotated[str, Field(description="3-char currency code, e.g. EUR.")],
    ) -> dict:
        return await request("GET", f"/v1/currencies/{code}")

    @mcp.tool(
        name="update_currency",
        description=(
            "Update a currency's metadata. Only fields you pass are changed. "
            "Note: ``primary`` only accepts True (you cannot drop a currency "
            "from primary status here — promote a different one instead)."
        ),
    )
    async def update_currency(
        code: Annotated[str, Field(description="Currency code to update.")],
        new_code: Annotated[
            str | None,
            Field(min_length=3, max_length=3, description="Replace the code."),
        ] = None,
        name: Annotated[str | None, Field(description="New name.")] = None,
        symbol: Annotated[str | None, Field(description="New symbol.")] = None,
        decimal_places: Annotated[
            int | None,
            Field(ge=0, le=16, description="Decimals to display (0-16)."),
        ] = None,
        enabled: Annotated[bool | None, Field(description="Enable/disable.")] = None,
        primary: Annotated[
            bool | None,
            Field(description="Pass True to promote to primary."),
        ] = None,
    ) -> dict:
        body = {
            "code": new_code,
            "name": name,
            "symbol": symbol,
            "decimal_places": decimal_places,
            "enabled": enabled,
            "primary": primary,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("PUT", f"/v1/currencies/{code}", json=body)

    @mcp.tool(
        name="delete_currency",
        description="Permanently delete a currency by code. **Destructive**.",
    )
    async def delete_currency(
        code: Annotated[str, Field(description="Currency code to delete.")],
    ) -> dict:
        await request("DELETE", f"/v1/currencies/{code}")
        return {"status": "deleted", "code": code}

    @mcp.tool(
        name="enable_currency",
        description="Enable a currency so it can be used in transactions.",
    )
    async def enable_currency(
        code: Annotated[str, Field(description="Currency code to enable.")],
    ) -> dict:
        return await request("POST", f"/v1/currencies/{code}/enable")

    @mcp.tool(
        name="disable_currency",
        description=(
            "Disable a currency. Will fail if the currency is still in use "
            "by accounts or transactions."
        ),
    )
    async def disable_currency(
        code: Annotated[str, Field(description="Currency code to disable.")],
    ) -> dict:
        return await request("POST", f"/v1/currencies/{code}/disable")

    @mcp.tool(
        name="set_primary_currency",
        description=(
            "Promote the given currency to be the user's primary currency. "
            "Demotes the previous primary."
        ),
    )
    async def set_primary_currency(
        code: Annotated[str, Field(description="Currency code to make primary.")],
    ) -> dict:
        return await request("POST", f"/v1/currencies/{code}/primary")

    @mcp.tool(
        name="list_currency_accounts",
        description="List all accounts that use the given currency.",
    )
    async def list_currency_accounts(
        code: Annotated[str, Field(description="Currency code.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
        date: Annotated[
            str | None,
            Field(description="YYYY-MM-DD point-in-time for balances."),
        ] = None,
        type: Annotated[
            str | None,
            Field(description="Optional account type filter (e.g. 'asset')."),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/currencies/{code}/accounts",
            params={"limit": limit, "page": page, "date": date, "type": type},
        )

    @mcp.tool(
        name="list_currency_available_budgets",
        description="List all available-budget envelopes denominated in this currency.",
    )
    async def list_currency_available_budgets(
        code: Annotated[str, Field(description="Currency code.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
        start: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/currencies/{code}/available-budgets",
            params={"limit": limit, "page": page, "start": start, "end": end},
        )

    @mcp.tool(
        name="list_currency_bills",
        description="List all bills denominated in this currency.",
    )
    async def list_currency_bills(
        code: Annotated[str, Field(description="Currency code.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
        start: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/currencies/{code}/bills",
            params={"limit": limit, "page": page, "start": start, "end": end},
        )

    @mcp.tool(
        name="list_currency_budget_limits",
        description="List all budget limits denominated in this currency.",
    )
    async def list_currency_budget_limits(
        code: Annotated[str, Field(description="Currency code.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
        start: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/currencies/{code}/budget-limits",
            params={"limit": limit, "page": page, "start": start, "end": end},
        )

    @mcp.tool(
        name="list_currency_recurrences",
        description="List all recurring transactions denominated in this currency.",
    )
    async def list_currency_recurrences(
        code: Annotated[str, Field(description="Currency code.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/currencies/{code}/recurrences",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="list_currency_rules",
        description="List all rules that reference this currency.",
    )
    async def list_currency_rules(
        code: Annotated[str, Field(description="Currency code.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/currencies/{code}/rules",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="list_currency_transactions",
        description=(
            "List all transactions whose currency matches the given code. "
            "Filter by date range and/or transaction type."
        ),
    )
    async def list_currency_transactions(
        code: Annotated[str, Field(description="Currency code.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
        start: Annotated[str | None, Field(description="YYYY-MM-DD lower bound.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD upper bound.")] = None,
        type: Annotated[
            str | None,
            Field(description="Transaction type filter (e.g. 'deposit', 'withdrawal')."),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/currencies/{code}/transactions",
            params={
                "limit": limit,
                "page": page,
                "start": start,
                "end": end,
                "type": type,
            },
        )
