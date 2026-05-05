"""Tag tools — free-form labels attached to transactions."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..client import request


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_tags",
        description="List all of the user's tags, paginated.",
    )
    async def list_tags(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            "/v1/tags",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="get_tag",
        description="Fetch a single tag by numeric ID or tag name.",
    )
    async def get_tag(
        tag: Annotated[
            str,
            Field(description="Tag ID or tag name (e.g. 'groceries')."),
        ],
    ) -> dict:
        return await request("GET", f"/v1/tags/{tag}")

    @mcp.tool(
        name="create_tag",
        description="Create a new tag.",
    )
    async def create_tag(
        tag: Annotated[str, Field(description="The tag name.")],
        date: Annotated[
            str | None,
            Field(description="YYYY-MM-DD date the tag applies to."),
        ] = None,
        description: Annotated[
            str | None,
            Field(description="Free-form description."),
        ] = None,
        latitude: Annotated[
            float | None,
            Field(description="Latitude of the tag's location."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Longitude of the tag's location."),
        ] = None,
        zoom_level: Annotated[
            int | None,
            Field(description="Map zoom level (provider-specific)."),
        ] = None,
    ) -> dict:
        body = {
            "tag": tag,
            "date": date,
            "description": description,
            "latitude": latitude,
            "longitude": longitude,
            "zoom_level": zoom_level,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("POST", "/v1/tags", json=body)

    @mcp.tool(
        name="update_tag",
        description="Update a tag. Only fields you pass are changed.",
    )
    async def update_tag(
        tag: Annotated[
            str,
            Field(description="Tag ID or current tag name to update."),
        ],
        new_tag: Annotated[
            str | None,
            Field(description="New tag name."),
        ] = None,
        date: Annotated[
            str | None,
            Field(description="YYYY-MM-DD date the tag applies to."),
        ] = None,
        description: Annotated[
            str | None,
            Field(description="Free-form description."),
        ] = None,
        latitude: Annotated[
            float | None,
            Field(description="Latitude of the tag's location."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Longitude of the tag's location."),
        ] = None,
        zoom_level: Annotated[
            int | None,
            Field(description="Map zoom level (provider-specific)."),
        ] = None,
    ) -> dict:
        body = {
            "tag": new_tag,
            "date": date,
            "description": description,
            "latitude": latitude,
            "longitude": longitude,
            "zoom_level": zoom_level,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("PUT", f"/v1/tags/{tag}", json=body)

    @mcp.tool(
        name="delete_tag",
        description="Permanently delete a tag. **Destructive**.",
    )
    async def delete_tag(
        tag: Annotated[
            str,
            Field(description="Tag ID or tag name to delete."),
        ],
    ) -> dict:
        await request("DELETE", f"/v1/tags/{tag}")
        return {"status": "deleted", "id": tag}

    @mcp.tool(
        name="list_tag_attachments",
        description="List all attachments associated with a tag.",
    )
    async def list_tag_attachments(
        tag: Annotated[str, Field(description="Tag ID or tag name.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/tags/{tag}/attachments",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="list_tag_transactions",
        description="List all transactions carrying a given tag.",
    )
    async def list_tag_transactions(
        tag: Annotated[str, Field(description="Tag ID or tag name.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
        start: Annotated[
            str | None,
            Field(description="YYYY-MM-DD start date (inclusive)."),
        ] = None,
        end: Annotated[
            str | None,
            Field(description="YYYY-MM-DD end date (inclusive)."),
        ] = None,
        type: Annotated[
            str | None,
            Field(
                description=(
                    "Filter on transaction type "
                    "(e.g. 'withdrawal', 'deposit', 'transfer', 'all')."
                ),
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/tags/{tag}/transactions",
            params={
                "limit": limit,
                "page": page,
                "start": start,
                "end": end,
                "type": type,
            },
        )
