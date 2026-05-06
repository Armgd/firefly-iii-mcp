# Firefly III MCP — Prompt Set Design

**Date:** 2026-05-06
**Status:** Approved (brainstorming)
**Author:** Nicolas Gras (with Claude)

## Goal

Replace the two trivial inline prompts in `firefly_mcp/server.py` with a curated set of MCP prompts that help an LLM answer real personal-finance questions against Firefly III — especially complex macro analysis spanning multiple years of transactions. The prompts must steer the LLM through ~160 underlying tools without forcing it to discover tool-selection rules on its own.

## Non-goals

- We are not adding any new Firefly III tools or modifying the existing tool surface.
- We are not building a UI; prompts are consumed by MCP-compatible clients (Claude desktop, etc.).
- We are not solving cross-server orchestration or external data ingestion.
- We are not committing to a comprehensive prompt taxonomy — this is a base to iterate on.

## Shape of the solution

A **hybrid** prompt set:

- **9 methodology playbooks** — heavy prompts that encode an analytical workflow plus shared tool-selection rules. They cover the macro / multi-year analyses where naive tool use breaks down.
- **6 baseline question templates** — thin parameterised wrappers around common everyday questions (balance, recent transactions, budget status, etc.).

Methodology playbooks return a single user-role message containing three composed pieces (see "Body content" below). Baseline templates return a single short user message with parameters interpolated — no embedded methodology.

## File layout

Mirrors the existing `firefly_mcp/tools/` module-per-domain pattern.

```
firefly_mcp/
├── server.py              # imports prompt modules, calls register(mcp); inline prompts removed
└── prompts/
    ├── __init__.py
    ├── _methodology.py    # shared constants: MACRO_RULES, OUTPUT_CONTRACT, Horizon, CompareAgainst
    ├── baseline.py        # 6 thin question templates
    └── macro.py           # 9 methodology playbooks
```

Each module exposes `register(mcp: FastMCP) -> None`. `firefly_mcp/server.py` imports them after the existing tool imports and calls `register(mcp)` on each. The two existing inline prompts (`get_account_balance_prompt`, `summarize_spending_by_category_prompt`) are removed; their replacements live in `baseline.py`.

## Shared types (in `_methodology.py`)

```python
from typing import Literal

Horizon = Literal["ytd", "last_year", "last_3y", "last_5y", "all_time", "custom"]
CompareAgainst = Literal["prior_year", "prior_period", "custom"]
```

## Common parameter signature for macro playbooks

Every macro playbook accepts at least these parameters; individual playbooks add their own extras.

```python
horizon: Horizon = "last_3y"
start: str | None = None              # YYYY-MM-DD; used when horizon == "custom"
end: str | None = None                # YYYY-MM-DD; used when horizon == "custom"
currency_code: str | None = None      # None = use Firefly's primary (resolved at runtime via get_about)
accounts: list[int] | None = None     # optional asset/liability filter
```

`horizon` resolution lives in the prompt body (instructions to the LLM), not in Python. Some playbooks (`audit_recurring_charges`, `generate_year_end_report`) do not strictly need every common parameter; we keep the signature uniform anyway because optional params with sensible defaults do not hurt picker UX.

## Currency handling

`currency_code` is optional on every macro playbook. The shared methodology rules instruct the LLM: if `currency_code` is `None`, call `get_about` first to fetch the user's primary currency, then pass it to every subsequent insight call. If multiple currencies still appear in a result (e.g., cross-currency transfers), the LLM reports them separately rather than summing.

## The prompt set

### 6 baseline templates (`prompts/baseline.py`)

| Name | Parameters | Purpose |
|---|---|---|
| `account_balance` | `account_name: str` | Current balance of a named asset/liability account |
| `recent_transactions` | `count: int = 20`, `account_name: str \| None = None`, `category: str \| None = None` | Latest N transactions with optional filters |
| `bill_status` | (none) | Upcoming/paid/unpaid bills this month, next due dates |
| `budget_status` | (none) | Current-period budgeted vs. spent per budget |
| `piggy_bank_progress` | `name: str` | Current saved vs. target for a named goal |
| `net_worth_snapshot` | (none) | Total assets, liabilities, net worth right now |

### 9 methodology playbooks (`prompts/macro.py`)

All take the common signature above plus the extras noted.

| Name | Extra parameters | Purpose |
|---|---|---|
| `analyze_trend` | `dimension: Literal["net_worth", "savings_rate", "spending_by_category", "income"]` | Trajectory of one metric over the horizon, bucketed appropriately |
| `compare_year_over_year` | `compare_against: CompareAgainst = "prior_year"`, `compare_start: str \| None = None`, `compare_end: str \| None = None` | Same period this year vs. another, deltas + % per category/budget/account |
| `detect_anomalies` | `threshold_pct: float = 25.0` | Months where a category spike exceeds rolling average by ≥ threshold; large outlier transactions; new vendors |
| `analyze_cash_flow` | `runway_scenario: bool = False` | Income vs. expenses bucketed; if `runway_scenario`, runway-in-months estimate assuming income stops today |
| `audit_budget_adherence` | (common only) | Per budget, % of months under budget over the horizon and the systematic overspend categories |
| `audit_recurring_charges` | (common only) | Bills + recurring templates grouped, total annualised cost, "uncategorised but recurring" detection |
| `generate_year_end_report` | `tax_year: int` | Annual income, expense, by-tag totals, capital movement; `tax_year` overrides `horizon` |
| `track_goal_progress` | `piggy_bank_name: str \| None = None` | Per piggy bank: progress, projected hit date based on past contribution rate |
| `analyze_counterparties` | `direction: Literal["expense", "income"] = "expense"`, `top_n: int = 20` | Top N expense/revenue accounts (vendors/sources) over the horizon, concentration, new/lost vendors |

## Body content for macro playbooks

Each macro playbook returns a single user-role message composed of three pieces, in this order.

### Piece 1 — Resolved context line

The first paragraph restates the parameters in plain language so the LLM can echo them back to the user:

> You are answering: *{question phrasing}*. Params: horizon={horizon}, start={start}, end={end}, currency_code={currency_code}, accounts={accounts}.

### Piece 2 — Shared tool-selection rules (`MACRO_RULES`)

Defined once in `_methodology.py` and f-string-injected into every macro playbook body:

- Prefer `get_basic_summary`, `/v1/insight/*`, and `/v1/chart/*` over iterating `list_transactions` for any horizon ≥ 3 months. Raw transactions are only for narrow windows or questions no insight endpoint can answer.
- Multi-year horizons require chart `period` ≥ `"1M"`; use `"1Y"` for horizons ≥ 5 years.
- If `currency_code` is `None`, call `get_about` first and use the returned primary currency. Pass `currency_code` to every insight call. If multiple currencies still appear in a result, report them separately — never sum across currencies.
- If `accounts` is provided, pass `accounts[]` on every insight/chart call; otherwise use `preselected="assets"` for cash-flow questions.
- Resolve `horizon` to concrete `start`/`end` BEFORE the first tool call: `ytd` → ({current_year}-01-01, today); `last_year` → previous calendar year; `last_3y` / `last_5y` → today − N years through today; `all_time` → 1970-01-01 through today; `custom` → use the supplied `start`/`end`. If `horizon == "custom"` and `start`/`end` are missing, stop and ask the user before continuing.
- State the resolved horizon, currency, and account scope as the first line of the response.

### Piece 3 — Per-playbook methodology + shared output contract

A short numbered methodology specific to the playbook, followed by the shared `OUTPUT_CONTRACT`:

- Headline line first: `Horizon: {start} → {end}, currency: {code}, accounts: {scope}`.
- Executive summary: 3-5 bullets with the actionable observations and headline numbers.
- Data: ≤ 2 markdown tables of supporting numbers (≤ 15 rows each).
- Caveats: brief note if rows were dropped, currencies mixed, or data clipped.

### Concrete example — `analyze_trend` rendered body

> You are answering: *trajectory of {dimension} over the horizon.*
> Params: horizon={horizon}, start={start}, end={end}, currency_code={currency_code}, accounts={accounts}.
>
> {MACRO_RULES}
>
> Methodology:
> 1. Resolve horizon to start/end. Pick bucket: ≤4y → `"1M"`, ≥5y → `"1Y"`.
> 2. If currency_code is None, fetch primary via `get_about`.
> 3. For `dimension="net_worth"`: call `get_account_overview_chart` with resolved start/end/period (and `accounts[]` if set, else `preselected="assets"`); sum balances per bucket.
> 4. For `dimension="savings_rate"`: for each bucket call `get_income_total` and `get_expense_total`; savings_rate = (income − expenses) / income.
> 5. For `dimension="spending_by_category"`: call `get_spending_by_category` per bucket; trajectory of top 5 categories by total.
> 6. For `dimension="income"`: call `get_income_by_revenue_account` per bucket.
> 7. Headline metric: start value, end value, CAGR (or simple % delta if horizon < 1 year).
>
> {OUTPUT_CONTRACT}

The other 8 playbooks follow the same skeleton — only the "Methodology:" section changes.

## Body content for baseline templates

A single short user-role message with parameters interpolated. No `MACRO_RULES`, no methodology, no `OUTPUT_CONTRACT`. Examples:

- `account_balance("Checking EUR")` → `"What is the current balance of the account named 'Checking EUR'?"`
- `net_worth_snapshot()` → `"What is my current net worth right now? Sum total assets and total liabilities, and report both plus the net figure."`
- `bill_status()` → `"Show me my bill status for the current month: which bills are paid, which are upcoming, and the next due date for each."`

## Server wiring

`firefly_mcp/server.py` changes:

1. Add an import block for the prompt modules alongside the tool imports:
   ```python
   from .prompts import baseline as prompts_baseline, macro as prompts_macro
   ```
2. Call `prompts_baseline.register(mcp)` and `prompts_macro.register(mcp)` after the existing tool registration loop.
3. Remove the two inline `@mcp.prompt` definitions (`get_account_balance_prompt`, `summarize_spending_by_category_prompt`).

## Testing

Out of scope for this design — the project has no test suite yet. Manual verification only:

- `fastmcp dev main.py` and confirm all 15 prompts (6 + 9) appear in the MCP inspector with the documented parameter signatures and descriptions.
- Spot-check 2-3 playbooks (one baseline, one macro) by invoking them through Claude desktop and confirming the rendered message matches the intended structure.

## Open items / future iterations

- No prompt versioning (FastMCP supports it; we will adopt only when we have breaking parameter changes).
- No tags/grouping in the picker UI — could add `tags={"macro"}` / `tags={"baseline"}` later if FastMCP clients start surfacing tags.
- The methodology bodies will need real-world tuning once we see how Claude actually executes them.
