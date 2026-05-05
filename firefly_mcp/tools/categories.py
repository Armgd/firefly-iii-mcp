"""Category tools — labels for transactions (Groceries, Rent, …)."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..client import request


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_categories",
        description=(
            "List all transaction categories. Optionally pass a date range "
            "to include earned/spent totals for that window."
        ),
    )
    async def list_categories(
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
            "/v1/categories",
            params={"limit": limit, "page": page, "start": start, "end": end},
        )

    @mcp.tool(
        name="get_category",
        description="Fetch a single category by numeric ID.",
    )
    async def get_category(
        id: Annotated[str, Field(description="Numeric category ID.")],
        start: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/categories/{id}",
            params={"start": start, "end": end},
        )

    @mcp.tool(
        name="create_category",
        description="Create a new category.",
    )
    async def create_category(
        name: Annotated[str, Field(description="Category name.")],
        notes: Annotated[str | None, Field(description="Free-form notes.")] = None,
    ) -> dict:
        body = {"name": name}
        if notes is not None:
            body["notes"] = notes
        return await request("POST", "/v1/categories", json=body)

    @mcp.tool(
        name="update_category",
        description="Update a category. Only fields you pass are changed.",
    )
    async def update_category(
        id: Annotated[str, Field(description="Numeric category ID.")],
        name: Annotated[str | None, Field(description="New name.")] = None,
        notes: Annotated[str | None, Field(description="New notes.")] = None,
    ) -> dict:
        body = {"name": name, "notes": notes}
        body = {k: v for k, v in body.items() if v is not None}
        return await request("PUT", f"/v1/categories/{id}", json=body)

    @mcp.tool(
        name="delete_category",
        description="Permanently delete a category. **Destructive**.",
    )
    async def delete_category(
        id: Annotated[str, Field(description="Numeric category ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/categories/{id}")
        return {"status": "deleted", "id": id}

    @mcp.tool(
        name="list_category_attachments",
        description="List attachments uploaded to a category.",
    )
    async def list_category_attachments(
        id: Annotated[str, Field(description="Numeric category ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/categories/{id}/attachments",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="list_category_transactions",
        description=(
            "List transactions tagged with a specific category, optionally "
            "filtered by date range and/or transaction type."
        ),
    )
    async def list_category_transactions(
        id: Annotated[str, Field(description="Numeric category ID.")],
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
            f"/v1/categories/{id}/transactions",
            params={
                "limit": limit,
                "page": page,
                "start": start,
                "end": end,
                "type": type,
            },
        )
