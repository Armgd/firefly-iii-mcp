"""Transaction tools — list, get, search, create (single + split), update,
delete."""

from __future__ import annotations

from datetime import date as date_cls
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..client import request

TransactionType = Literal["withdrawal", "deposit", "transfer"]
TransactionTypeFilter = Literal[
    "all",
    "withdrawal",
    "withdrawals",
    "expense",
    "deposit",
    "deposits",
    "income",
    "transfer",
    "transfers",
    "opening_balance",
    "reconciliation",
]


class TransactionSplit(BaseModel):
    """One leg of a (possibly multi-split) transaction."""

    type: TransactionType = Field(
        description="Direction: withdrawal (out), deposit (in), or transfer (between own accounts)."
    )
    amount: str = Field(description="Decimal string, e.g. ``12.34``.")
    description: str = Field(description="Human-readable description.")
    source_name: str | None = Field(
        default=None,
        description="Name of the source account. Required if source_id not given.",
    )
    source_id: str | None = Field(
        default=None,
        description="Numeric ID of the source account.",
    )
    destination_name: str | None = Field(
        default=None,
        description="Name of the destination account. Required if destination_id not given.",
    )
    destination_id: str | None = Field(
        default=None,
        description="Numeric ID of the destination account.",
    )
    category_name: str | None = Field(
        default=None,
        description="Category name. Will be created if it does not exist.",
    )
    budget_id: str | None = Field(
        default=None,
        description="Numeric budget ID to attach (withdrawals only).",
    )
    tags: list[str] | None = Field(default=None, description="List of tag names.")
    notes: str | None = Field(default=None, description="Free-form notes.")
    date: str | None = Field(
        default=None,
        description="YYYY-MM-DD. Defaults to today.",
    )
    currency_code: str | None = Field(
        default=None,
        description="ISO 4217 currency code (e.g. EUR).",
    )


def _split_to_payload(split: TransactionSplit | dict[str, Any]) -> dict[str, Any]:
    if isinstance(split, BaseModel):
        data = split.model_dump(exclude_none=True)
    else:
        data = {k: v for k, v in split.items() if v is not None}
    data.setdefault("date", date_cls.today().isoformat())
    return data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_transactions",
        description=(
            "List transactions, optionally filtered by date range and/or "
            "type (withdrawal, deposit, transfer). Results are paginated; "
            "use ``page`` and ``limit``. Defaults to the most recent 50."
        ),
    )
    async def list_transactions(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[
            int,
            Field(ge=1, description="1-indexed page number."),
        ] = 1,
        start: Annotated[
            str | None,
            Field(description="YYYY-MM-DD inclusive lower bound."),
        ] = None,
        end: Annotated[
            str | None,
            Field(description="YYYY-MM-DD inclusive upper bound."),
        ] = None,
        type: Annotated[
            TransactionTypeFilter | None,
            Field(description="Filter by transaction direction."),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/transactions",
            params={
                "limit": limit,
                "page": page,
                "start": start,
                "end": end,
                "type": type,
            },
        )

    @mcp.tool(
        name="get_transaction",
        description="Fetch a single transaction (or split group) by its numeric ID.",
    )
    async def get_transaction(
        id: Annotated[str, Field(description="Numeric transaction (group) ID.")],
    ) -> dict:
        return await request("GET", f"/v1/transactions/{id}")

    @mcp.tool(
        name="create_transaction",
        description=(
            "Create a single-leg transaction (one withdrawal, deposit, or "
            "transfer). For multiple splits in one group, use "
            "``create_split_transaction`` instead. Either ``source_name`` or "
            "``source_id`` is required; same for destination."
        ),
    )
    async def create_transaction(
        type: Annotated[
            TransactionType,
            Field(description="withdrawal | deposit | transfer."),
        ],
        amount: Annotated[
            str,
            Field(description="Decimal string, e.g. ``12.34``."),
        ],
        description: Annotated[
            str,
            Field(description="Human-readable description."),
        ],
        source_name: Annotated[
            str | None,
            Field(description="Source account name."),
        ] = None,
        source_id: Annotated[
            str | None,
            Field(description="Source account numeric ID."),
        ] = None,
        destination_name: Annotated[
            str | None,
            Field(description="Destination account name."),
        ] = None,
        destination_id: Annotated[
            str | None,
            Field(description="Destination account numeric ID."),
        ] = None,
        category_name: Annotated[
            str | None,
            Field(description="Category name (created on demand)."),
        ] = None,
        budget_id: Annotated[
            str | None,
            Field(description="Numeric budget ID (withdrawals)."),
        ] = None,
        tags: Annotated[
            list[str] | None,
            Field(description="List of tag names."),
        ] = None,
        notes: Annotated[str | None, Field(description="Free-form notes.")] = None,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217 currency code."),
        ] = None,
        date: Annotated[
            str | None,
            Field(description="YYYY-MM-DD. Defaults to today."),
        ] = None,
        apply_rules: Annotated[
            bool,
            Field(description="Run user rules against the new transaction."),
        ] = True,
        error_if_duplicate_hash: Annotated[
            bool,
            Field(
                description=(
                    "If True, Firefly rejects a transaction whose content hash "
                    "matches an existing one (duplicate detection)."
                )
            ),
        ] = False,
    ) -> dict:
        split = {
            "type": type,
            "amount": amount,
            "description": description,
            "source_name": source_name,
            "source_id": source_id,
            "destination_name": destination_name,
            "destination_id": destination_id,
            "category_name": category_name,
            "budget_id": budget_id,
            "tags": tags,
            "notes": notes,
            "currency_code": currency_code,
            "date": date,
        }
        payload = {
            "error_if_duplicate_hash": error_if_duplicate_hash,
            "apply_rules": apply_rules,
            "transactions": [_split_to_payload(split)],
        }
        return await request("POST", "/v1/transactions", json=payload)

    @mcp.tool(
        name="create_split_transaction",
        description=(
            "Create a transaction group with multiple splits — useful for one "
            "receipt covering several categories or amounts. Provide a list "
            "of splits; each must include ``type``, ``amount``, "
            "``description``, ``source_*`` and ``destination_*``."
        ),
    )
    async def create_split_transaction(
        splits: Annotated[
            list[TransactionSplit],
            Field(min_length=1, description="One entry per split."),
        ],
        group_title: Annotated[
            str | None,
            Field(description="Optional title for the transaction group."),
        ] = None,
        apply_rules: Annotated[
            bool,
            Field(description="Run user rules against the new group."),
        ] = True,
    ) -> dict:
        payload = {
            "error_if_duplicate_hash": False,
            "apply_rules": apply_rules,
            "group_title": group_title,
            "transactions": [_split_to_payload(s) for s in splits],
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return await request("POST", "/v1/transactions", json=payload)

    @mcp.tool(
        name="update_transaction",
        description=(
            "Update fields on an existing transaction. Only the fields you "
            "pass are changed. To re-categorise a transaction, pass "
            "``category_name``."
        ),
    )
    async def update_transaction(
        id: Annotated[str, Field(description="Numeric transaction (group) ID.")],
        description: Annotated[str | None, Field(description="New description.")] = None,
        category_name: Annotated[
            str | None,
            Field(description="Reassign to this category."),
        ] = None,
        budget_id: Annotated[
            str | None,
            Field(description="Reassign to this budget."),
        ] = None,
        tags: Annotated[
            list[str] | None,
            Field(description="Replace tag list."),
        ] = None,
        notes: Annotated[str | None, Field(description="Replace notes.")] = None,
        amount: Annotated[
            str | None,
            Field(description="Decimal string."),
        ] = None,
        date: Annotated[str | None, Field(description="YYYY-MM-DD.")] = None,
    ) -> dict:
        body = {
            "description": description,
            "category_name": category_name,
            "budget_id": budget_id,
            "tags": tags,
            "notes": notes,
            "amount": amount,
            "date": date,
        }
        body = {k: v for k, v in body.items() if v is not None}
        if not body:
            return {"status": "noop", "id": id}
        payload = {"transactions": [body]}
        return await request("PUT", f"/v1/transactions/{id}", json=payload)

    @mcp.tool(
        name="delete_transaction",
        description="Permanently delete a transaction (or group). **Destructive**.",
    )
    async def delete_transaction(
        id: Annotated[str, Field(description="Numeric transaction (group) ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/transactions/{id}")
        return {"status": "deleted", "id": id}

    @mcp.tool(
        name="search_transactions",
        description=(
            "Full-text search across transactions. The ``query`` accepts "
            "Firefly's search operators (e.g. ``description:coffee``, "
            "``amount_more:50``, ``category:Food``)."
        ),
    )
    async def search_transactions(
        query: Annotated[
            str,
            Field(description="Firefly search query string."),
        ],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            "/v1/search/transactions",
            params={"query": query, "limit": limit, "page": page},
        )

    @mcp.tool(
        name="list_transaction_attachments",
        description=(
            "List attachments (receipts, invoices, etc.) linked to a "
            "transaction. Returns metadata only."
        ),
    )
    async def list_transaction_attachments(
        id: Annotated[str, Field(description="Numeric transaction (group) ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/transactions/{id}/attachments",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="list_transaction_piggy_bank_events",
        description=(
            "List piggy bank events triggered by a transaction (e.g. a "
            "transfer that added money to a savings goal)."
        ),
    )
    async def list_transaction_piggy_bank_events(
        id: Annotated[str, Field(description="Numeric transaction (group) ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/transactions/{id}/piggy-bank-events",
            params={"limit": limit, "page": page},
        )
