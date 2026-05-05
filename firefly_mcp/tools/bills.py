"""Bill tools — recurring expected expenses (rent, subscriptions, etc.)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from ..client import request

RepeatFreq = Literal["weekly", "monthly", "quarterly", "half-year", "yearly"]


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_bills",
        description=(
            "List all bills (recurring expected expenses). Optionally filter "
            "to a date range to see which bills are due in that window."
        ),
    )
    async def list_bills(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
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
            "/v1/bills",
            params={"limit": limit, "page": page, "start": start, "end": end},
        )

    @mcp.tool(
        name="get_bill",
        description="Fetch a single bill by numeric ID.",
    )
    async def get_bill(
        id: Annotated[str, Field(description="Numeric bill ID.")],
    ) -> dict:
        return await request("GET", f"/v1/bills/{id}")

    @mcp.tool(
        name="create_bill",
        description=(
            "Create a recurring bill. ``amount_min`` / ``amount_max`` define "
            "the expected amount range; ``repeat_freq`` controls cadence "
            "(``monthly`` is most common)."
        ),
    )
    async def create_bill(
        name: Annotated[str, Field(description="Bill name.")],
        amount_min: Annotated[
            str,
            Field(description="Decimal string minimum expected amount."),
        ],
        amount_max: Annotated[
            str,
            Field(description="Decimal string maximum expected amount."),
        ],
        date: Annotated[
            str,
            Field(description="YYYY-MM-DD anchor date for the schedule."),
        ],
        repeat_freq: Annotated[RepeatFreq, Field(description="Recurrence frequency.")],
        skip: Annotated[
            int,
            Field(
                ge=0,
                description="Periods to skip between hits (0 = every period).",
            ),
        ] = 0,
        active: Annotated[bool, Field(description="Active flag.")] = True,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217 currency code."),
        ] = None,
        notes: Annotated[str | None, Field(description="Free-form notes.")] = None,
    ) -> dict:
        body = {
            "name": name,
            "amount_min": amount_min,
            "amount_max": amount_max,
            "date": date,
            "repeat_freq": repeat_freq,
            "skip": skip,
            "active": active,
            "currency_code": currency_code,
            "notes": notes,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("POST", "/v1/bills", json=body)

    @mcp.tool(
        name="update_bill",
        description="Update a bill. Only fields you pass are changed.",
    )
    async def update_bill(
        id: Annotated[str, Field(description="Numeric bill ID.")],
        name: Annotated[str | None, Field(description="New name.")] = None,
        amount_min: Annotated[str | None, Field(description="Decimal string.")] = None,
        amount_max: Annotated[str | None, Field(description="Decimal string.")] = None,
        active: Annotated[bool | None, Field(description="Active flag.")] = None,
        notes: Annotated[str | None, Field(description="New notes.")] = None,
    ) -> dict:
        body = {
            "name": name,
            "amount_min": amount_min,
            "amount_max": amount_max,
            "active": active,
            "notes": notes,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("PUT", f"/v1/bills/{id}", json=body)

    @mcp.tool(
        name="delete_bill",
        description="Permanently delete a bill. **Destructive**.",
    )
    async def delete_bill(
        id: Annotated[str, Field(description="Numeric bill ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/bills/{id}")
        return {"status": "deleted", "id": id}

    @mcp.tool(
        name="list_bill_attachments",
        description="List attachments (e.g. PDFs, images) uploaded to a bill.",
    )
    async def list_bill_attachments(
        id: Annotated[str, Field(description="Numeric bill ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/bills/{id}/attachments",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="list_bill_rules",
        description=(
            "List Firefly III rules whose action assigns transactions to "
            "this bill. Useful for auditing automatic bill matching."
        ),
    )
    async def list_bill_rules(
        id: Annotated[str, Field(description="Numeric bill ID.")],
    ) -> dict:
        return await request("GET", f"/v1/bills/{id}/rules")

    @mcp.tool(
        name="list_bill_transactions",
        description=(
            "List transactions linked to a specific bill, optionally "
            "filtered by date range and/or transaction type."
        ),
    )
    async def list_bill_transactions(
        id: Annotated[str, Field(description="Numeric bill ID.")],
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
            f"/v1/bills/{id}/transactions",
            params={
                "limit": limit,
                "page": page,
                "start": start,
                "end": end,
                "type": type,
            },
        )
