"""Autocomplete tools — typeahead lookup of IDs/names for forms and prompts."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..client import request


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="autocomplete_accounts",
        description=(
            "Typeahead search of accounts. Returns minimal {id, name, type} "
            "rows for the user to pick from. Optionally filter by account "
            "types (e.g. ``asset``, ``expense``, ``revenue``, ``liabilities``)."
        ),
    )
    async def autocomplete_accounts(
        query: Annotated[
            str | None,
            Field(description="Substring to match against account names."),
        ] = None,
        limit: Annotated[
            int,
            Field(ge=1, le=50, description="Max items returned (default 10)."),
        ] = 10,
        types: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional list of account types to restrict the search "
                    "(e.g. [\"asset\", \"expense\"])."
                )
            ),
        ] = None,
        date: Annotated[
            str | None,
            Field(
                description=(
                    "YYYY-MM-DD. If returned account is asset/liability, "
                    "balance is computed as of this date."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"query": query, "limit": limit, "date": date}
        if types:
            params["types"] = ",".join(types)
        return await request("GET", "/v1/autocomplete/accounts", params=params)

    def _make_simple_autocomplete(
        tool_name: str,
        path: str,
        subject: str,
    ) -> None:
        description = (
            f"Typeahead search of {subject}. Returns minimal autocomplete "
            "rows (id + name) for picking inside other tools."
        )

        @mcp.tool(name=tool_name, description=description)
        async def _autocomplete(
            query: Annotated[
                str | None,
                Field(description="Substring to match against names."),
            ] = None,
            limit: Annotated[
                int,
                Field(ge=1, le=50, description="Max items returned (default 10)."),
            ] = 10,
        ) -> dict[str, Any]:
            return await request(
                "GET",
                path,
                params={"query": query, "limit": limit},
            )

    _make_simple_autocomplete(
        "autocomplete_bills",
        "/v1/autocomplete/bills",
        "bills",
    )
    _make_simple_autocomplete(
        "autocomplete_budgets",
        "/v1/autocomplete/budgets",
        "budgets",
    )
    _make_simple_autocomplete(
        "autocomplete_categories",
        "/v1/autocomplete/categories",
        "categories",
    )
    _make_simple_autocomplete(
        "autocomplete_currencies",
        "/v1/autocomplete/currencies",
        "currencies",
    )
    _make_simple_autocomplete(
        "autocomplete_currencies_with_code",
        "/v1/autocomplete/currencies-with-code",
        "currencies (results include the ISO currency code)",
    )
    _make_simple_autocomplete(
        "autocomplete_object_groups",
        "/v1/autocomplete/object-groups",
        "object groups",
    )
    _make_simple_autocomplete(
        "autocomplete_piggy_banks",
        "/v1/autocomplete/piggy-banks",
        "piggy banks",
    )
    _make_simple_autocomplete(
        "autocomplete_piggy_banks_with_balance",
        "/v1/autocomplete/piggy-banks-with-balance",
        "piggy banks (results include current balance)",
    )
    _make_simple_autocomplete(
        "autocomplete_recurring",
        "/v1/autocomplete/recurring",
        "recurring transactions",
    )
    _make_simple_autocomplete(
        "autocomplete_rule_groups",
        "/v1/autocomplete/rule-groups",
        "rule groups",
    )
    _make_simple_autocomplete(
        "autocomplete_rules",
        "/v1/autocomplete/rules",
        "rules",
    )
    _make_simple_autocomplete(
        "autocomplete_subscriptions",
        "/v1/autocomplete/subscriptions",
        "subscriptions",
    )
    _make_simple_autocomplete(
        "autocomplete_tags",
        "/v1/autocomplete/tags",
        "tags",
    )
    _make_simple_autocomplete(
        "autocomplete_transaction_types",
        "/v1/autocomplete/transaction-types",
        "transaction types",
    )
    _make_simple_autocomplete(
        "autocomplete_transactions",
        "/v1/autocomplete/transactions",
        "transactions (by description)",
    )
    _make_simple_autocomplete(
        "autocomplete_transactions_with_id",
        "/v1/autocomplete/transactions-with-id",
        "transactions (results include the transaction journal ID)",
    )
