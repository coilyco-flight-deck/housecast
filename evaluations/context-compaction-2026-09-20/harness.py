"""Pure pieces of the compaction experiment: rendering, grading, cost.

No network and no subprocess here, so every function is unit-testable.
Messages use fast-jev-compaction's shape: role, text, toolUses, toolResults.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SYSTEM = (
    "You are an engineer exploring a code repository through tool calls. "
    "Earlier tool calls and results appear in the conversation as text."
)
NUDGE = "In one sentence, say which file or search you will look at next."
QUESTION = (
    "In the file `{path}` that you read earlier, what is the exact text of line {line}? "
    "Reply with that line's text only. If the file's contents are no longer in the "
    "conversation, reply exactly `RE-READ {path}` and I will send the file again."
)
MAX_REREADS = 2


def render_message(message: dict[str, Any]) -> str:
    parts: list[str] = []
    if message["text"].strip():
        parts.append(message["text"].strip())
    for use in message.get("toolUses", []):
        args = json.dumps(use["input"], sort_keys=True)
        parts.append(f"[call {use['tool_use_id']}] {use['tool']}({args})")
    for result in message.get("toolResults") or []:
        parts.append(f"[result {result['tool_use_id']}]\n{result['text']}")
    return "\n".join(parts)


def to_chat(
    messages: list[dict[str, Any]], system: str, tail: str | None = None
) -> list[dict[str, str]]:
    """Chat messages with same-role neighbours merged, since dropped calls leave gaps."""
    out: list[dict[str, str]] = [{"role": "system", "content": system}]
    bodies = [(m["role"], render_message(m)) for m in messages]
    if tail:
        bodies.append(("user", tail))
    for role, body in bodies:
        if not body:
            continue
        if out[-1]["role"] == role:
            out[-1]["content"] += "\n\n" + body
        else:
            out.append({"role": role, "content": body})
    return out


def sha256(chat: list[dict[str, str]]) -> str:
    return hashlib.sha256(json.dumps(chat, sort_keys=True).encode()).hexdigest()[:16]


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def grade(answer: str, expected: str) -> str:
    """pass when the exact line is in the answer, else unknown or wrong."""
    text = norm(answer)
    if norm(expected) in text:
        return "pass"
    if "UNKNOWN" in text.upper() or "RE-READ" in text.upper():
        return "unknown"
    return "wrong"


def reread_target(answer: str) -> str | None:
    """The path of a `RE-READ <path>` request, which must be the whole reply."""
    match = re.fullmatch(r"`?RE-READ\s+`?([^\s`]+)`?\.?", norm(answer))
    return match.group(1) if match else None


def billed(
    prompt: int, cached: int, completion: int, miss_usd: float, hit_usd: float, out_usd: float
) -> float:
    """Cost in USD from per-million prices, with misses derived as prompt minus cached."""
    return ((prompt - cached) * miss_usd + cached * hit_usd + completion * out_usd) / 1e6


def drop_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "resultsDropped": sum(d["action"] == "drop_result" for d in decisions),
        "callsDropped": sum(d["action"] == "drop_call" for d in decisions),
    }


def cached_tokens(usage: dict[str, Any]) -> int:
    details = usage.get("prompt_tokens_details") or {}
    return int(details.get("cached_tokens") or usage.get("prompt_cache_hit_tokens") or 0)
