"""ASGI entry point for ``uvicorn main:app``."""

from firefly_mcp.server import app, mcp

__all__ = ["app", "mcp"]
