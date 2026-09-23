"""The model client: plain OpenAI-style, with no gateway or vendor branch in it.

Measured 2026-09-16 on the `evaluation/*` routes: deepseek thinking-mode routes answer
any `tool_choice` with HTTP 400, so none is sent and a caller setting one is refused
rather than silently dropped. Some routes emit calls as message content, not
`tool_calls`, and `probe_tool_calls` catches that before a board rather than inside it.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx


class TransportError(RuntimeError):
    """Raised when a request cannot be made as specified, rather than made differently."""


@dataclass(frozen=True)
class ToolCall:
    """One call the model asked for, as the trial records it."""

    name: str
    arguments: Mapping[str, Any]
    call_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "arguments": dict(self.arguments)}


@dataclass(frozen=True)
class ModelReply:
    """One turn's answer."""

    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_message: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelConfig:
    """Everything that identifies the model arm of a comparison.

    Recorded on every trial. Two runs differing on any field here are not two
    arms of one experiment, and the comparison refuses rather than averaging.
    """

    base_url: str
    model: str
    api_key: str = ""
    temperature: float = 0.0
    seed: int | None = None
    tool_choice: str | None = None
    max_attempts: int = 5
    timeout_seconds: float = 180.0

    def fingerprint(self) -> dict[str, Any]:
        """What a comparison holds constant. The key is deliberately absent."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "seed": self.seed,
            "tool_choice": self.tool_choice,
        }


class Turner(Protocol):
    """What the runner needs from a model, and nothing more.

    A protocol rather than the concrete client, because transport is not the
    runner's to decide. `ModelClient` is one implementation and a scripted
    stand-in in the tests is another, and nothing above either changes.
    """

    @property
    def config(self) -> ModelConfig: ...

    async def turn(
        self, messages: Sequence[Mapping[str, Any]], tools: Sequence[Mapping[str, Any]]
    ) -> ModelReply: ...


class ModelClient:
    """One OpenAI-style chat-completions endpoint, reused across a run's prompts."""

    def __init__(self, config: ModelConfig, client: httpx.AsyncClient | None = None) -> None:
        self.config = config
        self._client = client
        self._owned = client is None

    async def __aenter__(self) -> ModelClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout_seconds)
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owned and self._client is not None:
            await self._client.aclose()
            self._client = None

    def payload(
        self, messages: Sequence[Mapping[str, Any]], tools: Sequence[Mapping[str, Any]]
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": list(messages),
            "temperature": self.config.temperature,
        }
        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description") or "",
                        "parameters": tool.get("inputSchema")
                        or {"type": "object", "properties": {}},
                    },
                }
                for tool in tools
            ]
            if self.config.tool_choice is not None:
                body["tool_choice"] = self.config.tool_choice
        if self.config.seed is not None:
            body["seed"] = self.config.seed
        return body

    async def turn(
        self, messages: Sequence[Mapping[str, Any]], tools: Sequence[Mapping[str, Any]]
    ) -> ModelReply:
        if self._client is None:
            raise TransportError("ModelClient used outside its context manager")
        body = self.payload(messages, tools)
        headers = {"content-type": "application/json"}
        if self.config.api_key:
            headers["authorization"] = f"Bearer {self.config.api_key}"
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        last = ""
        for attempt in range(self.config.max_attempts):
            response = await self._client.post(
                url, json=body, headers=headers, timeout=self.config.timeout_seconds
            )
            if response.status_code == 429:
                await asyncio.sleep(retry_after(response.headers, attempt))
                continue
            if response.status_code >= 400:
                last = response.text[:400]
                raise TransportError(f"{self.config.model} answered {response.status_code}: {last}")
            return parse_reply(response.json())
        raise TransportError(
            f"{self.config.model} shed {self.config.max_attempts} attempts. "
            "Concurrency is the caller's to lower; the rate limit is not this code's to raise."
        )


def retry_after(headers: Mapping[str, str], attempt: int) -> float:
    """Honour the server's own number, and back off only when it does not give one."""
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw:
        try:
            return max(float(raw), 0.0)
        except ValueError:
            pass
    return min(2.0**attempt, 30.0)


def parse_reply(payload: Mapping[str, Any]) -> ModelReply:
    choice = payload["choices"][0]
    message = choice.get("message") or {}
    calls: list[ToolCall] = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        raw = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except json.JSONDecodeError:
            # A model emitting unparseable arguments is a result, not a crash.
            # It is graded as a malformed call rather than dropped.
            arguments = {"__unparsed__": raw}
        calls.append(
            ToolCall(
                name=function.get("name") or "",
                arguments=arguments,
                call_id=call.get("id") or "",
            )
        )
    usage = payload.get("usage") or {}
    return ModelReply(
        text=message.get("content") or "",
        tool_calls=tuple(calls),
        finish_reason=choice.get("finish_reason") or "",
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        raw_message=message,
    )


async def probe_tool_calls(config: ModelConfig) -> str:
    """Does this route emit structured `tool_calls` at all?

    Run before a board, not inside one. A route that answers in prose scores
    every prompt as calling nothing, which reads as a catastrophic prose defect
    and is a transport fact.
    """
    tools = [
        {
            "name": "probe_echo",
            "description": "Echo a string back. Call this with the word 'ping'.",
            "inputSchema": {
                "type": "object",
                "properties": {"word": {"type": "string"}},
                "required": ["word"],
            },
        }
    ]
    async with ModelClient(config) as client:
        reply = await client.turn([{"role": "user", "content": "Echo the word ping."}], tools)
    if reply.tool_calls:
        return "ok"
    return (
        f"{config.model} returned no structured tool_calls "
        f"(finish_reason={reply.finish_reason!r}, content={reply.text[:80]!r}). "
        "A board against this route would score every prompt as calling nothing."
    )
