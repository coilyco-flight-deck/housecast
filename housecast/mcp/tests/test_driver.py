"""PR-3: the response reaches the record joined to the case that provoked it.

The client here is a recording fake rather than a live model. That is not a
shortcut around PR-2: what these tests own is the join and the tool payload,
and both are decided by the harness rather than by transport. The concrete
Agent Proxy client implements the same protocol and changes nothing above it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import anyio

from housecast.grade.trial import Provenance, Trial
from housecast.mcp.driver import ModelReply, as_tool_payload, drive
from housecast.mcp.host import hosted, tool_set
from housecast.mcp.tests.test_host import BASELINE, EDITED, fixture_server

PROVENANCE = Provenance(
    board="sha256:board",
    fixture="sha256:fixture",
    tools="sha256:unset",
    subject_version="1.4.0",
    model="local/qwen3-coder",
    temperature=0.0,
    harness_mode="in-memory",
    seed=7,
)


class RecordingClient:
    """Answers every turn the same way, and keeps what it was asked."""

    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.tools: list[Sequence[Mapping[str, object]]] = []

    async def turn(self, prompt: str, tools: Sequence[Mapping[str, object]]) -> ModelReply:
        self.prompts.append(prompt)
        self.tools.append(tools)
        return ModelReply(text="I would call write_file.", tool_calls=("write_file",))


async def run_one(prose: dict[str, str]) -> tuple[RecordingClient, Trial]:
    client = RecordingClient()
    async with hosted(fixture_server, prose) as session:
        captured = await tool_set(session)
        trial = await drive(
            client,
            captured,
            challenge_id="selectable-write-in",
            prompt="Save this note to /tmp/note.txt",
            variant="sha256:variant",
            epoch=1,
            provenance=PROVENANCE,
        )
    return client, trial


def test_the_response_is_joined_to_the_case_that_provoked_it() -> None:
    """PR-3."""
    _, trial = anyio.run(run_one, EDITED)
    assert trial.challenge_id == "selectable-write-in"
    assert trial.response == "I would call write_file."
    assert trial.tools_called == ("write_file",)
    assert trial.epoch == 1


def test_the_trial_records_the_roster_it_actually_ran_against() -> None:
    """A trial cannot claim a tool set it was not run against, so the driver folds it in."""
    _, trial = anyio.run(run_one, EDITED)
    assert trial.provenance.tools != "sha256:unset"
    assert trial.provenance.tools.startswith("sha256:")


def test_two_variants_produce_trials_with_different_rosters() -> None:
    """Negative control for the fold above."""
    _, first = anyio.run(run_one, BASELINE)
    _, second = anyio.run(run_one, EDITED)
    assert first.provenance.tools != second.provenance.tools


def test_the_model_is_shown_the_variant_prose() -> None:
    """The whole loop rests on the edit reaching the model, so assert it does."""
    client, _ = anyio.run(run_one, EDITED)
    described = {
        t["function"]["name"]: t["function"]["description"]  # type: ignore[index]
        for t in client.tools[0]
    }
    assert described["write_file"] == EDITED["write_file"]


def test_the_tool_payload_keeps_presentation_order() -> None:
    client, _ = anyio.run(run_one, BASELINE)
    names = [t["function"]["name"] for t in client.tools[0]]  # type: ignore[index]
    assert names == ["write_file", "read_file"]


def test_the_payload_carries_the_schema_the_subject_declared() -> None:
    async def capture() -> list[dict[str, object]]:
        async with hosted(fixture_server, BASELINE) as session:
            return as_tool_payload(await tool_set(session))

    payload = anyio.run(capture)
    function = payload[0]["function"]
    assert isinstance(function, dict)
    properties = function["parameters"]["properties"]
    assert "path" in properties
    assert "text" in properties
