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
