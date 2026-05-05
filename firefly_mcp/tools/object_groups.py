"""Object-group tools — read-only access to user-defined groupings of
piggy banks and bills."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..client import request


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_object_groups",
        description=(
            "List object groups — user-defined ways to group piggy banks "
            "and bills (e.g. 'Vacation', 'Recurring bills')."
        ),
    )
    async def list_object_groups(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            "/v1/object-groups",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="get_object_group",
        description="Fetch a single object group by numeric ID.",
    )
    async def get_object_group(
        id: Annotated[str, Field(description="Numeric object group ID.")],
    ) -> dict:
        return await request("GET", f"/v1/object-groups/{id}")
