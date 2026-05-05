"""Rule tools — automation rules that match and modify transactions."""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from ..client import request

RuleTriggerType = Literal["store-journal", "update-journal", "manual-activation"]


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_rules",
        description="List all rules across every rule group.",
    )
    async def list_rules(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            "/v1/rules",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="get_rule",
        description="Fetch a single rule by numeric ID, including its triggers and actions.",
    )
    async def get_rule(
        id: Annotated[str, Field(description="Numeric rule ID.")],
    ) -> dict:
        return await request("GET", f"/v1/rules/{id}")

    @mcp.tool(
        name="create_rule",
        description=(
            "Create a new rule. `triggers` is a list of dicts shaped "
            "{type: <RuleTriggerKeyword>, value: str, order?: int, active?: bool, "
            "prohibited?: bool, stop_processing?: bool}; `actions` is a list of "
            "{type: <RuleActionKeyword>, value: str, order?: int, active?: bool, "
            "stop_processing?: bool}. The `trigger` field selects when the rule fires."
        ),
    )
    async def create_rule(
        title: Annotated[str, Field(description="Rule title.")],
        rule_group_id: Annotated[
            str,
            Field(description="ID of the parent rule group."),
        ],
        trigger: Annotated[
            RuleTriggerType,
            Field(
                description=(
                    "When the rule fires: 'store-journal' (on transaction creation), "
                    "'update-journal' (on update), or 'manual-activation' (only when "
                    "manually triggered)."
                ),
            ),
        ],
        triggers: Annotated[
            list[dict],
            Field(
                description=(
                    "Conditions to match. Each item: "
                    "{type, value, order?, active?, prohibited?, stop_processing?}."
                ),
            ),
        ],
        actions: Annotated[
            list[dict],
            Field(
                description=(
                    "Actions to apply when the rule matches. Each item: "
                    "{type, value, order?, active?, stop_processing?}."
                ),
            ),
        ],
        description: Annotated[
            str | None, Field(description="Free-form description.")
        ] = None,
        order: Annotated[
            int | None,
            Field(description="Position of this rule within its group."),
        ] = None,
        active: Annotated[
            bool | None,
            Field(description="Whether the rule is active. Defaults to true."),
        ] = None,
        strict: Annotated[
            bool | None,
            Field(
                description=(
                    "If true, ALL triggers must match for the rule to fire; "
                    "otherwise just one is enough. Defaults to true."
                ),
            ),
        ] = None,
        stop_processing: Annotated[
            bool | None,
            Field(
                description=(
                    "If true, later rules in the same group are skipped after this "
                    "rule fires. Defaults to false."
                ),
            ),
        ] = None,
    ) -> dict:
        body = {
            "title": title,
            "rule_group_id": rule_group_id,
            "trigger": trigger,
            "triggers": triggers,
            "actions": actions,
            "description": description,
            "order": order,
            "active": active,
            "strict": strict,
            "stop_processing": stop_processing,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("POST", "/v1/rules", json=body)

    @mcp.tool(
        name="update_rule",
        description=(
            "Update a rule. Only fields you pass are changed. Passing `triggers` "
            "or `actions` REPLACES the full list — not a partial merge."
        ),
    )
    async def update_rule(
        id: Annotated[str, Field(description="Numeric rule ID.")],
        title: Annotated[str | None, Field(description="New title.")] = None,
        description: Annotated[
            str | None, Field(description="New description.")
        ] = None,
        rule_group_id: Annotated[
            str | None, Field(description="Move the rule to this group.")
        ] = None,
        order: Annotated[int | None, Field(description="New order.")] = None,
        trigger: Annotated[
            RuleTriggerType | None,
            Field(description="New firing trigger."),
        ] = None,
        active: Annotated[
            bool | None, Field(description="Active flag.")
        ] = None,
        strict: Annotated[
            bool | None, Field(description="Strict matching flag.")
        ] = None,
        stop_processing: Annotated[
            bool | None, Field(description="Stop later rules after this one fires.")
        ] = None,
        triggers: Annotated[
            list[dict] | None,
            Field(
                description=(
                    "Replacement triggers list. Each item: "
                    "{type, value, order?, active?, prohibited?, stop_processing?}."
                ),
            ),
        ] = None,
        actions: Annotated[
            list[dict] | None,
            Field(
                description=(
                    "Replacement actions list. Each item: "
                    "{type, value, order?, active?, stop_processing?}."
                ),
            ),
        ] = None,
    ) -> dict:
        body = {
            "title": title,
            "description": description,
            "rule_group_id": rule_group_id,
            "order": order,
            "trigger": trigger,
            "active": active,
            "strict": strict,
            "stop_processing": stop_processing,
            "triggers": triggers,
            "actions": actions,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("PUT", f"/v1/rules/{id}", json=body)

    @mcp.tool(
        name="delete_rule",
        description="Permanently delete a rule. **Destructive**.",
    )
    async def delete_rule(
        id: Annotated[str, Field(description="Numeric rule ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/rules/{id}")
        return {"status": "deleted", "id": id}

    @mcp.tool(
        name="test_rule",
        description=(
            "Test which transactions would be matched by this rule. No changes are "
            "made. Optionally scope by date range and asset/liability account IDs."
        ),
    )
    async def test_rule(
        id: Annotated[str, Field(description="Numeric rule ID.")],
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
    ) -> dict:
        return await request(
            "GET",
            f"/v1/rules/{id}/test",
            params={
                "start": start,
                "end": end,
                "accounts[]": accounts,
            },
        )

    @mcp.tool(
        name="trigger_rule",
        description=(
            "Fire this rule against transactions. **Mutates data**: rule actions "
            "will be applied. Optionally scope by date range and accounts."
        ),
    )
    async def trigger_rule(
        id: Annotated[str, Field(description="Numeric rule ID.")],
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
            f"/v1/rules/{id}/trigger",
            params={
                "start": start,
                "end": end,
                "accounts[]": accounts,
            },
        )
