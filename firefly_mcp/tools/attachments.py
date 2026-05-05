"""Attachment tools — list / get / delete metadata for files attached to
Firefly objects.

Binary upload/download is intentionally not exposed: it doesn't fit the
plain-JSON MCP tool model cleanly. Manage uploads through the Firefly III
web UI and reference attachments here for metadata only.
"""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..client import request


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_attachments",
        description=(
            "List metadata for all files attached to Firefly objects "
            "(transactions, accounts, bills, etc.). Returns filenames, "
            "sizes, MIME types, and the parent object reference."
        ),
    )
    async def list_attachments(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            "/v1/attachments",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="get_attachment",
        description="Fetch attachment metadata by numeric ID.",
    )
    async def get_attachment(
        id: Annotated[str, Field(description="Numeric attachment ID.")],
    ) -> dict:
        return await request("GET", f"/v1/attachments/{id}")

    @mcp.tool(
        name="delete_attachment",
        description="Permanently delete an attachment. **Destructive**.",
    )
    async def delete_attachment(
        id: Annotated[str, Field(description="Numeric attachment ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/attachments/{id}")
        return {"status": "deleted", "id": id}
