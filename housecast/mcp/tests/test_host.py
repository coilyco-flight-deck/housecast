"""A-4: two harness launches of identical variants produce identical rosters.

The fixture is a real MCPServer driven over the real in-memory transport, not
a stub. A stub would prove the test agrees with itself and nothing about the
transport actually carrying descriptions across.
"""

from __future__ import annotations

import anyio
import pytest
from mcp.server.mcpserver import MCPServer
from mcp.types import TextContent

from housecast.mcp.host import HostError, Roster, apply_prose, hosted, roster

BASELINE = {
    "write_file": "Write text to a path, creating parent directories.",
    "read_file": "Read a file as text.",
}
EDITED = BASELINE | {"write_file": "Writes anything, anywhere, for any purpose at all."}


def fixture_server() -> MCPServer:
    server = MCPServer("fixture")

    @server.tool()
    def write_file(path: str, text: str) -> str:
        """Write text to a path, creating parent directories."""
        return "written"

    @server.tool()
    def read_file(path: str) -> str:
        """Read a file as text."""
        return "contents"

    return server


async def capture(prose: dict[str, str] | None = None) -> Roster:
    async with hosted(fixture_server, prose) as session:
        return await roster(session)


def test_two_launches_of_one_variant_are_byte_identical() -> None:
    """A-4."""
    first = anyio.run(capture, EDITED)
    second = anyio.run(capture, EDITED)
    assert [t.canonical() for t in first.tools] == [t.canonical() for t in second.tools]
    assert first.digest == second.digest


def test_two_different_variants_are_not_byte_identical() -> None:
    """Negative control: identity above must be the variant's doing, not the harness flattening."""
    assert anyio.run(capture, BASELINE).digest != anyio.run(capture, EDITED).digest


def test_the_hosted_subject_advertises_the_variant_prose() -> None:
    captured = anyio.run(capture, EDITED)
    described = {t.name: t.description for t in captured.tools}
    assert described["write_file"] == EDITED["write_file"]
    assert described["read_file"] == BASELINE["read_file"]


def test_prose_editing_leaves_the_schema_alone() -> None:
    """K-3: differing prose is the measurement, so nothing else may move with it."""
    base = {t.name: t.schema for t in anyio.run(capture, BASELINE).tools}
    edited = {t.name: t.schema for t in anyio.run(capture, EDITED).tools}
    assert base == edited


def test_the_tool_still_runs_after_its_prose_is_rewritten() -> None:
    async def call() -> str:
        async with hosted(fixture_server, EDITED) as session:
            result = await session.call_tool("write_file", {"path": "/tmp/x", "text": "hi"})
            block = result.content[0]
            assert isinstance(block, TextContent)
            return block.text

    assert anyio.run(call) == "written"


def test_presentation_order_is_carried_not_sorted() -> None:
    """Selection depends on what else was on offer and where, so order is part of the roster."""
    assert anyio.run(capture, BASELINE).names() == ("write_file", "read_file")


def test_a_variant_naming_an_unknown_tool_refuses() -> None:
    with pytest.raises(HostError, match="does not advertise"):
        apply_prose(fixture_server(), {"delete_everything": "surely fine"})


def test_a_launch_does_not_leak_prose_into_the_next_one() -> None:
    """`hosted` builds its own server, so a mutated registry cannot outlive one launch."""
    anyio.run(capture, EDITED)
    assert anyio.run(capture).digest == anyio.run(capture, BASELINE).digest
