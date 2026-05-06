"""Methodology playbooks for multi-year macro analysis.

Each playbook accepts the common signature (`horizon`, `start`, `end`,
`currency_code`, `accounts`) plus its own extras, and returns a single
user-role message composed by ``macro_body`` from
``firefly_mcp.prompts._methodology``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from ._methodology import CompareAgainst, Horizon, macro_body


def register(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="analyze_trend",
        description=(
            "Trajectory of one financial metric (net worth, savings rate, "
            "spending by category, or income) over the horizon."
        ),
    )
    def analyze_trend(
        dimension: Annotated[
            Literal["net_worth", "savings_rate", "spending_by_category", "income"],
            Field(description="Which metric's trajectory to analyse."),
        ],
        horizon: Annotated[Horizon, Field(description="Time window for the analysis.")] = "last_3y",
        start: Annotated[
            str | None,
            Field(description="YYYY-MM-DD, only used when horizon='custom'."),
        ] = None,
        end: Annotated[
            str | None,
            Field(description="YYYY-MM-DD, only used when horizon='custom'."),
        ] = None,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217. None = use Firefly's primary currency."),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(description="Optional asset/liability account IDs to scope to."),
        ] = None,
    ) -> str:
        methodology = (
            "1. Resolve horizon to start/end. Pick chart bucket: <=4y -> '1M', "
            ">=5y -> '1Y'.\n"
            "2. If currency_code is None, fetch the primary currency via "
            "`get_about`.\n"
            "3. For dimension='net_worth': call `get_account_overview_chart` "
            "with the resolved start/end/period (and `accounts[]` if set, else "
            '`preselected="assets"`); sum balances per bucket.\n'
            "4. For dimension='savings_rate': for each bucket call "
            "`get_income_total` and `get_expense_total`; "
            "savings_rate = (income - expenses) / income.\n"
            "5. For dimension='spending_by_category': call "
            "`get_spending_by_category` per bucket; chart the trajectory of the "
            "top 5 categories by total over the horizon.\n"
            "6. For dimension='income': call `get_income_by_revenue_account` "
            "per bucket.\n"
            "7. Headline metric: start value, end value, and CAGR (or simple "
            "% delta if horizon < 1 year)."
        )
        return macro_body(
            question=f"trajectory of {dimension} over the horizon",
            params={
                "dimension": dimension,
                "horizon": horizon,
                "start": start,
                "end": end,
                "currency_code": currency_code,
                "accounts": accounts,
            },
            methodology=methodology,
        )

    @mcp.prompt(
        name="compare_year_over_year",
        description=(
            "Compare a primary horizon against a comparison horizon (prior "
            "year by default), with deltas per category, budget, and account."
        ),
    )
    def compare_year_over_year(
        horizon: Annotated[Horizon, Field(description="Primary horizon.")] = "ytd",
        start: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        end: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217. None = use Firefly's primary currency."),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(description="Optional asset/liability account IDs to scope to."),
        ] = None,
        compare_against: Annotated[
            CompareAgainst,
            Field(description="What to compare the primary horizon against."),
        ] = "prior_year",
        compare_start: Annotated[
            str | None,
            Field(description="YYYY-MM-DD, used when compare_against='custom'."),
        ] = None,
        compare_end: Annotated[
            str | None,
            Field(description="YYYY-MM-DD, used when compare_against='custom'."),
        ] = None,
    ) -> str:
        methodology = (
            "1. Resolve the primary horizon (start, end). Resolve the comparison "
            "horizon:\n"
            "   - 'prior_year': shift the primary horizon back by exactly 12 "
            "months.\n"
            "   - 'prior_period': same length as primary, ending immediately "
            "before primary's start.\n"
            "   - 'custom': use compare_start/compare_end. Stop and ask if "
            "missing.\n"
            "2. If currency_code is None, fetch primary via `get_about`.\n"
            "3. For each horizon, call `get_basic_summary`, "
            "`get_spending_by_category`, `get_income_by_category`, and "
            "`get_spending_by_budget`.\n"
            "4. For each category and budget compute absolute delta "
            "(primary - comparison) and percent delta "
            "((primary - comparison) / comparison * 100).\n"
            "5. Lead findings: top 5 categories by absolute delta and any "
            "category whose |percent delta| > 15%.\n"
            "6. Output one table of top movers (category, primary, comparison, "
            "delta, %) and one table of budget comparison "
            "(budget, primary spent, comparison spent, delta)."
        )
        return macro_body(
            question="year-over-year comparison",
            params={
                "horizon": horizon,
                "start": start,
                "end": end,
                "currency_code": currency_code,
                "accounts": accounts,
                "compare_against": compare_against,
                "compare_start": compare_start,
                "compare_end": compare_end,
            },
            methodology=methodology,
        )

    @mcp.prompt(
        name="detect_anomalies",
        description=(
            "Find spending spikes vs. rolling average, large outlier "
            "transactions, and unclassified hotspots over the horizon."
        ),
    )
    def detect_anomalies(
        horizon: Annotated[Horizon, Field(description="Time window for the analysis.")] = "last_3y",
        start: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        end: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217. None = use Firefly's primary currency."),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(description="Optional asset/liability account IDs to scope to."),
        ] = None,
        threshold_pct: Annotated[
            float,
            Field(description="Percent over rolling 3-month mean to flag as a spike."),
        ] = 25.0,
    ) -> str:
        methodology = (
            "1. Resolve horizon. If horizon length < 6 months, warn the user "
            "that anomaly detection needs >= 6 months of history and stop.\n"
            "2. If currency_code is None, fetch primary via `get_about`.\n"
            "3. Bucket the horizon into months. For each month, call "
            "`get_spending_by_category`.\n"
            "4. For each category, compute the rolling 3-month mean of "
            "expense. Flag any month whose spend exceeds that mean by >= "
            "`threshold_pct` percent.\n"
            "5. Call `get_expense_by_expense_account` for the full horizon. "
            "For each top expense account, call `search_transactions` "
            "(limit 5) to surface its largest single transactions; flag those "
            "exceeding 3x the median for that account.\n"
            "6. Call `get_expense_no_category` and `get_expense_no_budget` to "
            "surface unclassified spending hotspots.\n"
            "7. Output one table of category spikes (category, month, amount, "
            "baseline, % over) and one table of outlier transactions "
            "(date, amount, account, description). Brief narrative on what "
            "looks new vs. recurring."
        )
        return macro_body(
            question="anomaly detection over the horizon",
            params={
                "horizon": horizon,
                "start": start,
                "end": end,
                "currency_code": currency_code,
                "accounts": accounts,
                "threshold_pct": threshold_pct,
            },
            methodology=methodology,
        )

    @mcp.prompt(
        name="analyze_cash_flow",
        description=(
            "Income vs. expenses bucketed over the horizon, with optional "
            "runway-in-months estimate if income stopped today."
        ),
    )
    def analyze_cash_flow(
        horizon: Annotated[Horizon, Field(description="Time window for the analysis.")] = "last_3y",
        start: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        end: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217. None = use Firefly's primary currency."),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(description="Optional asset/liability account IDs to scope to."),
        ] = None,
        runway_scenario: Annotated[
            bool,
            Field(description="If True, also compute runway months assuming income stops today."),
        ] = False,
    ) -> str:
        methodology = (
            "1. Resolve horizon. Pick chart bucket: <=4y -> '1M', >=5y -> "
            "'1Y'.\n"
            "2. If currency_code is None, fetch primary via `get_about`.\n"
            "3. Call `get_balance_chart` with start/end/period. If `accounts` "
            "is set use it; otherwise preselected='assets'.\n"
            "4. Aggregate per bucket: total income, total expense, net flow. "
            "Compute the monthly average net flow over the horizon.\n"
            "5. If `runway_scenario` is True:\n"
            "   - Call `get_basic_summary` for the current cash position "
            "(sum of asset accounts).\n"
            "   - Compute the average monthly expense over the horizon.\n"
            "   - runway_months = current_cash / avg_monthly_expense.\n"
            "   - State the assumption (zero income from today) explicitly in "
            "the caveats.\n"
            "6. Output one table of per-bucket income/expense/net, optional "
            "runway figure as a headline, and an observation about volatility "
            "(standard deviation of monthly net flow)."
        )
        return macro_body(
            question="cash-flow analysis",
            params={
                "horizon": horizon,
                "start": start,
                "end": end,
                "currency_code": currency_code,
                "accounts": accounts,
                "runway_scenario": runway_scenario,
            },
            methodology=methodology,
        )

    @mcp.prompt(
        name="audit_budget_adherence",
        description=(
            "Per budget, what fraction of months over the horizon stayed "
            "under the limit, and which categories consistently overspend."
        ),
    )
    def audit_budget_adherence(
        horizon: Annotated[Horizon, Field(description="Time window for the analysis.")] = "last_3y",
        start: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        end: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217. None = use Firefly's primary currency."),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(description="Optional asset/liability account IDs to scope to."),
        ] = None,
    ) -> str:
        methodology = (
            "1. Resolve horizon.\n"
            "2. If currency_code is None, fetch primary via `get_about`.\n"
            "3. Call `list_budgets` to enumerate active budgets.\n"
            "4. For each budget, call `list_budget_limits` to retrieve the "
            "limit for each period within the horizon. For each period, call "
            "`get_spending_by_budget` to retrieve the actual spend.\n"
            "5. Per budget compute: months evaluated, months under limit, "
            "adherence_rate = months_under / months_evaluated.\n"
            "6. Flag systematic overspenders (adherence_rate < 50%) and "
            "chronic under-utilisers (adherence_rate == 100% AND average "
            "utilisation < 50%).\n"
            "7. Output one table sorted by adherence ascending (worst first) "
            "with columns: budget, months evaluated, adherence %, average "
            "utilisation %."
        )
        return macro_body(
            question="budget adherence audit",
            params={
                "horizon": horizon,
                "start": start,
                "end": end,
                "currency_code": currency_code,
                "accounts": accounts,
            },
            methodology=methodology,
        )

    @mcp.prompt(
        name="audit_recurring_charges",
        description=(
            "Catalogue all recurring charges (bills + recurring templates), "
            "annualise them, and detect uncatalogued recurring spend."
        ),
    )
    def audit_recurring_charges(
        horizon: Annotated[Horizon, Field(description="Time window for the analysis.")] = "last_3y",
        start: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        end: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217. None = use Firefly's primary currency."),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(description="Optional asset/liability account IDs to scope to."),
        ] = None,
    ) -> str:
        methodology = (
            "1. Resolve horizon.\n"
            "2. If currency_code is None, fetch primary via `get_about`.\n"
            "3. Call `list_bills` (paginate if needed). For each bill, capture "
            "amount range, frequency, and skip pattern; annualise to a yearly "
            "cost.\n"
            "4. Call `list_recurrences`. For each recurrence, capture amount, "
            "type, and frequency; annualise.\n"
            "5. Call `get_expense_no_bill` across the horizon, bucketed "
            "monthly. Flag expense accounts (vendors) that appear in >= 3 of "
            "the last 6 months but are not linked to any bill - likely "
            "uncatalogued recurring charges.\n"
            "6. Output one table of catalogued recurring charges (name, "
            "frequency, monthly equivalent, annual cost) and one table of "
            "suspected uncatalogued recurring charges (vendor, months seen, "
            "average amount). Headline: total annual recurring cost."
        )
        return macro_body(
            question="recurring-charges audit",
            params={
                "horizon": horizon,
                "start": start,
                "end": end,
                "currency_code": currency_code,
                "accounts": accounts,
            },
            methodology=methodology,
        )

    @mcp.prompt(
        name="generate_year_end_report",
        description=(
            "Annual summary for a given tax year: income, expense, by-tag "
            "totals, and capital movement. Overrides the horizon parameter."
        ),
    )
    def generate_year_end_report(
        tax_year: Annotated[
            int,
            Field(description="Calendar year, e.g. 2025. Overrides `horizon`."),
        ],
        horizon: Annotated[
            Horizon,
            Field(description="Ignored; kept for signature uniformity."),
        ] = "custom",
        start: Annotated[str | None, Field(description="Ignored.")] = None,
        end: Annotated[str | None, Field(description="Ignored.")] = None,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217. None = use Firefly's primary currency."),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(description="Optional asset/liability account IDs to scope to."),
        ] = None,
    ) -> str:
        methodology = (
            "1. Set start='{tax_year}-01-01', end='{tax_year}-12-31'. Ignore "
            "the `horizon`, `start`, and `end` parameters - the tax year is "
            "the source of truth.\n"
            "2. If currency_code is None, fetch primary via `get_about`.\n"
            "3. Call `get_basic_summary`, `get_income_total`, "
            "`get_expense_total`, and `get_transfer_total`.\n"
            "4. Call `get_income_by_category`, `get_spending_by_category`, "
            "`get_income_by_revenue_account`, and "
            "`get_expense_by_expense_account`.\n"
            "5. Call `get_income_by_tag` and `get_expense_by_tag` (useful for "
            "deductible / business tags).\n"
            "6. Call `get_account_overview_chart` with period='1M' to "
            "retrieve start-of-year and end-of-year asset balances.\n"
            "7. Output: net worth change (delta assets - delta liabilities), "
            "income breakdown table, expense breakdown table, by-tag table, "
            "and a capital movement summary."
        )
        return macro_body(
            question=f"year-end report for {tax_year}",
            params={
                "tax_year": tax_year,
                "currency_code": currency_code,
                "accounts": accounts,
            },
            methodology=methodology,
        )

    @mcp.prompt(
        name="track_goal_progress",
        description=(
            "Per-piggy-bank progress: current vs. target, monthly "
            "contribution rate, and projected hit date."
        ),
    )
    def track_goal_progress(
        horizon: Annotated[
            Horizon,
            Field(description="Window used to estimate the average contribution rate."),
        ] = "last_year",
        start: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        end: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217. None = use Firefly's primary currency."),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(description="Ignored for piggy banks; kept for signature uniformity."),
        ] = None,
        piggy_bank_name: Annotated[
            str | None,
            Field(description="If set, restrict to this piggy bank only."),
        ] = None,
    ) -> str:
        methodology = (
            "1. Resolve horizon (used for contribution-rate calculation only; "
            "current values are always 'now').\n"
            "2. Call `list_piggy_banks`. If `piggy_bank_name` is given, filter "
            "to the piggy bank whose name matches.\n"
            "3. For each piggy bank in scope:\n"
            "   - Capture current_amount, target_amount, "
            "percent = current/target.\n"
            "   - Call `list_piggy_bank_events` for that piggy bank within "
            "the horizon. Sum positive events (deposits) and divide by the "
            "horizon length in months -> average monthly contribution.\n"
            "   - Projected hit date = today + "
            "(target - current) / monthly_contribution months. If "
            "monthly_contribution <= 0, mark 'no projection'.\n"
            "4. Output one table sorted by % complete descending: name, "
            "current, target, %, monthly contribution, projected hit date. "
            "Narrative flagging any goal stuck at 0 contribution for >= 3 "
            "months."
        )
        return macro_body(
            question="goal progress tracking",
            params={
                "horizon": horizon,
                "start": start,
                "end": end,
                "currency_code": currency_code,
                "piggy_bank_name": piggy_bank_name,
            },
            methodology=methodology,
        )

    @mcp.prompt(
        name="analyze_counterparties",
        description=(
            "Top expense or income counterparties (vendors / sources) over "
            "the horizon, with concentration and new/lost detection."
        ),
    )
    def analyze_counterparties(
        horizon: Annotated[
            Horizon, Field(description="Time window for the analysis.")
        ] = "last_year",
        start: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        end: Annotated[
            str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")
        ] = None,
        currency_code: Annotated[
            str | None,
            Field(description="ISO 4217. None = use Firefly's primary currency."),
        ] = None,
        accounts: Annotated[
            list[int] | None,
            Field(description="Optional asset/liability account IDs to scope to."),
        ] = None,
        direction: Annotated[
            Literal["expense", "income"],
            Field(description="Which side to analyse: vendors (expense) or sources (income)."),
        ] = "expense",
        top_n: Annotated[
            int,
            Field(description="How many top counterparties to return."),
        ] = 20,
    ) -> str:
        methodology = (
            "1. Resolve horizon.\n"
            "2. If currency_code is None, fetch primary via `get_about`.\n"
            "3. If direction='expense': call `get_expense_by_expense_account` "
            "(with `accounts[]` if set). Sort descending by amount, take "
            "top_n.\n"
            "   If direction='income': call `get_income_by_revenue_account` "
            "the same way.\n"
            "4. Compute concentration: top_n's share of the horizon's total "
            "expense (or income).\n"
            "5. Compute the equivalent prior horizon (same length, ending "
            "immediately before start). Run the same call. Identify "
            "counterparties new in the current horizon (absent from prior) "
            "and lost (present in prior, absent now).\n"
            "6. Output one table of top_n counterparties with current "
            "amount, prior amount, and percent change. Concentration figure "
            "as the headline. Brief list of new/lost counterparties."
        )
        return macro_body(
            question=f"top {direction} counterparties over the horizon",
            params={
                "horizon": horizon,
                "start": start,
                "end": end,
                "currency_code": currency_code,
                "accounts": accounts,
                "direction": direction,
                "top_n": top_n,
            },
            methodology=methodology,
        )
