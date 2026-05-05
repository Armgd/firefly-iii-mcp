"""Recurrence tools — recurring (scheduled) transaction templates."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..client import request


_REPETITIONS_EXAMPLE = (
    "List of repetition rules. Each item: "
    '{"type": "daily|weekly|ndom|monthly|yearly", "moment": "<see below>", '
    '"skip": 0, "weekend": 1}. '
    "moment depends on type: empty for daily; 1-7 (Mon-Sun) for weekly; "
    "'W,D' (e.g. '2,3' = 2nd Wednesday) for ndom; day-of-month 1-31 for "
    "monthly; full date 'YYYY-MM-DD' for yearly. "
    "weekend: 1=do nothing, 2=skip, 3=previous Friday, 4=next Monday."
)

_TRANSACTIONS_EXAMPLE = (
    "List of transaction templates. Each item (store): "
    '{"description": "Rent", "amount": "123.45", "source_id": "913", '
    '"destination_id": "258", "currency_code": "EUR", "category_id": "211", '
    '"budget_id": "4", "tags": ["bills"], "piggy_bank_id": null, '
    '"bill_id": null}. '
    "Required: description, amount, source_id, destination_id."
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_recurrences",
        description="List all recurring transactions (paginated).",
    )
    async def list_recurrences(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            "/v1/recurrences",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="get_recurrence",
        description="Fetch a single recurring transaction by numeric ID.",
    )
    async def get_recurrence(
        id: Annotated[str, Field(description="Numeric recurrence ID.")],
    ) -> dict:
        return await request("GET", f"/v1/recurrences/{id}")

    @mcp.tool(
        name="create_recurrence",
        description=(
            "Create a recurring transaction. Requires top-level type "
            "(withdrawal/transfer/deposit), title, first_date, plus "
            "non-empty repetitions and transactions arrays. Use either "
            "repeat_until or nr_of_repetitions to bound it."
        ),
    )
    async def create_recurrence(
        type: Annotated[
            str,
            Field(description="One of: withdrawal, transfer, deposit."),
        ],
        title: Annotated[str, Field(description="Recurrence title, e.g. 'Rent'.")],
        first_date: Annotated[
            str,
            Field(description="YYYY-MM-DD. First firing date, must be after today."),
        ],
        repetitions: Annotated[
            list[dict],
            Field(description=_REPETITIONS_EXAMPLE),
        ],
        transactions: Annotated[
            list[dict],
            Field(description=_TRANSACTIONS_EXAMPLE),
        ],
        description: Annotated[
            str | None,
            Field(description="Recurrence description (not the transaction's)."),
        ] = None,
        repeat_until: Annotated[
            str | None,
            Field(description="YYYY-MM-DD. Use this OR nr_of_repetitions."),
        ] = None,
        nr_of_repetitions: Annotated[
            int | None,
            Field(ge=1, description="Max creations. Use this OR repeat_until."),
        ] = None,
        apply_rules: Annotated[
            bool | None,
            Field(description="Run rules on each created transaction."),
        ] = None,
        active: Annotated[
            bool | None,
            Field(description="Whether the recurrence is active."),
        ] = None,
        notes: Annotated[str | None, Field(description="Free-form notes.")] = None,
    ) -> dict:
        body = {
            "type": type,
            "title": title,
            "first_date": first_date,
            "repetitions": repetitions,
            "transactions": transactions,
            "description": description,
            "repeat_until": repeat_until,
            "nr_of_repetitions": nr_of_repetitions,
            "apply_rules": apply_rules,
            "active": active,
            "notes": notes,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("POST", "/v1/recurrences", json=body)

    @mcp.tool(
        name="update_recurrence",
        description=(
            "Update a recurring transaction. Only fields you pass are changed. "
            "When updating transactions, each item should include its 'id' "
            "(omittable only if there is exactly one transaction)."
        ),
    )
    async def update_recurrence(
        id: Annotated[str, Field(description="Numeric recurrence ID.")],
        title: Annotated[str | None, Field(description="New title.")] = None,
        description: Annotated[
            str | None,
            Field(description="New description."),
        ] = None,
        first_date: Annotated[
            str | None,
            Field(description="YYYY-MM-DD."),
        ] = None,
        repeat_until: Annotated[
            str | None,
            Field(description="YYYY-MM-DD. Use this OR nr_of_repetitions."),
        ] = None,
        nr_of_repetitions: Annotated[
            int | None,
            Field(ge=1, description="Max creations. Use this OR repeat_until."),
        ] = None,
        apply_rules: Annotated[
            bool | None,
            Field(description="Run rules on each created transaction."),
        ] = None,
        active: Annotated[
            bool | None,
            Field(description="Whether the recurrence is active."),
        ] = None,
        notes: Annotated[str | None, Field(description="Free-form notes.")] = None,
        repetitions: Annotated[
            list[dict] | None,
            Field(description="Replacement repetitions. " + _REPETITIONS_EXAMPLE),
        ] = None,
        transactions: Annotated[
            list[dict] | None,
            Field(
                description=(
                    "Replacement transaction templates. Each item should "
                    "include 'id'. " + _TRANSACTIONS_EXAMPLE
                )
            ),
        ] = None,
    ) -> dict:
        body = {
            "title": title,
            "description": description,
            "first_date": first_date,
            "repeat_until": repeat_until,
            "nr_of_repetitions": nr_of_repetitions,
            "apply_rules": apply_rules,
            "active": active,
            "notes": notes,
            "repetitions": repetitions,
            "transactions": transactions,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("PUT", f"/v1/recurrences/{id}", json=body)

    @mcp.tool(
        name="delete_recurrence",
        description=(
            "Permanently delete a recurring transaction. Already-created "
            "transactions are kept. **Destructive**."
        ),
    )
    async def delete_recurrence(
        id: Annotated[str, Field(description="Numeric recurrence ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/recurrences/{id}")
        return {"status": "deleted", "id": id}

    @mcp.tool(
        name="trigger_recurrence",
        description=(
            "Force-fire a recurrence for a specific upcoming date. The "
            "transaction is created NOW (dated today), and will not be "
            "created again on its scheduled date."
        ),
    )
    async def trigger_recurrence(
        id: Annotated[str, Field(description="Numeric recurrence ID.")],
        date: Annotated[
            str,
            Field(
                description=(
                    "YYYY-MM-DD. The future occurrence to consume; pick from "
                    "the recurrence's listed occurrences."
                )
            ),
        ],
    ) -> dict:
        return await request(
            "POST",
            f"/v1/recurrences/{id}/trigger",
            params={"date": date},
        )

    @mcp.tool(
        name="list_recurrence_transactions",
        description=(
            "List transactions previously created by a given recurrence, "
            "optionally filtered by date range and type."
        ),
    )
    async def list_recurrence_transactions(
        id: Annotated[str, Field(description="Numeric recurrence ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
        start: Annotated[
            str | None,
            Field(description="YYYY-MM-DD. Pair with end."),
        ] = None,
        end: Annotated[
            str | None,
            Field(description="YYYY-MM-DD. Pair with start."),
        ] = None,
        type: Annotated[
            str | None,
            Field(
                description=(
                    "Transaction type filter, e.g. 'withdrawal', 'deposit', "
                    "'transfer', 'all'."
                )
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/recurrences/{id}/transactions",
            params={
                "limit": limit,
                "page": page,
                "start": start,
                "end": end,
                "type": type,
            },
        )
