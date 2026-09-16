"""One prompt, end to end, against one definition set. The centre of the loop.

`tools/list` -> apply the definition set -> chat completion with tools attached
-> route the returned calls back to the real subject -> feed results back ->
write a trial.

The route back is the half that is easy to skip and cannot be. A model that
asks for a tool and never sees its result never discovers that the media_id it
invented was rejected, so a run without the return path measures first-guess
selection and calls it task success. Recovery, the dimension that asks whether
an error message actually got acted on, does not exist at all without it.

Everything a comparison depends on is recorded on the trial rather than inferred
later: the roster the model was shown, the subject version, the model
fingerprint, and the definition digest. An unrecorded input is an uncontrolled
variable, and this is where prompt-optimization tooling usually fails quietly -
the prose changes, the model version moves the same week, and the improvement
is attributed to the edit.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from mcp.client.client import Client

from housecast.digest import digest
from housecast.mcpeval.definitions import DefinitionSet
from housecast.mcpeval.models import ModelConfig, ToolCall, TransportError, Turner

# Unfinished after this many turns is recorded rather than run further: an
# unbounded loop spends wall clock on the prompt least likely to teach anything.
MAX_TURNS = 6


class RunnerError(RuntimeError):
    """Raised when a prompt could not be driven as specified."""


@dataclass(frozen=True)
class CallRecord:
    """One tool call and what the subject actually answered."""

    name: str
    arguments: Mapping[str, Any]
    result: str
    is_error: bool
    advertised: bool
    duration_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arguments": dict(self.arguments),
            "result": self.result,
            "is_error": self.is_error,
            "advertised": self.advertised,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True)
class Trial:
    """One prompt, driven once, against one definition set."""

    prompt_id: str
    prompt: str
    definition_digest: str
    roster_digest: str
    roster_names: tuple[str, ...]
    subject_version: str
    model: Mapping[str, Any]
    calls: tuple[CallRecord, ...]
    answer: str
    turns: int
    finished: bool
    duration_ms: int
    prompt_tokens: int
    completion_tokens: int
    error: str = ""

    @property
    def call_names(self) -> tuple[str, ...]:
        return tuple(call.name for call in self.calls)

    def as_dict(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "prompt": self.prompt,
            "definition_digest": self.definition_digest,
            "roster_digest": self.roster_digest,
            "roster_names": list(self.roster_names),
            "subject_version": self.subject_version,
            "model": dict(self.model),
            "calls": [call.as_dict() for call in self.calls],
            "answer": self.answer,
            "turns": self.turns,
            "finished": self.finished,
            "duration_ms": self.duration_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "error": self.error,
        }


@dataclass(frozen=True)
class Roster:
    """The exact tool list the model was shown, in presentation order.

    Order is carried rather than sorted away, because whether a tool is selected
    depends on what else was on offer and where. Two trials shown different
    rosters are not comparable, which is why this digests.
    """

    tools: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

    @property
    def digest(self) -> str:
        canonical = json.dumps(
            [
                {
                    "name": tool["name"],
                    "description": tool.get("description") or "",
                    "schema": tool.get("inputSchema") or {},
                }
                for tool in self.tools
            ],
            ensure_ascii=False,
            sort_keys=True,
        )
        return digest(canonical)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(str(tool["name"]) for tool in self.tools)


async def advertised_tools(client: Client) -> list[dict[str, Any]]:
    """What the subject advertises, as plain dicts the overlay can clone."""
    listed = await client.list_tools()
    return [
        {
            "name": tool.name,
            "description": tool.description or "",
            "inputSchema": _schema_of(tool),
        }
        for tool in listed.tools
    ]


def _schema_of(tool: Any) -> dict[str, Any]:
    """The SDK has spelled this `inputSchema` and `input_schema` in living memory."""
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)
    return dict(schema) if schema else {"type": "object", "properties": {}}


def _text_of(result: Any) -> str:
    """Flatten a CallToolResult to the string a model is shown."""
    parts: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(str(text))
    if not parts:
        structured = getattr(result, "structured_content", None) or getattr(
            result, "structuredContent", None
        )
        if structured is not None:
            parts.append(json.dumps(structured, ensure_ascii=False))
    return "\n".join(parts)


async def _route(subject: Client, call: ToolCall, advertised: Sequence[str]) -> CallRecord:
    """Send one model-requested call to the real subject and record what came back."""
    started = time.monotonic()
    if call.name not in advertised:
        # A hallucinated tool never reaches the subject. The model is told so,
        # because that is the recovery signal a real host would give it.
        return CallRecord(
            name=call.name,
            arguments=call.arguments,
            result=json.dumps(
                {"error": "no_such_tool", "received": call.name, "available": list(advertised)}
            ),
            is_error=True,
            advertised=False,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
    try:
        result = await subject.call_tool(call.name, dict(call.arguments))
        text = _text_of(result)
        is_error = bool(getattr(result, "is_error", False)) or '"error"' in text
    except Exception as exc:  # the subject is a service; its faults are data
        text = json.dumps({"error": "subject_exception", "detail": f"{type(exc).__name__}: {exc}"})
        is_error = True
    return CallRecord(
        name=call.name,
        arguments=call.arguments,
        result=text,
        is_error=is_error,
        advertised=True,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


async def run_prompt(
    *,
    subject: Client,
    model: Turner,
    definitions: DefinitionSet,
    advertised: Sequence[Mapping[str, Any]],
    prompt_id: str,
    prompt: str,
    subject_version: str,
    max_turns: int = MAX_TURNS,
) -> Trial:
    """Drive one prompt to an answer, routing every call through the real subject."""
    roster = Roster(tools=tuple(definitions.overlay(advertised)))
    names = roster.names
    messages: list[dict[str, Any]] = []
    if definitions.instructions.strip():
        messages.append({"role": "system", "content": definitions.instructions})
    messages.append({"role": "user", "content": prompt})

    calls: list[CallRecord] = []
    answer = ""
    turns = 0
    finished = False
    error = ""
    prompt_tokens = 0
    completion_tokens = 0
    started = time.monotonic()

    try:
        for turn_index in range(1, max_turns + 1):
            turns = turn_index
            reply = await model.turn(messages, roster.tools)
            prompt_tokens += reply.prompt_tokens
            completion_tokens += reply.completion_tokens
            if not reply.tool_calls:
                answer = reply.text
                finished = True
                break
            assistant: dict[str, Any] = {
                "role": "assistant",
                "content": reply.text or None,
                "tool_calls": [
                    {
                        "id": call.call_id or f"call_{len(calls) + index}",
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(dict(call.arguments), ensure_ascii=False),
                        },
                    }
                    for index, call in enumerate(reply.tool_calls)
                ],
            }
            messages.append(assistant)
            for index, call in enumerate(reply.tool_calls):
                record = await _route(subject, call, names)
                calls.append(record)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": assistant["tool_calls"][index]["id"],
                        "content": record.result,
                    }
                )
            answer = reply.text
    except TransportError as exc:
        error = str(exc)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    return Trial(
        prompt_id=prompt_id,
        prompt=prompt,
        definition_digest=definitions.digest,
        roster_digest=roster.digest,
        roster_names=names,
        subject_version=subject_version,
        model=model.config.fingerprint(),
        calls=tuple(calls),
        answer=answer,
        turns=turns,
        finished=finished,
        duration_ms=int((time.monotonic() - started) * 1000),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        error=error,
    )


__all__ = [
    "CallRecord",
    "ModelConfig",
    "Roster",
    "RunnerError",
    "Trial",
    "advertised_tools",
    "run_prompt",
]
