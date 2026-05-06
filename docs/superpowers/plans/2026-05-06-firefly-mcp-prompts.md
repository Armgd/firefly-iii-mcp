# Firefly III MCP — Prompt Set Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two trivial inline prompts in `firefly_mcp/server.py` with a hybrid prompt set — 6 baseline question templates + 9 methodology playbooks — that steers the LLM through the existing ~160 Firefly III tools, especially for multi-year macro analysis.

**Architecture:** New `firefly_mcp/prompts/` package mirroring the existing `firefly_mcp/tools/` module-per-domain pattern. Three modules: `_methodology.py` (shared types and constants), `baseline.py` (6 thin wrappers), `macro.py` (9 methodology playbooks). Each module exposes `register(mcp: FastMCP) -> None` and is wired into `server.py` next to the existing tool registrations.

**Tech Stack:** Python 3.12, FastMCP ≥ 3.0, Pydantic ≥ 2.7. No new runtime dependencies. No test suite (project has none yet — verification is by import + ruff + a smoke-script).

**Spec:** `docs/superpowers/specs/2026-05-06-firefly-mcp-prompts-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `firefly_mcp/prompts/__init__.py` | Create | Package marker, one-line module docstring. |
| `firefly_mcp/prompts/_methodology.py` | Create | Shared `Horizon` / `CompareAgainst` literal types, `MACRO_RULES` and `OUTPUT_CONTRACT` text constants, `macro_body()` helper that composes the 3-piece body. |
| `firefly_mcp/prompts/baseline.py` | Create | `register(mcp)` defining the 6 baseline prompts (`account_balance`, `recent_transactions`, `bill_status`, `budget_status`, `piggy_bank_progress`, `net_worth_snapshot`). |
| `firefly_mcp/prompts/macro.py` | Create | `register(mcp)` defining the 9 macro playbooks (`analyze_trend`, `compare_year_over_year`, `detect_anomalies`, `analyze_cash_flow`, `audit_budget_adherence`, `audit_recurring_charges`, `generate_year_end_report`, `track_goal_progress`, `analyze_counterparties`). |
| `firefly_mcp/server.py` | Modify | Import the prompt modules, call their `register()` after the tool loop, delete the two inline `@mcp.prompt` definitions. |

---

## Working Conventions

- All files start with `from __future__ import annotations` (project convention).
- Module docstrings are one-line.
- Ruff line-length is 100. Run `ruff check .` and `ruff format .` after every file edit.
- Conventional Commits required (semantic-release): use `feat:` for new prompts and `refactor:` for the server.py rewiring.
- Verify after every task with `python -c "import firefly_mcp.server"` — any registration error surfaces immediately at import time.

---

## Task 1: Create the prompts package skeleton

**Files:**
- Create: `firefly_mcp/prompts/__init__.py`

- [ ] **Step 1: Create the package marker file**

Write `firefly_mcp/prompts/__init__.py`:

```python
"""Prompt modules. Each exposes ``register(mcp)``."""
```

- [ ] **Step 2: Verify the package imports**

Run: `python -c "import firefly_mcp.prompts"`
Expected: exits 0 with no output.

- [ ] **Step 3: Lint**

Run: `ruff check firefly_mcp/prompts/`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add firefly_mcp/prompts/__init__.py
git commit -m "feat(prompts): add prompts package skeleton"
```

---

## Task 2: Add the shared methodology module

**Files:**
- Create: `firefly_mcp/prompts/_methodology.py`

- [ ] **Step 1: Create the methodology module**

Write `firefly_mcp/prompts/_methodology.py`:

```python
"""Shared types, rule text, and body composer for Firefly III macro prompts."""

from __future__ import annotations

from typing import Literal

Horizon = Literal["ytd", "last_year", "last_3y", "last_5y", "all_time", "custom"]
CompareAgainst = Literal["prior_year", "prior_period", "custom"]

MACRO_RULES = """\
TOOL-SELECTION RULES (apply in order):
- Prefer `get_basic_summary`, `/v1/insight/*`, and `/v1/chart/*` over iterating
  `list_transactions` for any horizon >= 3 months. Raw transactions are only
  for narrow windows or questions no insight endpoint can answer.
- Multi-year horizons require chart `period` >= "1M"; use "1Y" for horizons
  >= 5 years.
- If `currency_code` is None, call `get_about` first and use the returned
  primary currency. Pass `currency_code` to every insight call. If multiple
  currencies still appear in a result, report them separately - never sum
  across currencies.
- If `accounts` is provided, pass `accounts[]` on every insight/chart call;
  otherwise use `preselected="assets"` for cash-flow questions.
- Resolve `horizon` to concrete `start`/`end` BEFORE the first tool call:
    - "ytd"        -> ({current_year}-01-01, today)
    - "last_year"  -> previous calendar year (Jan 1 to Dec 31)
    - "last_3y"    -> today - 3 years through today
    - "last_5y"    -> today - 5 years through today
    - "all_time"   -> 1970-01-01 through today
    - "custom"     -> use the supplied `start`/`end`
  If `horizon == "custom"` and `start`/`end` are missing, stop and ask the
  user before continuing.
- State the resolved horizon, currency, and account scope as the first line
  of the response."""

OUTPUT_CONTRACT = """\
OUTPUT CONTRACT:
1. Headline line: `Horizon: {start} -> {end}, currency: {code}, accounts: {scope}`.
2. Executive summary: 3-5 bullets with the actionable observations and
   headline numbers.
3. Data: at most 2 markdown tables of supporting numbers, <= 15 rows each.
4. Caveats: a brief note if rows were dropped, currencies were mixed, or
   the data was clipped at either end of the horizon."""


def macro_body(*, question: str, params: dict[str, object], methodology: str) -> str:
    """Compose the standard 3-piece body for a macro playbook.

    The result is a single user-role message: framing line, params line,
    shared rules, per-playbook methodology, then the output contract.
    """
    params_str = ", ".join(f"{k}={v!r}" for k, v in params.items())
    return (
        f"You are answering: *{question}*.\n"
        f"Params: {params_str}.\n\n"
        f"{MACRO_RULES}\n\n"
        f"Methodology:\n{methodology}\n\n"
        f"{OUTPUT_CONTRACT}"
    )
```

- [ ] **Step 2: Verify the module imports and the helper works**

Run:

```bash
python -c "
from firefly_mcp.prompts._methodology import macro_body, MACRO_RULES, OUTPUT_CONTRACT
body = macro_body(question='test', params={'horizon': 'ytd'}, methodology='1. Do thing.')
assert 'TOOL-SELECTION RULES' in body
assert 'Methodology:' in body
assert 'OUTPUT CONTRACT' in body
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3: Lint and format**

Run: `ruff check firefly_mcp/prompts/_methodology.py && ruff format --check firefly_mcp/prompts/_methodology.py`
Expected: no errors. If format fails, run `ruff format firefly_mcp/prompts/_methodology.py` and re-check.

- [ ] **Step 4: Commit**

```bash
git add firefly_mcp/prompts/_methodology.py
git commit -m "feat(prompts): add shared methodology constants and body composer"
```

---

## Task 3: Add the baseline prompt module

**Files:**
- Create: `firefly_mcp/prompts/baseline.py`

- [ ] **Step 1: Create the baseline module with all 6 prompts**

Write `firefly_mcp/prompts/baseline.py`:

```python
"""Baseline question templates - thin parameterised wrappers, no methodology."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="account_balance",
        description=(
            "Ask for the current balance of a named asset or liability "
            "account in Firefly III."
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
            "Per-budget spending for the current period: budgeted vs. spent "
            "vs. remaining."
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
```

- [ ] **Step 2: Verify the module imports and registers 6 prompts**

Run:

```bash
python -c "
import asyncio
from fastmcp import FastMCP
from firefly_mcp.prompts import baseline

async def main():
    mcp = FastMCP(name='test')
    baseline.register(mcp)
    prompts = await mcp.get_prompts()
    names = sorted(prompts)
    expected = sorted([
        'account_balance', 'recent_transactions', 'bill_status',
        'budget_status', 'piggy_bank_progress', 'net_worth_snapshot',
    ])
    assert names == expected, f'got {names}'
    print(f'OK: {len(names)} baseline prompts registered')

asyncio.run(main())
"
```

Expected: `OK: 6 baseline prompts registered`.

If `mcp.get_prompts()` does not exist in the installed FastMCP version, fall back to `await mcp._mcp_server.list_prompts()` or inspect `mcp._prompt_manager._prompts.keys()` — adjust the smoke script and continue.

- [ ] **Step 3: Lint and format**

Run: `ruff check firefly_mcp/prompts/baseline.py && ruff format --check firefly_mcp/prompts/baseline.py`
Expected: no errors. If format fails, run `ruff format firefly_mcp/prompts/baseline.py` and re-check.

- [ ] **Step 4: Commit**

```bash
git add firefly_mcp/prompts/baseline.py
git commit -m "feat(prompts): add baseline question templates"
```

---

## Task 4: Add the macro playbook module

**Files:**
- Create: `firefly_mcp/prompts/macro.py`

This is the heaviest task — 9 playbook functions in one file. Each playbook has the same shape: take the common params (plus its own extras), call `macro_body()` with a question string and a per-playbook `methodology` string, return the result.

- [ ] **Step 1: Create the macro module shell with imports and the empty `register()`**

Write the top of `firefly_mcp/prompts/macro.py`:

```python
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
    # Playbook definitions follow in subsequent steps.
    pass
```

Do not commit yet — this file will be filled in over the following steps before the first verification.

- [ ] **Step 2: Add the `analyze_trend` playbook**

Inside `register()` (replace the `pass`), add:

```python
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
            "`preselected=\"assets\"`); sum balances per bucket.\n"
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
```

- [ ] **Step 3: Add the `compare_year_over_year` playbook**

Append inside `register()`:

```python
    @mcp.prompt(
        name="compare_year_over_year",
        description=(
            "Compare a primary horizon against a comparison horizon (prior "
            "year by default), with deltas per category, budget, and account."
        ),
    )
    def compare_year_over_year(
        horizon: Annotated[Horizon, Field(description="Primary horizon.")] = "ytd",
        start: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
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
```

- [ ] **Step 4: Add the `detect_anomalies` playbook**

Append inside `register()`:

```python
    @mcp.prompt(
        name="detect_anomalies",
        description=(
            "Find spending spikes vs. rolling average, large outlier "
            "transactions, and unclassified hotspots over the horizon."
        ),
    )
    def detect_anomalies(
        horizon: Annotated[Horizon, Field(description="Time window for the analysis.")] = "last_3y",
        start: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
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
```

- [ ] **Step 5: Add the `analyze_cash_flow` playbook**

Append inside `register()`:

```python
    @mcp.prompt(
        name="analyze_cash_flow",
        description=(
            "Income vs. expenses bucketed over the horizon, with optional "
            "runway-in-months estimate if income stopped today."
        ),
    )
    def analyze_cash_flow(
        horizon: Annotated[Horizon, Field(description="Time window for the analysis.")] = "last_3y",
        start: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
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
```

- [ ] **Step 6: Add the `audit_budget_adherence` playbook**

Append inside `register()`:

```python
    @mcp.prompt(
        name="audit_budget_adherence",
        description=(
            "Per budget, what fraction of months over the horizon stayed "
            "under the limit, and which categories consistently overspend."
        ),
    )
    def audit_budget_adherence(
        horizon: Annotated[Horizon, Field(description="Time window for the analysis.")] = "last_3y",
        start: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
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
```

- [ ] **Step 7: Add the `audit_recurring_charges` playbook**

Append inside `register()`:

```python
    @mcp.prompt(
        name="audit_recurring_charges",
        description=(
            "Catalogue all recurring charges (bills + recurring templates), "
            "annualise them, and detect uncatalogued recurring spend."
        ),
    )
    def audit_recurring_charges(
        horizon: Annotated[Horizon, Field(description="Time window for the analysis.")] = "last_3y",
        start: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
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
```

- [ ] **Step 8: Add the `generate_year_end_report` playbook**

Append inside `register()`:

```python
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
```

- [ ] **Step 9: Add the `track_goal_progress` playbook**

Append inside `register()`:

```python
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
        start: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
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
```

- [ ] **Step 10: Add the `analyze_counterparties` playbook**

Append inside `register()`:

```python
    @mcp.prompt(
        name="analyze_counterparties",
        description=(
            "Top expense or income counterparties (vendors / sources) over "
            "the horizon, with concentration and new/lost detection."
        ),
    )
    def analyze_counterparties(
        horizon: Annotated[Horizon, Field(description="Time window for the analysis.")] = "last_year",
        start: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
        end: Annotated[str | None, Field(description="YYYY-MM-DD, used when horizon='custom'.")] = None,
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
```

- [ ] **Step 11: Verify the module imports and registers all 9 playbooks**

Run:

```bash
python -c "
import asyncio
from fastmcp import FastMCP
from firefly_mcp.prompts import macro

async def main():
    mcp = FastMCP(name='test')
    macro.register(mcp)
    prompts = await mcp.get_prompts()
    names = sorted(prompts)
    expected = sorted([
        'analyze_trend', 'compare_year_over_year', 'detect_anomalies',
        'analyze_cash_flow', 'audit_budget_adherence',
        'audit_recurring_charges', 'generate_year_end_report',
        'track_goal_progress', 'analyze_counterparties',
    ])
    assert names == expected, f'got {names}'
    print(f'OK: {len(names)} macro playbooks registered')

asyncio.run(main())
"
```

Expected: `OK: 9 macro playbooks registered`.

If `mcp.get_prompts()` is missing in the installed FastMCP version, fall back to `mcp._prompt_manager._prompts.keys()` and adjust the script.

- [ ] **Step 12: Lint and format**

Run: `ruff check firefly_mcp/prompts/macro.py && ruff format --check firefly_mcp/prompts/macro.py`
Expected: no errors. If format fails, run `ruff format firefly_mcp/prompts/macro.py` and re-check.

- [ ] **Step 13: Commit**

```bash
git add firefly_mcp/prompts/macro.py
git commit -m "feat(prompts): add 9 macro methodology playbooks"
```

---

## Task 5: Wire prompt modules into the server, remove inline prompts

**Files:**
- Modify: `firefly_mcp/server.py` — add prompt imports below the existing `from .tools import (...)` block, register the prompt modules after the existing registration loop, and delete the two inline `@mcp.prompt` definitions (`get_account_balance_prompt`, `summarize_spending_by_category_prompt`).

- [ ] **Step 1: Re-read the current `server.py` to confirm structure**

Run: `cat -n firefly_mcp/server.py`

Confirm the file still contains:
- A `from .tools import (...)` block.
- A `for module in (...): module.register(mcp)` loop.
- Two inline `@mcp.prompt` definitions (`get_account_balance_prompt`, `summarize_spending_by_category_prompt`).
- A `health_check` route and `app = mcp.http_app()` at the bottom.

Anchor edits to the surrounding text rather than line numbers.

- [ ] **Step 2: Add the prompt-module imports**

Add this import block immediately after the existing `from .tools import (...)` block in `firefly_mcp/server.py`:

```python
from .prompts import baseline as prompts_baseline, macro as prompts_macro
```

- [ ] **Step 3: Register the prompt modules**

Immediately after the existing `for module in (...): module.register(mcp)` loop, add:

```python
prompts_baseline.register(mcp)
prompts_macro.register(mcp)
```

- [ ] **Step 4: Delete the two inline prompts**

Remove the entire block:

```python
@mcp.prompt
def get_account_balance_prompt(account_name: str) -> str:
    """Prompt asking for the current balance of a specific account."""
    return f"What is the current balance of the account named '{account_name}'?"


@mcp.prompt
def summarize_spending_by_category_prompt(start_date: str, end_date: str) -> str:
    """Prompt summarizing spending by category between two YYYY-MM-DD dates."""
    return (
        "Please provide a summary of my spending by category from "
        f"{start_date} to {end_date}."
    )
```

After this step, the bottom of `server.py` should be the `health_check` route followed directly by `app = mcp.http_app()`.

- [ ] **Step 5: Verify the server module imports cleanly and registers all 15 prompts**

Run:

```bash
python -c "
import asyncio
from firefly_mcp.server import mcp

async def main():
    prompts = await mcp.get_prompts()
    names = sorted(prompts)
    expected = sorted([
        # baseline (6)
        'account_balance', 'recent_transactions', 'bill_status',
        'budget_status', 'piggy_bank_progress', 'net_worth_snapshot',
        # macro (9)
        'analyze_trend', 'compare_year_over_year', 'detect_anomalies',
        'analyze_cash_flow', 'audit_budget_adherence',
        'audit_recurring_charges', 'generate_year_end_report',
        'track_goal_progress', 'analyze_counterparties',
    ])
    assert names == expected, f'expected {expected}, got {names}'
    print(f'OK: {len(names)} prompts registered')
    assert 'get_account_balance_prompt' not in prompts
    assert 'summarize_spending_by_category_prompt' not in prompts
    print('OK: legacy prompts removed')

asyncio.run(main())
"
```

Expected:
```
OK: 15 prompts registered
OK: legacy prompts removed
```

- [ ] **Step 6: Render one prompt to confirm body composition**

Run:

```bash
python -c "
import asyncio
from firefly_mcp.server import mcp

async def main():
    result = await mcp.get_prompt('analyze_trend', {'dimension': 'net_worth'})
    body = result.messages[0].content.text if result.messages else ''
    assert 'TOOL-SELECTION RULES' in body, 'MACRO_RULES missing'
    assert 'OUTPUT CONTRACT' in body, 'OUTPUT_CONTRACT missing'
    assert 'Methodology:' in body, 'methodology section missing'
    print('OK: analyze_trend body composed correctly')

asyncio.run(main())
"
```

Expected: `OK: analyze_trend body composed correctly`.

If the FastMCP render API exposes message content differently (e.g. `result.messages[0].content` is itself a string in this version), adjust the attribute lookup until the assertion runs.

- [ ] **Step 7: Lint and format the modified server file**

Run: `ruff check firefly_mcp/server.py && ruff format --check firefly_mcp/server.py`
Expected: no errors. If format fails, run `ruff format firefly_mcp/server.py` and re-check.

- [ ] **Step 8: Commit**

```bash
git add firefly_mcp/server.py
git commit -m "refactor(server): wire new prompt modules and drop inline prompts"
```

---

## Task 6: Final manual smoke (operator step, optional)

**Files:** none.

- [ ] **Step 1: Boot the server in dev mode and inspect the prompt list**

Run: `fastmcp dev main.py`

In the MCP inspector that opens, navigate to the **Prompts** tab and confirm:

- 15 prompts listed (6 baseline + 9 macro).
- The macro playbooks show the documented parameters (`horizon`, `start`, `end`, `currency_code`, `accounts`, plus per-playbook extras).
- Invoking `analyze_trend` with `dimension="net_worth"` renders a body containing the framing line, the `TOOL-SELECTION RULES` block, the `Methodology:` section, and the `OUTPUT CONTRACT`.

This step is not required to "pass" the plan — it is a final eyeball check before relying on the prompts in a real Claude desktop session.

---

## Self-review notes

- **Spec coverage:** every section of `2026-05-06-firefly-mcp-prompts-design.md` maps to at least one task: file layout → all tasks; shared types and constants → Task 2; baseline templates → Task 3; macro playbooks → Task 4 (one step per playbook); server wiring → Task 5; manual verification → Task 6.
- **Type consistency:** `Horizon` and `CompareAgainst` are defined once in `_methodology.py` (Task 2) and referenced consistently in `macro.py` (Task 4). The `register(mcp: FastMCP) -> None` signature matches the existing tool-module pattern.
- **No placeholders:** every prompt body, methodology, and verification command is shown in full.
- **Risk:** the FastMCP introspection API used in verification (`mcp.get_prompts()`, `mcp.get_prompt(name, args)`) may differ slightly between FastMCP minor versions; the verification steps note fallback paths so the engineer can adapt without abandoning the smoke check.
