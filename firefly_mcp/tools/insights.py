"""Insight tools — pre-aggregated summaries and charts.

These endpoints are how Firefly's dashboard answers questions like "what did I
spend by category last month" without you having to fetch and aggregate raw
transactions.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from ..client import request

ChartPeriod = Literal["1D", "1W", "1M", "3M", "6M", "1Y"]
PreselectedAccounts = Literal["empty", "all", "assets", "liabilities"]


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="get_basic_summary",
        description=(
            "Return Firefly's pre-computed summary for a date range: "
            "total earned, total spent, net worth, balance per asset "
            "account, etc. Cheaper than aggregating transactions yourself."
        ),
    )
    async def get_basic_summary(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217 code to convert all values to."),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/summary/basic",
            params={"start": start, "end": end, "currency_code": currency_code},
        )

    @mcp.tool(
        name="get_account_overview_chart",
        description=(
            "Return the dashboard balance-trend chart data over a date "
            "range, one series per asset account."
        ),
    )
    async def get_account_overview_chart(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        period: Annotated[
            ChartPeriod | None,
            Field(description="Bucket size for the chart."),
        ] = None,
        preselected: Annotated[
            PreselectedAccounts | None,
            Field(description="Which set of accounts to include."),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/chart/account/overview",
            params={
                "start": start,
                "end": end,
                "period": period,
                "preselected": preselected,
            },
        )

    @mcp.tool(
        name="get_spending_by_category",
        description=(
            "Total expense per category for the given date range. Returns "
            "a list of ``{name, difference, currency_code, …}`` entries."
        ),
    )
    async def get_spending_by_category(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/expense/category",
            params={"start": start, "end": end},
        )

    @mcp.tool(
        name="get_spending_by_budget",
        description=(
            "Total expense per budget for the given date range. Useful to "
            "see which budgets are tracking high before month-end."
        ),
    )
    async def get_spending_by_budget(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/expense/budget",
            params={"start": start, "end": end},
        )

    @mcp.tool(
        name="get_balance_chart",
        description=(
            "Return the dashboard balance chart: spending vs earning per "
            "asset/liability account, bucketed across the given date range. "
            "Use for cash-flow visualisations."
        ),
    )
    async def get_balance_chart(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        period: Annotated[
            ChartPeriod | None,
            Field(description="Bucket size for the chart."),
        ] = None,
        preselected: Annotated[
            PreselectedAccounts | None,
            Field(description="Which set of accounts to include."),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(
                description=(
                    "Limit to these asset/liability account IDs. "
                    "Overruled by ``preselected`` if both are set."
                ),
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/chart/balance/balance",
            params={
                "start": start,
                "end": end,
                "period": period,
                "preselected": preselected,
                "accounts[]": accounts,
            },
        )

    @mcp.tool(
        name="get_budget_overview_chart",
        description=(
            "Return the dashboard budget-overview chart: budgeted vs spent "
            "per budget for the given date range."
        ),
    )
    async def get_budget_overview_chart(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
    ) -> dict:
        return await request(
            "GET",
            "/v1/chart/budget/overview",
            params={"start": start, "end": end},
        )

    @mcp.tool(
        name="get_category_overview_chart",
        description=(
            "Return the dashboard category-overview chart: spending and "
            "earning per category for the given date range."
        ),
    )
    async def get_category_overview_chart(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
    ) -> dict:
        return await request(
            "GET",
            "/v1/chart/category/overview",
            params={"start": start, "end": end},
        )

    @mcp.tool(
        name="get_expense_by_asset",
        description=(
            "Total expense grouped by asset account (where the money left "
            "from). One row per asset account per currency."
        ),
    )
    async def get_expense_by_asset(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/expense/asset",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_expense_by_bill",
        description=(
            "Total expense grouped by bill. Useful to see actual spending "
            "against each recurring bill for the given date range."
        ),
    )
    async def get_expense_by_bill(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        bills: Annotated[
            list[int] | None,
            Field(description="Limit to these bill IDs."),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/expense/bill",
            params={
                "start": start,
                "end": end,
                "bills[]": bills,
                "accounts[]": accounts,
            },
        )

    @mcp.tool(
        name="get_expense_by_expense_account",
        description=(
            "Total expense grouped by expense account (where the money went "
            "to — vendors, merchants). One row per account per currency."
        ),
    )
    async def get_expense_by_expense_account(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description=(
                    "Limit to these account IDs (asset, liability, or expense "
                    "accounts). Other types are silently ignored."
                ),
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/expense/expense",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_expense_no_bill",
        description=(
            "Sum of expenses NOT linked to any bill, for the given date "
            "range. Useful to spot unbudgeted recurring charges."
        ),
    )
    async def get_expense_no_bill(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/expense/no-bill",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_expense_no_budget",
        description=(
            "Sum of expenses NOT assigned to any budget, for the given "
            "date range. Highlights spending that escaped budgeting."
        ),
    )
    async def get_expense_no_budget(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/expense/no-budget",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_expense_no_category",
        description=(
            "Sum of expenses NOT assigned to any category, for the given "
            "date range. Useful to find uncategorised spending."
        ),
    )
    async def get_expense_no_category(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/expense/no-category",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_expense_no_tag",
        description=("Sum of expenses NOT assigned to any tag, for the given date range."),
    )
    async def get_expense_no_tag(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/expense/no-tag",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_expense_by_tag",
        description=("Total expense grouped by tag. One row per tag per currency."),
    )
    async def get_expense_by_tag(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        tags: Annotated[
            list[int] | None,
            Field(
                description="Limit to these tag IDs (integers, not names).",
            ),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/expense/tag",
            params={
                "start": start,
                "end": end,
                "tags[]": tags,
                "accounts[]": accounts,
            },
        )

    @mcp.tool(
        name="get_expense_total",
        description=(
            "Single-number total of all expenses for the given date range, one row per currency."
        ),
    )
    async def get_expense_total(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/expense/total",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_income_by_asset",
        description=(
            "Total income grouped by asset account (where the money landed). "
            "One row per asset account per currency."
        ),
    )
    async def get_income_by_asset(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/income/asset",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_income_by_category",
        description=(
            "Total income grouped by category for the given date range. "
            "One row per category per currency."
        ),
    )
    async def get_income_by_category(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        categories: Annotated[
            list[int] | None,
            Field(
                description="Limit to these category IDs.",
            ),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/income/category",
            params={
                "start": start,
                "end": end,
                "categories[]": categories,
                "accounts[]": accounts,
            },
        )

    @mcp.tool(
        name="get_income_no_category",
        description=("Sum of income NOT assigned to any category, for the given date range."),
    )
    async def get_income_no_category(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/income/no-category",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_income_no_tag",
        description=("Sum of income NOT assigned to any tag, for the given date range."),
    )
    async def get_income_no_tag(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/income/no-tag",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_income_by_revenue_account",
        description=(
            "Total income grouped by revenue account (the source — employer, "
            "client, etc.). One row per account per currency."
        ),
    )
    async def get_income_by_revenue_account(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description=(
                    "Limit to these account IDs (asset, liability, or revenue "
                    "accounts). Other types are silently ignored."
                ),
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/income/revenue",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_income_by_tag",
        description=("Total income grouped by tag. One row per tag per currency."),
    )
    async def get_income_by_tag(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        tags: Annotated[
            list[int] | None,
            Field(
                description="Limit to these tag IDs (integers, not names).",
            ),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/income/tag",
            params={
                "start": start,
                "end": end,
                "tags[]": tags,
                "accounts[]": accounts,
            },
        )

    @mcp.tool(
        name="get_income_total",
        description=(
            "Single-number total of all income for the given date range, one row per currency."
        ),
    )
    async def get_income_total(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/income/total",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_transfer_by_asset",
        description=(
            "Total transfers grouped by asset/liability account for the "
            "given date range. One row per account per currency."
        ),
    )
    async def get_transfer_by_asset(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description=(
                    "Limit to these asset/liability account IDs. Only "
                    "transfers between included accounts are counted."
                ),
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/transfer/asset",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_transfer_by_category",
        description=("Total transfers grouped by category. One row per category per currency."),
    )
    async def get_transfer_by_category(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        categories: Annotated[
            list[int] | None,
            Field(
                description="Limit to these category IDs.",
            ),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/transfer/category",
            params={
                "start": start,
                "end": end,
                "categories[]": categories,
                "accounts[]": accounts,
            },
        )

    @mcp.tool(
        name="get_transfer_no_category",
        description=("Sum of transfers NOT assigned to any category, for the given date range."),
    )
    async def get_transfer_no_category(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/transfer/no-category",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_transfer_no_tag",
        description=("Sum of transfers NOT assigned to any tag, for the given date range."),
    )
    async def get_transfer_no_tag(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/transfer/no-tag",
            params={"start": start, "end": end, "accounts[]": accounts},
        )

    @mcp.tool(
        name="get_transfer_by_tag",
        description=("Total transfers grouped by tag. One row per tag per currency."),
    )
    async def get_transfer_by_tag(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        tags: Annotated[
            list[int] | None,
            Field(
                description="Limit to these tag IDs (integers, not names).",
            ),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/transfer/tag",
            params={
                "start": start,
                "end": end,
                "tags[]": tags,
                "accounts[]": accounts,
            },
        )

    @mcp.tool(
        name="get_transfer_total",
        description=(
            "Single-number total of all transfers for the given date range, one row per currency."
        ),
    )
    async def get_transfer_total(
        start: Annotated[str, Field(description="YYYY-MM-DD inclusive start.")],
        end: Annotated[str, Field(description="YYYY-MM-DD inclusive end.")],
        accounts: Annotated[
            list[int] | None,
            Field(
                description="Limit to these asset/liability account IDs.",
            ),
        ] = None,
    ) -> dict:
        return await request(
            "GET",
            "/v1/insight/transfer/total",
            params={"start": start, "end": end, "accounts[]": accounts},
        )
