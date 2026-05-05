"""Piggy bank tools — savings goals attached to one or more asset accounts."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..client import request


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_piggy_banks",
        description=(
            "List all piggy banks. Each piggy bank tracks progress toward a "
            "savings goal sitting inside one or more asset accounts."
        ),
    )
    async def list_piggy_banks(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            "/v1/piggy-banks",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="get_piggy_bank",
        description="Fetch a single piggy bank by numeric ID.",
    )
    async def get_piggy_bank(
        id: Annotated[str, Field(description="Numeric piggy bank ID.")],
    ) -> dict:
        return await request("GET", f"/v1/piggy-banks/{id}")

    @mcp.tool(
        name="create_piggy_bank",
        description=(
            "Create a new piggy bank. Provide ``account_id`` to host the "
            "savings inside one asset account, or ``account_ids`` to span "
            "several — at least one is required. ``target_amount`` is the goal."
        ),
    )
    async def create_piggy_bank(
        name: Annotated[str, Field(description="Piggy bank display name.")],
        target_amount: Annotated[
            str,
            Field(description="Decimal string goal amount, e.g. ``500.00``."),
        ],
        account_id: Annotated[
            str | None,
            Field(description="Numeric asset account ID hosting the savings."),
        ] = None,
        account_ids: Annotated[
            list[str] | None,
            Field(description="Multiple asset account IDs (alternative to account_id)."),
        ] = None,
        current_amount: Annotated[
            str | None,
            Field(description="Decimal string starting amount."),
        ] = None,
        start_date: Annotated[
            str | None,
            Field(description="YYYY-MM-DD."),
        ] = None,
        target_date: Annotated[
            str | None,
            Field(description="YYYY-MM-DD."),
        ] = None,
        object_group_id: Annotated[
            str | None,
            Field(description="Numeric object-group ID for organisation."),
        ] = None,
        notes: Annotated[str | None, Field(description="Free-form notes.")] = None,
    ) -> dict:
        ids: list[str] = []
        if account_id:
            ids.append(account_id)
        if account_ids:
            ids.extend(a for a in account_ids if a not in ids)
        if not ids:
            raise ValueError(
                "create_piggy_bank requires at least one of "
                "`account_id` or `account_ids`."
            )

        body: dict = {
            "name": name,
            "target_amount": target_amount,
            "current_amount": current_amount,
            "start_date": start_date,
            "target_date": target_date,
            "object_group_id": object_group_id,
            "notes": notes,
        }
        if ids:
            body["accounts"] = [{"id": a} for a in ids]
        body = {k: v for k, v in body.items() if v is not None}
        return await request("POST", "/v1/piggy-banks", json=body)

    @mcp.tool(
        name="update_piggy_bank",
        description=(
            "Update a piggy bank. To add or remove money, pass the new "
            "``current_amount`` (decimal string). Only fields you pass are "
            "changed."
        ),
    )
    async def update_piggy_bank(
        id: Annotated[str, Field(description="Numeric piggy bank ID.")],
        name: Annotated[str | None, Field(description="New name.")] = None,
        target_amount: Annotated[
            str | None,
            Field(description="Decimal string goal amount."),
        ] = None,
        current_amount: Annotated[
            str | None,
            Field(description="Decimal string current saved amount."),
        ] = None,
        target_date: Annotated[
            str | None,
            Field(description="YYYY-MM-DD."),
        ] = None,
        notes: Annotated[str | None, Field(description="New notes.")] = None,
    ) -> dict:
        body = {
            "name": name,
            "target_amount": target_amount,
            "current_amount": current_amount,
            "target_date": target_date,
            "notes": notes,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("PUT", f"/v1/piggy-banks/{id}", json=body)

    @mcp.tool(
        name="delete_piggy_bank",
        description="Permanently delete a piggy bank. **Destructive**.",
    )
    async def delete_piggy_bank(
        id: Annotated[str, Field(description="Numeric piggy bank ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/piggy-banks/{id}")
        return {"status": "deleted", "id": id}

    @mcp.tool(
        name="list_piggy_bank_attachments",
        description="List attachments uploaded to a piggy bank.",
    )
    async def list_piggy_bank_attachments(
        id: Annotated[str, Field(description="Numeric piggy bank ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/piggy-banks/{id}/attachments",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="list_piggy_bank_events",
        description=(
            "List events recorded against a piggy bank — i.e. each time "
            "money was added or removed from the savings goal."
        ),
    )
    async def list_piggy_bank_events(
        id: Annotated[str, Field(description="Numeric piggy bank ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/piggy-banks/{id}/events",
            params={"limit": limit, "page": page},
        )
