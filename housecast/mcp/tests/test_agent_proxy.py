"""The transport contract, tested where it can be tested offline.

No live request is made here. What these own is the request this client would
send and what it does with a response, both of which are decided before any
socket opens. Whether the contract survives LiteLLM's translation per provider
is a different question, and a deployed one:
`teable:coilyco-flight-deck/agent-proxy#7807`.
"""

from __future__ import annotations

import pytest

from housecast.mcp.agent_proxy import (
    EVALUATION_ROUTES,
    AgentProxyClient,
    TransportError,
    parse_reply,
    retry_after,
)

DEEPSEEK = "evaluation/deepseek-v4-pro"
OLLAMA = "evaluation/ornith-35b"


def client(**overrides: object) -> AgentProxyClient:
    fields: dict[str, object] = {"base_url": "http://proxy.invalid", "model": DEEPSEEK}
    fields.update(overrides)
    return AgentProxyClient(**fields)  # type: ignore[arg-type]


def test_a_service_route_refuses_because_it_carries_fallbacks() -> None:
    """A fallback firing mid-run swaps the model underneath the comparison."""
    with pytest.raises(TransportError, match="not an evaluation route"):
        client(model="sirens-echo/default")


def test_every_evaluation_route_is_accepted() -> None:
    """Negative control for the refusal above."""
    for route in EVALUATION_ROUTES:
        choice = "auto" if "ministral" in route or "ornith" in route else "required"
        assert client(model=route, tool_choice=choice).model == route


def test_forcing_a_call_on_an_ollama_route_refuses_locally() -> None:
    """The proxy 400s on this now. Refusing here says why without a round trip."""
    with pytest.raises(TransportError, match="ollama-dialect route"):
        client(model=OLLAMA, tool_choice="required")


def test_auto_is_allowed_on_an_ollama_route() -> None:
    assert client(model=OLLAMA, tool_choice="auto").tool_choice == "auto"


def test_the_payload_carries_the_constraints_that_used_to_be_dropped() -> None:
    body = client(seed=7, temperature=0.0).payload("go", [{"type": "function"}])
    assert body["tool_choice"] == "required"
    assert body["seed"] == 7
    assert body["temperature"] == 0.0
    assert body["tools"] == [{"type": "function"}]


def test_no_seed_is_omitted_rather_than_sent_as_null() -> None:
    assert "seed" not in client().payload("go", [])


def test_retry_after_honours_the_server_number() -> None:
    assert retry_after({"Retry-After": "2.5"}, attempt=0) == 2.5
    assert retry_after({"retry-after": "1"}, attempt=4) == 1.0


def test_retry_after_backs_off_when_the_server_gives_nothing() -> None:
    assert retry_after({}, attempt=0) == 1.0
    assert retry_after({}, attempt=3) == 8.0
    assert retry_after({}, attempt=20) == 30.0


def test_a_junk_retry_after_falls_back_rather_than_raising() -> None:
    assert retry_after({"Retry-After": "soon"}, attempt=2) == 4.0


def test_tool_call_ids_are_dropped_so_nothing_can_compare_them() -> None:
    """Ids are backend-issued on DeepSeek and synthetic on ollama."""
    reply = parse_reply(
        {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {"id": "call_abc", "function": {"name": "write_file"}},
                            {"id": "call_xyz", "function": {"name": "read_file"}},
                        ],
                    }
                }
            ]
        }
    )
    assert reply.tool_calls == ("write_file", "read_file")


def test_a_reply_with_no_tool_calls_is_not_an_error() -> None:
    reply = parse_reply({"choices": [{"message": {"content": "I would not call anything."}}]})
    assert reply.tool_calls == ()
    assert reply.text == "I would not call anything."
