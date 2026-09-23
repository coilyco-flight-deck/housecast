"""The one `ModelClient` that talks to a real model, through Agent Proxy.

Proxy behaviour, not spec (`teable:coilyco-flight-deck/agent-proxy#7805`): an
ollama-dialect route 400s on `tool_choice`, so that pairing is refused rather than
falling back to `auto` and scoring a dropped constraint as a decline. `seed` is
forwarded, `Retry-After` is honoured because admission sheds bursts, and tool call
ids are normalized away because some backends issue them and ollama invents them.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from housecast.mcp.driver import ModelReply

EVALUATION_ROUTES = (
    "evaluation/ministral-3-14b",
    "evaluation/ornith-35b",
    "evaluation/deepseek-v4-flash",
    "evaluation/deepseek-v4-pro",
    "evaluation/deepseek-v4-flash-vision-exp",
)

# Ollama-dialect, so these refuse `tool_choice`: a forced call cannot run
# against them.
OLLAMA_DIALECT_ROUTES = ("evaluation/ministral-3-14b", "evaluation/ornith-35b")


class TransportError(RuntimeError):
    """Raised when a request cannot be made as specified, rather than made differently."""


@dataclass(frozen=True)
class AgentProxyClient:
    """One turn against one `evaluation/` route.

    The `evaluation/` namespace is the lane to use because every route in it
    declares an empty fallback list. A service route falls back across models
    and the response carries the logical key either way, so a fallback firing
    mid-run swaps the model underneath a comparison invisibly.
    """

    base_url: str
    model: str
    api_key: str = ""
    temperature: float = 0.0
    seed: int | None = None
    tool_choice: str = "required"
    max_attempts: int = 5

    def __post_init__(self) -> None:
        if self.model not in EVALUATION_ROUTES:
            raise TransportError(
                f"{self.model!r} is not an evaluation route. A service route carries "
                "fallbacks, and a fallback firing mid-run swaps the model underneath "
                f"the comparison. Use one of: {', '.join(EVALUATION_ROUTES)}"
            )
        if self.model in OLLAMA_DIALECT_ROUTES and self.tool_choice != "auto":
            raise TransportError(
                f"{self.model!r} is an ollama-dialect route, which accepts only "
                f'tool_choice="auto", not {self.tool_choice!r}. Forcing a call needs '
                "one of the DeepSeek routes."
            )

    def payload(self, prompt: str, tools: Sequence[Mapping[str, object]]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "tools": list(tools),
            "tool_choice": self.tool_choice,
            "temperature": self.temperature,
        }
        if self.seed is not None:
            body["seed"] = self.seed
        return body

    async def turn(self, prompt: str, tools: Sequence[Mapping[str, object]]) -> ModelReply:
        body = self.payload(prompt, tools)
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as http:
            for attempt in range(self.max_attempts):
                response = await http.post("/v1/chat/completions", json=body, headers=headers)
                if response.status_code != 429:
                    response.raise_for_status()
                    return parse_reply(response.json())
                await asyncio.sleep(retry_after(response.headers, attempt))
        raise TransportError(
            f"{self.model} shed {self.max_attempts} attempts. Admission shedding "
            "defaults to one request per second per logical route, and this loop's "
            "traffic is bursts. Raising it is a deploy-side value, not a code change."
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
    """Tool names only, ids dropped.

    An id is backend-issued on the DeepSeek routes and synthetic on ollama, so
    two trials of one variant can differ on id shape alone. Nothing downstream
    compares ids, and dropping them here means nothing downstream can start.
    """
    choice = payload["choices"][0]["message"]
    calls = choice.get("tool_calls") or []
    return ModelReply(
        text=choice.get("content") or "",
        tool_calls=tuple(call["function"]["name"] for call in calls),
    )
