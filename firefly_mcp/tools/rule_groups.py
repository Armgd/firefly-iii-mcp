"""Rule group tools — collections of rules applied to transactions."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..client import request


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_rule_groups",
        description="List all rule groups (containers that hold ordered sets of rules).",
    )
    async def list_rule_groups(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            "/v1/rule-groups",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="get_rule_group",
        description="Fetch a single rule group by numeric ID. Does not include the rules; use list_rules_in_group for that.",
    )
    async def get_rule_group(
        id: Annotated[str, Field(description="Numeric rule group ID.")],
    ) -> dict:
        return await request("GET", f"/v1/rule-groups/{id}")

    @mcp.tool(
        name="create_rule_group",
        description="Create a new rule group.",
    )
    async def create_rule_group(
        title: Annotated[str, Field(description="Rule group title.")],
        description: Annotated[
            str | None, Field(description="Free-form description.")
        ] = None,
        order: Annotated[
            int | None,
            Field(description="Position of this group relative to others."),
        ] = None,
        active: Annotated[
            bool | None,
            Field(description="Whether the group is active. Defaults to true."),
        ] = None,
    ) -> dict:
        body = {
            "title": title,
            "description": description,
            "order": order,
            "active": active,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("POST", "/v1/rule-groups", json=body)

    @mcp.tool(
        name="update_rule_group",
        description="Update a rule group. Only fields you pass are changed.",
    )
    async def update_rule_group(
        id: Annotated[str, Field(description="Numeric rule group ID.")],
        title: Annotated[str | None, Field(description="New title.")] = None,
        description: Annotated[
            str | None, Field(description="New description.")
        ] = None,
        order: Annotated[int | None, Field(description="New order.")] = None,
        active: Annotated[
            bool | None, Field(description="Active flag.")
        ] = None,
    ) -> dict:
        body = {
            "title": title,
            "description": description,
            "order": order,
            "active": active,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("PUT", f"/v1/rule-groups/{id}", json=body)

    @mcp.tool(
        name="delete_rule_group",
        description="Permanently delete a rule group and all rules inside it. **Destructive**.",
    )
    async def delete_rule_group(
        id: Annotated[str, Field(description="Numeric rule group ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/rule-groups/{id}")
        return {"status": "deleted", "id": id}

    @mcp.tool(
        name="list_rules_in_group",
        description="List all rules belonging to a given rule group.",
    )
    async def list_rules_in_group(
        id: Annotated[str, Field(description="Numeric rule group ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/rule-groups/{id}/rules",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="test_rule_group",
        description=(
            "Test which transactions would be matched by all rules in this group. "
            "No changes are made. Optionally limit by date range and asset accounts."
        ),
    )
    async def test_rule_group(
        id: Annotated[str, Field(description="Numeric rule group ID.")],
        start: Annotated[
            str | None, Field(description="YYYY-MM-DD start of test window.")
        ] = None,
        end: Annotated[
            str | None, Field(description="YYYY-MM-DD end of test window.")
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(description="Restrict to these asset/liability account IDs."),
        ] = None,
        limit: Annotated[
            int | None, Field(ge=1, le=200, description="Items per page.")
        ] = None,
        page: Annotated[int | None, Field(ge=1, description="1-indexed page.")] = None,
        search_limit: Annotated[
            int | None,
            Field(description="Max transactions Firefly will scan (suggest <=200)."),
        ] = None,
        triggered_limit: Annotated[
            int | None,
            Field(description="Max transactions the group can match before stopping."),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/rule-groups/{id}/test",
            params={
                "start": start,
                "end": end,
                "accounts[]": accounts,
                "limit": limit,
                "page": page,
                "search_limit": search_limit,
                "triggered_limit": triggered_limit,
            },
        )

    @mcp.tool(
        name="trigger_rule_group",
        description=(
            "Fire all rules in this group against transactions. **Mutates data**: "
            "rule actions will be applied. Optionally scope by date range and accounts."
        ),
    )
    async def trigger_rule_group(
        id: Annotated[str, Field(description="Numeric rule group ID.")],
        start: Annotated[
            str | None, Field(description="YYYY-MM-DD start of window.")
        ] = None,
        end: Annotated[
            str | None, Field(description="YYYY-MM-DD end of window.")
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(description="Restrict to these asset/liability account IDs."),
        ] = None,
    ) -> dict:
        return await request(
            "POST",
            f"/v1/rule-groups/{id}/trigger",
            params={
                "start": start,
                "end": end,
                "accounts[]": accounts,
            },
        )
