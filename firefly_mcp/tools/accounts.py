"""Account tools — list/get/create/update/delete asset, expense, revenue,
liability accounts."""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from ..client import request

AccountType = Literal[
    "all",
    "asset",
    "cash",
    "expense",
    "revenue",
    "liabilities",
    "liability",
    "default",
    "hidden",
]

AccountRole = Literal[
    "defaultAsset",
    "sharedAsset",
    "savingAsset",
    "ccAsset",
    "cashWalletAsset",
]

CreditCardType = Literal["monthlyFull", "interest"]


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_accounts",
        description=(
            "List Firefly III accounts. Optionally filter by ``type`` "
            "(``asset`` for bank/cash accounts, ``expense`` for places you "
            "pay money to, ``revenue`` for income sources, ``liabilities`` "
            "for debts). Results are paginated; use ``page`` and ``limit``."
        ),
    )
    async def list_accounts(
        type: Annotated[
            AccountType | None,
            Field(description="Filter by account type. Default: all types."),
        ] = None,
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[
            int,
            Field(ge=1, description="1-indexed page number."),
        ] = 1,
        date: Annotated[
            str | None,
            Field(
                description=(
                    "YYYY-MM-DD. Compute account balances as of this date. "
                    "Defaults to today."
                )
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/accounts",
            params={"type": type, "limit": limit, "page": page, "date": date},
        )

    @mcp.tool(
        name="get_account",
        description="Fetch a single account by its numeric ID, including balance and metadata.",
    )
    async def get_account(
        id: Annotated[str, Field(description="Numeric Firefly III account ID.")],
        date: Annotated[
            str | None,
            Field(description="YYYY-MM-DD. Balance as of this date."),
        ] = None,
    ) -> dict:
        return await request("GET", f"/v1/accounts/{id}", params={"date": date})

    @mcp.tool(
        name="create_account",
        description=(
            "Create a new account. ``name`` and ``type`` are required. For "
            "asset accounts you typically also want ``account_role`` (e.g. "
            "``defaultAsset``) and ``currency_code`` (ISO 4217). For credit "
            "cards set ``account_role=ccAsset`` plus ``credit_card_type`` "
            "and ``monthly_payment_date``."
        ),
    )
    async def create_account(
        name: Annotated[str, Field(description="Display name of the account.")],
        type: Annotated[
            AccountType,
            Field(description="Account type — most often ``asset`` or ``liabilities``."),
        ],
        account_role: Annotated[
            AccountRole | None,
            Field(description="Asset account role. Required when type=asset."),
        ] = None,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217 currency code (e.g. EUR, USD)."),
        ] = None,
        opening_balance: Annotated[
            str | None,
            Field(description="Decimal string opening balance (e.g. ``1000.00``)."),
        ] = None,
        opening_balance_date: Annotated[
            str | None,
            Field(description="YYYY-MM-DD date of the opening balance."),
        ] = None,
        credit_card_type: Annotated[
            CreditCardType | None,
            Field(description="Required when account_role=ccAsset."),
        ] = None,
        monthly_payment_date: Annotated[
            str | None,
            Field(description="YYYY-MM-DD. Required when account_role=ccAsset."),
        ] = None,
        notes: Annotated[
            str | None,
            Field(description="Free-form notes (markdown supported)."),
        ] = None,
    ) -> dict:
        body = {
            "name": name,
            "type": type,
            "account_role": account_role,
            "currency_code": currency_code,
            "opening_balance": opening_balance,
            "opening_balance_date": opening_balance_date,
            "credit_card_type": credit_card_type,
            "monthly_payment_date": monthly_payment_date,
            "notes": notes,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("POST", "/v1/accounts", json=body)

    @mcp.tool(
        name="update_account",
        description=(
            "Update an existing account. Only the fields you pass are "
            "changed. Common fields: ``name``, ``active``, ``notes``."
        ),
    )
    async def update_account(
        id: Annotated[str, Field(description="Numeric Firefly III account ID.")],
        name: Annotated[str | None, Field(description="New name.")] = None,
        active: Annotated[
            bool | None,
            Field(description="Toggle whether the account is active."),
        ] = None,
        notes: Annotated[str | None, Field(description="New notes.")] = None,
        currency_code: Annotated[
            str | None,
            Field(description="New ISO 4217 currency code."),
        ] = None,
    ) -> dict:
        body = {
            "name": name,
            "active": active,
            "notes": notes,
            "currency_code": currency_code,
        }
        body = {k: v for k, v in body.items() if v is not None}
        return await request("PUT", f"/v1/accounts/{id}", json=body)

    @mcp.tool(
        name="delete_account",
        description=(
            "Permanently delete an account. **Destructive**: also removes "
            "all transactions linked to this account."
        ),
    )
    async def delete_account(
        id: Annotated[str, Field(description="Numeric Firefly III account ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/accounts/{id}")
        return {"status": "deleted", "id": id}

    @mcp.tool(
        name="list_account_attachments",
        description=(
            "List attachments uploaded to an account (receipts, statements, "
            "etc.). Returns metadata only; use ``download_attachment`` to "
            "fetch file bytes."
        ),
    )
    async def list_account_attachments(
        id: Annotated[str, Field(description="Numeric Firefly III account ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/accounts/{id}/attachments",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="list_account_piggy_banks",
        description=(
            "List piggy banks (savings goals) hosted inside this asset "
            "account."
        ),
    )
    async def list_account_piggy_banks(
        id: Annotated[str, Field(description="Numeric Firefly III account ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/accounts/{id}/piggy-banks",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="list_account_transactions",
        description=(
            "List transactions linked to a specific account, optionally "
            "filtered by date range and/or transaction type."
        ),
    )
    async def list_account_transactions(
        id: Annotated[str, Field(description="Numeric Firefly III account ID.")],
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
            f"/v1/accounts/{id}/transactions",
            params={
                "limit": limit,
                "page": page,
                "start": start,
                "end": end,
                "type": type,
            },
        )
