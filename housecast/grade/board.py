"""A board: every context a run needs, and every challenge to put through it.

A challenge is always answered the same way, by compiling a context and sending
one model call. That is true of a composed role bundle and of a deployed
conversational lane, so the board carries the compiled context rather than the
recipe for it, and a runner needs to know nothing about how it was built.

This layer defines and validates the board. It does not run one. See
docs/grading.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from housecast.grade.schema import AGENT_COMPOSE, Challenge, Profile

# Wire format, not a package name. Committed evidence carries it.
BOARD_SCHEMA = "aos-eval.board.v1"


class BoardError(Exception):
    """Raised on a board that cannot be read or would run incompletely."""


@dataclass(frozen=True)
class Board:
    """Contexts keyed by entity, plus the challenges that run against them."""

    contexts: dict[str, str]
    challenges: list[Challenge]
    provenance: dict[str, Any] = field(default_factory=dict)

    def context_for(self, challenge: Challenge) -> str:
        return self.contexts[challenge.entity]

    @property
    def entities(self) -> list[str]:
        return sorted({challenge.entity for challenge in self.challenges})


def load_board(raw: dict[str, Any], profile: Profile = AGENT_COMPOSE) -> Board:
    """Read a board and refuse one that would run incompletely.

    An unwritten challenge or a missing context fails here rather than at the
    model call, because a partial run reads as coverage it did not have.
    """
    schema = str(raw.get("schema", ""))
    if schema and schema != BOARD_SCHEMA and not schema.endswith(".board.v1"):
        raise BoardError(f"{schema} is not a board")

    contexts = {str(name): str(text) for name, text in (raw.get("contexts") or {}).items()}
    empty = sorted(name for name, text in contexts.items() if not text.strip())
    if empty:
        raise BoardError(f"context is empty for: {', '.join(empty)}")

    entries = raw.get("challenges") or []
    if not entries:
        raise BoardError("board holds no challenges")
    challenges = [Challenge.model_validate(entry) for entry in entries]

    problems: list[str] = []
    for challenge in challenges:
        if not challenge.written:
            problems.append(f"{challenge.id}: unwritten, so it cannot be run")
        if challenge.entity not in contexts:
            problems.append(f"{challenge.id}: no context for entity {challenge.entity!r}")
        problems.extend(challenge.check_against(profile))
    if problems:
        raise BoardError("\n".join(problems))

    unused = sorted(set(contexts) - {challenge.entity for challenge in challenges})
    if unused:
        raise BoardError(f"context with no challenge: {', '.join(unused)}")

    return Board(
        contexts=contexts,
        challenges=challenges,
        provenance=dict(raw.get("provenance") or {}),
    )
