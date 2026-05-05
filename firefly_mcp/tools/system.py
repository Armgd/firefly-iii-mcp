"""System / metadata tools."""

from __future__ import annotations

from fastmcp import FastMCP

from ..client import request


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="get_about",
        description=(
            "Return Firefly III system information: software version, API "
            "version, PHP version, OS, and database driver. Useful as a "
            "connectivity / sanity check."
        ),
    )
    async def get_about() -> dict:
        return await request("GET", "/v1/about")
