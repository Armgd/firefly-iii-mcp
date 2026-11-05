import json

import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    ("tool", "args", "path", "params"),
    [
        (
            "count_transactions",
            {"external_identifier": "bank-123"},
            "/api/v1/search/transactions/count",
            {"external_identifier": "bank-123"},
        ),
        (
            "list_piggy_bank_accounts",
            {"id": "7"},
            "/api/v1/piggy-banks/7/accounts",
            {"limit": "50", "page": "1"},
        ),
        (
            "list_currency_exchange_rates",
            {"code": "EUR"},
            "/api/v1/currencies/EUR/cer",
            {"limit": "50", "page": "1"},
        ),
        (
            "get_budget_limits_overview_chart",
            {"start": "2026-01-01", "end": "2026-01-31"},
            "/api/v1/chart/budget/overview-with-limits",
            {"start": "2026-01-01", "end": "2026-01-31"},
        ),
        (
            "validate_rule_expression",
            {"expression": "description ~ 'x'"},
            "/api/v1/rules/validate-expression",
            {"expression": "description ~ 'x'"},
        ),
        (
            "autocomplete_transactions_with_meta",
            {"query": "rent"},
            "/api/v1/autocomplete/transactions-with-meta",
            {"query": "rent", "limit": "10"},
        ),
        (
            "list_accounts",
            {"active": False},
            "/api/v1/accounts",
            {"active": "false"},
        ),
    ],
)
async def test_tool_calls_expected_endpoint(firefly, mcp_client, tool, args, path, params):
    await mcp_client.call_tool(tool, args)

    assert firefly.last.method == "GET"
    assert firefly.last.url.path == path
    assert params.items() <= dict(firefly.last.url.params).items()


@pytest.mark.parametrize(
    ("tool", "args", "method", "path"),
    [
        ("create_category", {"name": "Food", "color": "FF0000"}, "POST", "/api/v1/categories"),
        ("update_category", {"id": "3", "color": "00FF00"}, "PUT", "/api/v1/categories/3"),
    ],
)
async def test_category_color_is_sent(firefly, mcp_client, tool, args, method, path):
    await mcp_client.call_tool(tool, args)

    assert firefly.last.method == method
    assert firefly.last.url.path == path
    assert json.loads(firefly.last.content)["color"] == args["color"]


async def test_lookups_removed_from_firefly_are_gone(mcp_client):
    names = {t.name for t in await mcp_client.list_tools()}

    assert names.isdisjoint(
        {
            "autocomplete_currencies_with_code",
            "autocomplete_piggy_banks_with_balance",
            "autocomplete_transactions_with_id",
        }
    )
