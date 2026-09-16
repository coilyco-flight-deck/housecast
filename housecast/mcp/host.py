"""PR-1: the subject, constructed inside the evaluation process.

The harness process is the subject's runtime. That is a constraint rather than
a preference: the transport is a linked in-memory stream pair, and a linked
in-memory pair does not cross a language boundary, so no other runtime can
construct the server object and hold the other end.

The reason it has to be in-process is `apply_prose`. Editing a description
means rewriting the tool registry before a client ever sees it, and an
out-of-process client only receives what the subject chose to advertise.
Dropping in-process does not simplify the loop, it cancels it.

Everything here stops at a captured roster. Nothing below decides anything a
comparison depends on, which keeps the pinned runtime under the logic rather
than through it.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass

import anyio
from mcp.client.session import ClientSession
from mcp.server.mcpserver import MCPServer
from mcp.shared.memory import create_client_server_memory_streams

from housecast.digest import digest


class HostError(RuntimeError):
    """Raised when a variant names prose the subject does not advertise."""


@dataclass(frozen=True)
class ToolDefinition:
    """One advertised tool, as the model was shown it."""

    name: str
    description: str
    schema: Mapping[str, object]

    def canonical(self) -> str:
        return json.dumps(
            {"name": self.name, "description": self.description, "schema": self.schema},
            ensure_ascii=False,
            sort_keys=True,
        )


@dataclass(frozen=True)
class Roster:
    """The exact tool list the model was shown, in presentation order.

    Order is carried rather than sorted away, because whether a tool is
    selected depends on what else was on offer and where. Two trials with
    different rosters are not comparable, which is why this digests.
    """

    tools: tuple[ToolDefinition, ...]

    @property
    def digest(self) -> str:
        return digest("\n".join(tool.canonical() for tool in self.tools))

    def names(self) -> tuple[str, ...]:
        return tuple(tool.name for tool in self.tools)


def apply_prose(server: MCPServer, prose: Mapping[str, str]) -> MCPServer:
    """Rewrite each advertised description in place, before any client connects.

    Mutates the registry the server already built rather than re-registering,
    because a tool carries its callable and its generated schema and only the
    prose is under test. K-3: differing prose is the measurement, so everything
    else must survive the edit untouched.
    """
    registry = server._tool_manager._tools
    unknown = set(prose) - set(registry)
    if unknown:
        raise HostError(
            f"variant names tools the subject does not advertise: {sorted(unknown)}. "
            "Prose is measured against the subject that was hosted, not against a later one."
        )
    for name, description in prose.items():
        registry[name] = registry[name].model_copy(update={"description": description})
    return server


@asynccontextmanager
async def hosted(
    build: Callable[[], MCPServer], prose: Mapping[str, str] | None = None
) -> AsyncIterator[ClientSession]:
    """Construct the subject, apply the variant's prose, and yield a connected client.

    `build` is called inside rather than taking a server, so two launches cannot
    accidentally share one mutated registry. That is most of what A-4 asks for.
    """
    server = build()
    if prose:
        apply_prose(server, prose)
    low = server._lowlevel_server
    async with (
        create_client_server_memory_streams() as (
            (client_read, client_write),
            (server_read, server_write),
        ),
        anyio.create_task_group() as group,
    ):

        async def serve() -> None:
            await low.run(
                server_read,
                server_write,
                low.create_initialization_options(),
                raise_exceptions=True,
            )

        group.start_soon(serve)
        async with ClientSession(client_read, client_write) as session:
            await session.initialize()
            yield session
        group.cancel_scope.cancel()


async def roster(session: ClientSession) -> Roster:
    """What the model would be shown, captured as the trial records it."""
    listed = await session.list_tools()
    return Roster(
        tools=tuple(
            ToolDefinition(
                name=tool.name,
                description=tool.description or "",
                schema=tool.input_schema,
            )
            for tool in listed.tools
        )
    )
