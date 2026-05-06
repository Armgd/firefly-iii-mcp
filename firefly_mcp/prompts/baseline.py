"""Baseline question templates - thin parameterised wrappers, no methodology."""

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="account_balance",
        description=(
            "Ask for the current balance of a named asset or liability account in Firefly III."
        ),
    )
    def account_balance(
        account_name: Annotated[
            str,
            Field(description="Exact name of the account in Firefly III."),
        ],
    ) -> str:
        return f"What is the current balance of the account named '{account_name}'?"

    @mcp.prompt(
        name="recent_transactions",
        description=(
            "Show the most recent transactions, optionally filtered by "
            "account name and/or category name."
        ),
    )
    def recent_transactions(
        count: Annotated[
            int,
            Field(description="How many recent transactions to return."),
        ] = 20,
        account_name: Annotated[
            str | None,
            Field(description="Restrict to this account name, or None for all accounts."),
        ] = None,
        category: Annotated[
            str | None,
            Field(description="Restrict to this category name, or None for all categories."),
        ] = None,
    ) -> str:
        filters: list[str] = []
        if account_name is not None:
            filters.append(f"account '{account_name}'")
        if category is not None:
            filters.append(f"category '{category}'")
        scope = f" filtered by {' and '.join(filters)}" if filters else ""
        return f"Show me my last {count} transactions{scope}, newest first."

    @mcp.prompt(
        name="bill_status",
        description=(
            "Bill status for the current month: which bills are paid, which "
            "are still upcoming, and the next due date for each."
        ),
    )
    def bill_status() -> str:
        return (
            "Show me my bill status for the current month: which bills are paid, "
            "which are upcoming, and the next due date for each."
        )

    @mcp.prompt(
        name="budget_status",
        description=(
            "Per-budget spending for the current period: budgeted vs. spent vs. remaining."
        ),
    )
    def budget_status() -> str:
        return (
            "Show me each budget's spending for the current period: how much was "
            "budgeted, how much has been spent, and the remaining amount."
        )

    @mcp.prompt(
        name="piggy_bank_progress",
        description="Current saved amount vs. target for a named piggy bank goal.",
    )
    def piggy_bank_progress(
        name: Annotated[
            str,
            Field(description="Exact piggy bank name in Firefly III."),
        ],
    ) -> str:
        return (
            f"Show me my progress on the piggy bank named '{name}': "
            "current saved amount, target amount, and percent complete."
        )

    @mcp.prompt(
        name="net_worth_snapshot",
        description="Current total assets, total liabilities, and net worth.",
    )
    def net_worth_snapshot() -> str:
        return (
            "What is my current net worth? Sum total assets and total liabilities, "
            "and report both plus the net figure."
        )
