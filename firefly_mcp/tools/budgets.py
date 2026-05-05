"""Budget tools — budgets and per-period budget limits."""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from ..client import request

AutoBudgetType = Literal["reset", "rollover", "none"]
AutoBudgetPeriod = Literal["daily", "weekly", "monthly", "quarterly", "half_year", "yearly"]


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_budgets",
        description=(
            "List all budgets, including their auto-budget settings and "
            "current period spending if Firefly has them computed."
        ),
    )
    async def list_budgets(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
        start: Annotated[
            str | None,
            Field(description="YYYY-MM-DD lower bound for spent calculation."),
        ] = None,
        end: Annotated[
            str | None,
            Field(description="YYYY-MM-DD upper bound for spent calculation."),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/budgets",
            params={"limit": limit, "page": page, "start": start, "end": end},
        )

    @mcp.tool(
        name="get_budget",
        description="Fetch a single budget by numeric ID.",
    )
    async def get_budget(
        id: Annotated[str, Field(description="Numeric budget ID.")],
    ) -> dict:
        return await request("GET", f"/v1/budgets/{id}")

    @mcp.tool(
        name="create_budget",
        description=(
            "Create a new budget. The ``auto_budget_*`` fields configure a "
            "recurring auto-budget that Firefly will roll forward each period."
        ),
    )
    async def create_budget(
        name: Annotated[str, Field(description="Display name.")],
        active: Annotated[bool, Field(description="Active flag.")] = True,
        auto_budget_type: Annotated[
            AutoBudgetType | None,
            Field(description="Type of auto-budget. ``none`` to disable."),
        ] = None,
        auto_budget_amount: Annotated[
            str | None,
            Field(description="Decimal string. Required if auto_budget_type set."),
        ] = None,
        auto_budget_period: Annotated[
            AutoBudgetPeriod | None,
            Field(description="Auto-budget recurrence."),
        ] = None,
        auto_budget_currency_code: Annotated[
            str | None,
            Field(description="ISO 4217 code for the auto-budget."),
        ] = None,
        notes: Annotated[str | None, Field(description="Free-form notes.")] = None,
    ) -> dict:
        body = {
            "name": name,
            "active": active,
            "auto_budget_type": auto_budget_type,
            "auto_budget_amount": auto_budget_amount,
            "auto_budget_period": auto_budget_period,
            "auto_budget_currency_code": auto_budget_currency_code,
            "notes": notes,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("POST", "/v1/budgets", json=body)

    @mcp.tool(
        name="update_budget",
        description="Update a budget. Only fields you pass are changed.",
    )
    async def update_budget(
        id: Annotated[str, Field(description="Numeric budget ID.")],
        name: Annotated[str | None, Field(description="New name.")] = None,
        active: Annotated[bool | None, Field(description="Active flag.")] = None,
        notes: Annotated[str | None, Field(description="New notes.")] = None,
    ) -> dict:
        body = {"name": name, "active": active, "notes": notes}
        body = {k: v for k, v in body.items() if v is not None}
        return await request("PUT", f"/v1/budgets/{id}", json=body)

    @mcp.tool(
        name="delete_budget",
        description="Permanently delete a budget. **Destructive**.",
    )
    async def delete_budget(
        id: Annotated[str, Field(description="Numeric budget ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/budgets/{id}")
        return {"status": "deleted", "id": id}

    @mcp.tool(
        name="list_budget_limits",
        description=(
            "List the per-period monetary limits configured on a budget. A "
            "budget has zero or more limits, each covering a date range."
        ),
    )
    async def list_budget_limits(
        id: Annotated[str, Field(description="Numeric budget ID.")],
        start: Annotated[
            str | None,
            Field(description="YYYY-MM-DD lower bound."),
        ] = None,
        end: Annotated[
            str | None,
            Field(description="YYYY-MM-DD upper bound."),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/budgets/{id}/limits",
            params={"start": start, "end": end},
        )

    @mcp.tool(
        name="create_budget_limit",
        description=(
            "Create a monetary limit on a budget covering a date range "
            "(e.g. €300 for May 2026)."
        ),
    )
    async def create_budget_limit(
        id: Annotated[str, Field(description="Numeric budget ID.")],
        amount: Annotated[
            str,
            Field(description="Decimal string limit amount, e.g. ``300.00``."),
        ],
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217 code (defaults to budget's currency)."),
        ] = None,
        period: Annotated[
            AutoBudgetPeriod | None,
            Field(description="Recurrence label, mostly informational."),
        ] = None,
    ) -> dict:
        body = {
            "amount": amount,
            "start": start,
            "end": end,
            "currency_code": currency_code,
            "period": period,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("POST", f"/v1/budgets/{id}/limits", json=body)

    @mcp.tool(
        name="delete_budget_limit",
        description="Permanently delete a single budget limit.",
    )
    async def delete_budget_limit(
        budget_id: Annotated[str, Field(description="Numeric budget ID.")],
        limit_id: Annotated[str, Field(description="Numeric limit ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/budgets/{budget_id}/limits/{limit_id}")
        return {"status": "deleted", "budget_id": budget_id, "limit_id": limit_id}

    @mcp.tool(
        name="list_budget_attachments",
        description="List attachments uploaded to a budget.",
    )
    async def list_budget_attachments(
        id: Annotated[str, Field(description="Numeric budget ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/budgets/{id}/attachments",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="list_budget_transactions",
        description=(
            "List transactions assigned to a budget, optionally filtered by "
            "date range and/or transaction type."
        ),
    )
    async def list_budget_transactions(
        id: Annotated[str, Field(description="Numeric budget ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
        start: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
        type: Annotated[
            str | None,
            Field(description="Optional transaction type filter (e.g. withdrawal, deposit, transfer)."),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/budgets/{id}/transactions",
            params={
                "limit": limit,
                "page": page,
                "start": start,
                "end": end,
                "type": type,
            },
        )

    @mcp.tool(
        name="list_transactions_without_budget",
        description=(
            "List transactions that are NOT linked to any budget — useful "
            "for finding spending you forgot to categorise."
        ),
    )
    async def list_transactions_without_budget(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
        start: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
        type: Annotated[
            str | None,
            Field(description="Optional transaction type filter (e.g. withdrawal, deposit, transfer)."),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/budgets/transactions-without-budget",
            params={
                "limit": limit,
                "page": page,
                "start": start,
                "end": end,
                "type": type,
            },
        )

    @mcp.tool(
        name="list_all_budget_limits",
        description=(
            "List every budget limit (across all budgets) overlapping the "
            "given date range. Both ``start`` and ``end`` are required by "
            "Firefly for this endpoint."
        ),
    )
    async def list_all_budget_limits(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
    ) -> dict:
        return await request(
            "GET",
            "/v1/budget-limits",
            params={"start": start, "end": end},
        )

    @mcp.tool(
        name="list_budget_limit_transactions",
        description=(
            "List the transactions covered by a specific budget limit. The "
            "date range is dictated by the limit itself, so no start/end is "
            "needed."
        ),
    )
    async def list_budget_limit_transactions(
        id: Annotated[str, Field(description="Numeric budget ID.")],
        limit_id: Annotated[str, Field(description="Numeric budget-limit ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
        type: Annotated[
            str | None,
            Field(description="Optional transaction type filter (e.g. withdrawal, deposit, transfer)."),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/budgets/{id}/limits/{limit_id}/transactions",
            params={"limit": limit, "page": page, "type": type},
        )
