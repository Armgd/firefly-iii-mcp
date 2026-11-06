"""Tool behaviour hints (read-only / destructive / idempotent) derived from
each tool's leading verb, so clients can auto-approve reads and confirm
deletes. Every tool name must start with a known verb; unknown verbs fail
loudly so a new tool cannot ship unclassified."""

from __future__ import annotations

from collections.abc import Sequence

from fastmcp.server.transforms import GetToolNext, Transform, VersionSpec
from fastmcp.tools import Tool
from mcp.types import ToolAnnotations

READ_ONLY_VERBS = ("get", "list", "search", "autocomplete", "test", "validate", "count")

WRITE_VERBS: dict[str, tuple[bool, bool]] = {
    # verb: (destructive, idempotent)
    "create": (False, False),
    "update": (True, True),
    "delete": (True, True),
    "trigger": (True, False),
    "enable": (False, True),
    "disable": (False, True),
    "set": (False, True),
    "bulk": (True, True),
}


def annotations_for(tool_name: str) -> ToolAnnotations:
    verb = tool_name.split("_", 1)[0]
    if verb in READ_ONLY_VERBS:
        return ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        )
    if verb in WRITE_VERBS:
        destructive, idempotent = WRITE_VERBS[verb]
        return ToolAnnotations(
            read_only_hint=False,
            destructive_hint=destructive,
            idempotent_hint=idempotent,
            open_world_hint=False,
        )
    raise ValueError(f"No behaviour hints defined for tool {tool_name!r} (verb {verb!r}).")


def _annotate(tool: Tool) -> Tool:
    return tool.model_copy(update={"annotations": annotations_for(tool.name)})


class VerbAnnotations(Transform):
    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [_annotate(t) for t in tools]

    async def get_tool(
        self, name: str, call_next: GetToolNext, *, version: VersionSpec | None = None
    ) -> Tool | None:
        tool = await call_next(name, version=version)
        return _annotate(tool) if tool is not None else None
