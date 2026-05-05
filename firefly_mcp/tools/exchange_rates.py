"""Exchange-rate tools — manage currency exchange rates and date-keyed series."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..client import request


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="list_exchange_rates",
        description="List all exchange rates known to Firefly III.",
    )
    async def list_exchange_rates(
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            "/v1/exchange-rates",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="create_exchange_rate",
        description=(
            "Store a new exchange rate for a currency pair on a specific date. "
            "If a rate already exists for this pair+date it is updated instead."
        ),
    )
    async def create_exchange_rate(
        from_: Annotated[
            str,
            Field(alias="from", description="Base currency code (e.g. 'USD')."),
        ],
        to: Annotated[str, Field(description="Destination currency code (e.g. 'EUR').")],
        date: Annotated[str, Field(description="YYYY-MM-DD date this rate applies.")],
        rate: Annotated[
            str,
            Field(description="Decimal rate as a string, e.g. '1.10340'."),
        ],
    ) -> dict:
        body = {"from": from_, "to": to, "date": date, "rate": rate}
        return await request("POST", "/v1/exchange-rates", json=body)

    @mcp.tool(
        name="get_exchange_rate_pair",
        description="List all historical exchange rates for a currency pair.",
    )
    async def get_exchange_rate_pair(
        from_: Annotated[
            str,
            Field(alias="from", description="Base currency code."),
        ],
        to: Annotated[str, Field(description="Destination currency code.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/exchange-rates/{from_}/{to}",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="delete_exchange_rate_pair",
        description=(
            "Delete ALL exchange rates for a currency pair (one direction only). "
            "Reverse-direction rates are kept. **Destructive**."
        ),
    )
    async def delete_exchange_rate_pair(
        from_: Annotated[
            str,
            Field(alias="from", description="Base currency code."),
        ],
        to: Annotated[str, Field(description="Destination currency code.")],
    ) -> dict:
        await request("DELETE", f"/v1/exchange-rates/{from_}/{to}")
        return {"status": "deleted", "from": from_, "to": to}

    @mcp.tool(
        name="get_exchange_rate_on_date",
        description="Fetch the exchange rate for a currency pair on a specific date.",
    )
    async def get_exchange_rate_on_date(
        from_: Annotated[
            str,
            Field(alias="from", description="Base currency code."),
        ],
        to: Annotated[str, Field(description="Destination currency code.")],
        date: Annotated[str, Field(description="YYYY-MM-DD date.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/exchange-rates/{from_}/{to}/{date}",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="update_exchange_rate_on_date",
        description=(
            "Update the exchange rate for a currency pair on a specific date. "
            "Only the ``rate`` field is required."
        ),
    )
    async def update_exchange_rate_on_date(
        from_: Annotated[
            str,
            Field(alias="from", description="Base currency code."),
        ],
        to: Annotated[str, Field(description="Destination currency code.")],
        date: Annotated[str, Field(description="YYYY-MM-DD date.")],
        rate: Annotated[str, Field(description="New decimal rate as a string.")],
    ) -> dict:
        return await request(
            "PUT",
            f"/v1/exchange-rates/{from_}/{to}/{date}",
            json={"rate": rate},
        )

    @mcp.tool(
        name="delete_exchange_rate_on_date",
        description=(
            "Delete the exchange rate for a currency pair on a specific date. "
            "Reverse-direction rate is kept. **Destructive**."
        ),
    )
    async def delete_exchange_rate_on_date(
        from_: Annotated[
            str,
            Field(alias="from", description="Base currency code."),
        ],
        to: Annotated[str, Field(description="Destination currency code.")],
        date: Annotated[str, Field(description="YYYY-MM-DD date.")],
    ) -> dict:
        await request("DELETE", f"/v1/exchange-rates/{from_}/{to}/{date}")
        return {"status": "deleted", "from": from_, "to": to, "date": date}

    @mcp.tool(
        name="get_exchange_rate",
        description="Fetch a single exchange rate entry by its numeric ID.",
    )
    async def get_exchange_rate(
        id: Annotated[str, Field(description="Numeric exchange-rate ID.")],
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Items per page (default 50)."),
        ] = 50,
        page: Annotated[int, Field(ge=1, description="1-indexed page.")] = 1,
    ) -> dict:
        return await request(
            "GET",
            f"/v1/exchange-rates/{id}",
            params={"limit": limit, "page": page},
        )

    @mcp.tool(
        name="update_exchange_rate",
        description=(
            "Update an exchange rate entry by ID. ``date`` and ``rate`` are "
            "required; ``from``/``to`` may be supplied to reassign the pair."
        ),
    )
    async def update_exchange_rate(
        id: Annotated[str, Field(description="Numeric exchange-rate ID.")],
        date: Annotated[str, Field(description="YYYY-MM-DD date the rate applies.")],
        rate: Annotated[str, Field(description="Decimal rate as a string.")],
        from_: Annotated[
            str | None,
            Field(alias="from", description="Optional new base currency code."),
        ] = None,
        to: Annotated[
            str | None,
            Field(description="Optional new destination currency code."),
        ] = None,
    ) -> dict:
        body = {"date": date, "rate": rate, "from": from_, "to": to}
        body = {k: v for k, v in body.items() if v is not None}
        return await request("PUT", f"/v1/exchange-rates/{id}", json=body)

    @mcp.tool(
        name="delete_exchange_rate",
        description="Permanently delete an exchange-rate entry by ID. **Destructive**.",
    )
    async def delete_exchange_rate(
        id: Annotated[str, Field(description="Numeric exchange-rate ID.")],
    ) -> dict:
        await request("DELETE", f"/v1/exchange-rates/{id}")
        return {"status": "deleted", "id": id}

    @mcp.tool(
        name="bulk_set_exchange_rates_by_pair",
        description=(
            "Bulk-set rates for one currency pair across multiple dates. "
            "``rates`` is a mapping of YYYY-MM-DD date → decimal rate string, "
            "e.g. ``{'2026-03-01': '1.2345', '2026-03-02': '1.2351'}``. "
            "Existing dates are overwritten."
        ),
    )
    async def bulk_set_exchange_rates_by_pair(
        from_: Annotated[
            str,
            Field(alias="from", description="Base currency code."),
        ],
        to: Annotated[str, Field(description="Destination currency code.")],
        rates: Annotated[
            dict[str, str],
            Field(description="Map of YYYY-MM-DD → rate string."),
        ],
    ) -> dict:
        return await request(
            "POST",
            f"/v1/exchange-rates/by-currencies/{from_}/{to}",
            json=rates,
        )

    @mcp.tool(
        name="bulk_set_exchange_rates_by_date",
        description=(
            "Bulk-set rates from one base currency to many destinations on a "
            "single date. ``rates`` maps destination currency code → decimal "
            "rate string, e.g. ``{'USD': '1.2345', 'GBP': '0.85'}``. "
            "Existing entries for that date are overwritten."
        ),
    )
    async def bulk_set_exchange_rates_by_date(
        date: Annotated[str, Field(description="YYYY-MM-DD date.")],
        from_: Annotated[
            str,
            Field(alias="from", description="Base currency code."),
        ],
        rates: Annotated[
            dict[str, str],
            Field(description="Map of destination code → rate string."),
        ],
    ) -> dict:
        body = {"from": from_, "rates": rates}
        return await request(
            "POST",
            f"/v1/exchange-rates/by-date/{date}",
            json=body,
        )
