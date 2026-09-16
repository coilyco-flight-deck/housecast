"""The subject over a real connection, and one prompt driven end to end.

The model is a stub here. What is exercised is the join the stub cannot fake:
tools/list, the overlay, routing the returned calls back to the real subject,
and the trial that records what happened. A test that stubbed the subject too
would prove only that the harness can talk to itself.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from mcp.client.client import Client

from housecast.mcpeval.checks import grade
from housecast.mcpeval.definitions import baseline_from
from housecast.mcpeval.models import ModelConfig, ModelReply, ToolCall, parse_reply
from housecast.mcpeval.runner import advertised_tools, run_prompt
from housecast.mcpeval.subject.server import SUBJECT_VERSION, build
from housecast.mcpeval.subject.state import LIBRARY, Library


async def call_json(client: Client, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """One tool call, decoded. Every tool here answers with a JSON object."""
    result = await client.call_tool(name, arguments)
    block = result.content[0]
    decoded = json.loads(str(getattr(block, "text", "")))
    assert isinstance(decoded, dict)
    return decoded


class ScriptedModel:
    """Replays a fixed sequence of turns, and records the rosters it was shown."""

    def __init__(self, turns: Sequence[ModelReply]) -> None:
        self._turns = list(turns)
        self.seen: list[list[Mapping[str, Any]]] = []
        self.config = ModelConfig(base_url="stub://", model="stub")

    async def turn(
        self, messages: Sequence[Mapping[str, Any]], tools: Sequence[Mapping[str, Any]]
    ) -> ModelReply:
        self.seen.append([dict(t) for t in tools])
        return self._turns.pop(0) if self._turns else ModelReply(text="done")


@pytest.mark.anyio
async def test_the_subject_serves_its_tools_and_the_happy_path_works() -> None:
    async with Client(build(Library())) as client:
        listed = await advertised_tools(client)
        assert [t["name"] for t in listed] == [
            "media_analyze",
            "media_register",
            "media_transcribe",
            "media_job_status",
            "media_convert",
        ]
        registered = await call_json(client, "media_register", {"path": "/media/lecture.mp4"})
        started = await call_json(client, "media_transcribe", {"media_id": registered["media_id"]})
        await call_json(client, "media_job_status", {"job_id": started["job_id"]})
        done = await call_json(client, "media_job_status", {"job_id": started["job_id"]})
    assert done["state"] == "completed"
    assert "cache coherence" in done["transcript"]


@pytest.mark.anyio
async def test_an_identifier_cannot_be_guessed() -> None:
    """Unguessable ids are what keep concurrent prompts from reading each other."""
    async with Client(build(Library())) as client:
        first = await call_json(client, "media_register", {"path": "/media/lecture.mp4"})
        answer = await call_json(client, "media_transcribe", {"media_id": "med_0001"})
    assert first["media_id"] != "med_0001"
    assert answer["error"] == "unknown_media_id"
    assert "media_register" in answer["correction"]


@pytest.mark.anyio
async def test_an_error_names_the_offending_input_and_a_valid_correction() -> None:
    """The Recovery dimension grades the response to this, so it has to say something."""
    async with Client(build(Library())) as client:
        answer = await call_json(
            client, "media_convert", {"path": "/media/lecture.mp4", "ratio": "widescreen"}
        )
    assert answer["received"] == "widescreen"
    assert "16:9" in answer["correction"]


@pytest.mark.anyio
async def test_a_file_with_no_audio_refuses_rather_than_inventing_a_transcript() -> None:
    async with Client(build(Library())) as client:
        registered = await call_json(
            client, "media_register", {"path": "/media/b-roll-skyline.mp4"}
        )
        answer = await call_json(client, "media_transcribe", {"media_id": registered["media_id"]})
    assert answer["error"] == "no_audio_track"
    assert not LIBRARY["/media/b-roll-skyline.mp4"].has_audio


@pytest.mark.anyio
async def test_one_prompt_drives_end_to_end_and_the_model_sees_the_edited_prose() -> None:
    """The route back is the half that is easy to skip and cannot be."""
    async with Client(build(Library())) as subject:
        advertised = await advertised_tools(subject)
        defs = baseline_from(advertised, authored_by="human:test").edited(
            tool="media_analyze", description="metadata only", authored_by="human:test"
        )
        model = ScriptedModel(
            [
                ModelReply(
                    text="",
                    tool_calls=(ToolCall("media_register", {"path": "/media/lecture.mp4"}),),
                ),
                ModelReply(text="here is the transcript: cache coherence", tool_calls=()),
            ]
        )
        result = await run_prompt(
            subject=subject,
            model=model,
            definitions=defs,
            advertised=advertised,
            prompt_id="p1",
            prompt="transcribe it",
            subject_version=SUBJECT_VERSION,
        )
    assert result.finished
    assert result.call_names == ("media_register",)
    assert json.loads(result.calls[0].result)["media_id"].startswith("med_")
    shown = {t["name"]: t["description"] for t in model.seen[0]}
    assert shown["media_analyze"] == "metadata only", "the model was not shown the edit"
    assert advertised[0]["description"] != "metadata only", "the subject was mutated"


@pytest.mark.anyio
async def test_a_hallucinated_tool_never_reaches_the_subject_but_is_still_answered() -> None:
    async with Client(build(Library())) as subject:
        advertised = await advertised_tools(subject)
        defs = baseline_from(advertised, authored_by="human:test")
        model = ScriptedModel(
            [
                ModelReply(text="", tool_calls=(ToolCall("media_summarise", {"path": "x"}),)),
                ModelReply(text="sorry", tool_calls=()),
            ]
        )
        result = await run_prompt(
            subject=subject,
            model=model,
            definitions=defs,
            advertised=advertised,
            prompt_id="p1",
            prompt="x",
            subject_version=SUBJECT_VERSION,
        )
    assert result.calls[0].advertised is False
    assert json.loads(result.calls[0].result)["error"] == "no_such_tool"
    assert not grade(
        result,
        {
            "expect": "transcript",
            "answer_contains": "z",
            "required_tools": [],
            "discouraged_tools": [],
        },
    ).outcome_passed


def test_a_model_answering_in_prose_is_read_as_no_tool_calls() -> None:
    """`ministral-3-14b` does exactly this, and a board would score it as total prose failure."""
    reply = parse_reply(
        {
            "choices": [
                {
                    "message": {"content": 'transcribe_video[ARGS]{"path": "/x"}'},
                    "finish_reason": "stop",
                }
            ]
        }
    )
    assert reply.tool_calls == ()
    assert reply.finish_reason == "stop"


def test_unparseable_arguments_are_graded_rather_than_crashed() -> None:
    reply = parse_reply(
        {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {"id": "1", "function": {"name": "f", "arguments": "{not json"}}
                        ]
                    }
                }
            ]
        }
    )
    assert reply.tool_calls[0].arguments == {"__unparsed__": "{not json"}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
