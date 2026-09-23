"""PR-2 and PR-3: drive a model against the hosted subject, and record what came back.

The model client is a protocol because transport is not this module's to decide.
What it owns is the join: a response is logged against the case that provoked it
and the provenance it ran under, because an unjoined response cannot be compared.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from housecast.grade.trial import Provenance, Trial
from housecast.mcp.host import ToolSet


@dataclass(frozen=True)
class ModelReply:
    """What a model returned for one turn, flattened to what a trial records."""

    text: str
    tool_calls: tuple[str, ...] = ()


class ModelClient(Protocol):
    """One turn against a model with tools attached.

    `tools` is the tool set in presentation order, already rendered to whatever
    the transport wants. The implementation owns that rendering because the
    wire shape belongs to the transport rather than to the harness.
    """

    async def turn(self, prompt: str, tools: Sequence[Mapping[str, object]]) -> ModelReply: ...


def as_tool_payload(tool_set: ToolSet) -> list[dict[str, object]]:
    """The tool set as a tools array, order preserved.

    Order survives because selection depends on what else was on offer and
    where, so a client that sorts this has changed the measurement.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.schema,
            },
        }
        for tool in tool_set.tools
    ]


async def drive(
    client: ModelClient,
    tool_set: ToolSet,
    *,
    challenge_id: str,
    prompt: str,
    variant: str,
    epoch: int,
    provenance: Provenance,
) -> Trial:
    """One case against one variant, returned as the record a comparison reads.

    The tool-set digest is folded into provenance here rather than trusted from
    the caller, so a trial cannot claim a tool set it was not run against.
    """
    reply = await client.turn(prompt, as_tool_payload(tool_set))
    return Trial(
        challenge_id=challenge_id,
        variant=variant,
        epoch=epoch,
        provenance=replace(provenance, tools=tool_set.digest),
        response=reply.text,
        tools_called=reply.tool_calls,
    )
