import pytest

from firefly_mcp.annotations import annotations_for

pytestmark = pytest.mark.anyio


async def test_every_tool_is_annotated(mcp_client):
    tools = await mcp_client.list_tools()

    unannotated = [t.name for t in tools if t.annotations is None]
    assert unannotated == []


@pytest.mark.parametrize(
    ("name", "read_only", "destructive", "idempotent"),
    [
        ("get_account", True, False, True),
        ("autocomplete_tags", True, False, True),
        ("test_rule", True, False, True),
        ("create_account", False, False, False),
        ("update_account", False, True, True),
        ("delete_account", False, True, True),
        ("trigger_rule", False, True, False),
        ("enable_currency", False, False, True),
    ],
)
def test_annotations_follow_tool_verb(name, read_only, destructive, idempotent):
    a = annotations_for(name)

    assert (a.read_only_hint, a.destructive_hint, a.idempotent_hint) == (
        read_only,
        destructive,
        idempotent,
    )
    assert a.open_world_hint is False


def test_unknown_verb_fails_loudly():
    with pytest.raises(ValueError, match="frobnicate_account"):
        annotations_for("frobnicate_account")
