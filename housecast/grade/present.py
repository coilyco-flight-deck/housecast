"""The audience surface. Public by default, because nothing private is here.

`serve` refuses to listen past loopback. This listens openly and that inversion
is deliberate: the two commands are separate processes so the only thing
dividing a grader's critique from a room is which one is running, rather than a
flag inside one that is a single wrong state away from serving the wrong half.

Nothing here is authenticated, per Kai on inbox#472. A viewer creates no
identity, and the vote is held in memory and discarded when the process exits.
The one capability that is gated is the presenter's own control, because a room
that can skip rounds or close a vote is a live failure with an audience.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from housecast.grade.deck import Round

if TYPE_CHECKING:
    from fastapi import FastAPI

DEFAULT_PORT = 8766

# The order a round unlocks in. Each state adds exactly one thing, and nothing
# earlier can reach what a later one holds. See inbox#472 #issuecomment-80481.
STATES = ("commitments", "case", "open", "split", "reveal")

CHOICES = frozenset({"pass", "fail"})


class VoteRejectedError(Exception):
    """A vote the current state does not accept. The page shows the reason."""


class Vote(BaseModel):
    """One anonymous vote. `device` is a token the browser minted for itself."""

    device: str
    choice: str


@dataclass
class Presentation:
    """One deck, advanced by the presenter, voted on by whoever is looking.

    Votes are a dict per round keyed by device, so re-voting replaces rather
    than accumulates. That is the whole integrity model and it is deliberately
    thin: this measures a room, and a phone plus a laptop counts twice.
    """

    name: str
    rounds: list[Round]
    control_token: str = field(default_factory=lambda: secrets.token_urlsafe(9))
    round_index: int = 0
    state_index: int = 0
    votes: dict[int, dict[str, str]] = field(default_factory=dict)

    @property
    def state(self) -> str:
        return STATES[self.state_index]

    @property
    def round(self) -> Round:
        return self.rounds[self.round_index]

    def reached(self, state: str) -> bool:
        return self.state_index >= STATES.index(state)

    def advance(self) -> None:
        if self.state_index + 1 < len(STATES):
            self.state_index += 1
        elif self.round_index + 1 < len(self.rounds):
            self.round_index += 1
            self.state_index = 0

    def back(self) -> None:
        if self.state_index > 0:
            self.state_index -= 1
        elif self.round_index > 0:
            self.round_index -= 1
            self.state_index = len(STATES) - 1

    def tally(self) -> dict[str, int]:
        cast = self.votes.get(self.round_index, {})
        return {
            "pass": sum(1 for choice in cast.values() if choice == "pass"),
            "fail": sum(1 for choice in cast.values() if choice == "fail"),
        }

    def record(self, vote: Vote) -> int:
        if self.state != "open":
            raise VoteRejectedError("voting is not open on this round")
        if vote.choice not in CHOICES:
            raise VoteRejectedError("a vote is pass or fail")
        if not vote.device:
            raise VoteRejectedError("a vote needs a device token")
        self.votes.setdefault(self.round_index, {})[vote.device] = vote.choice
        return len(self.votes[self.round_index])

    def public_state(self) -> dict[str, Any]:
        """Exactly what this state permits, and nothing a later state holds.

        The reveal is withheld until the presenter reaches it rather than being
        sent early and hidden, because a viewer reading the response body before
        voting would both spoil the round and corrupt the split it produces.
        """
        current = self.round
        payload: dict[str, Any] = {
            "deck": self.name,
            "round": self.round_index,
            "rounds": len(self.rounds),
            "state": self.state,
            "id": current.id,
            "commitments": list(current.commitments),
        }
        if self.reached("case"):
            payload["prompt"] = current.prompt
            payload["response"] = current.response
        # A count while open, never a direction: a running split anchors later
        # voters to the early ones. See docs/presenting.md.
        if self.state == "open":
            payload["votes_cast"] = len(self.votes.get(self.round_index, {}))
        if self.reached("split"):
            payload["split"] = self.tally()
        if self.reached("reveal"):
            payload["reveal"] = {
                "label": current.label,
                "critique": current.critique,
                "evidence": current.evidence,
            }
        return payload


NO_BUILD = """housecast grade present is running and no page is mounted.

Point --static at a built presentation page, or read the state directly:

    GET  /api/state   the current round, holding back everything this state has not reached
    POST /api/vote    one anonymous vote: {"device", "choice"}
"""


def create_app(show: Presentation, static: Any = None) -> FastAPI:
    from fastapi import FastAPI, Header, HTTPException
    from fastapi.responses import PlainTextResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="housecast grade present", docs_url=None, redoc_url=None)

    def presenter(token: str | None) -> None:
        if not token or not secrets.compare_digest(token, show.control_token):
            raise HTTPException(status_code=403, detail="the control token does not match")

    @app.get("/api/state")
    def read_state() -> dict[str, Any]:
        return show.public_state()

    @app.post("/api/vote")
    def cast_vote(vote: Vote) -> dict[str, Any]:
        try:
            cast = show.record(vote)
        except VoteRejectedError as rejected:
            raise HTTPException(status_code=409, detail=str(rejected)) from rejected
        # The voter learns that it counted and how many have voted. Never which
        # way the room is going.
        return {"recorded": True, "votes_cast": cast}

    @app.post("/api/control/advance")
    def advance(x_control_token: str | None = Header(default=None)) -> dict[str, Any]:
        presenter(x_control_token)
        show.advance()
        return show.public_state()

    @app.post("/api/control/back")
    def back(x_control_token: str | None = Header(default=None)) -> dict[str, Any]:
        presenter(x_control_token)
        show.back()
        return show.public_state()

    if static is not None:
        app.mount("/", StaticFiles(directory=str(static), html=True), name="page")
    else:

        @app.get("/", response_class=PlainTextResponse)
        def no_build() -> str:
            return NO_BUILD

    return app


def present(
    show: Presentation,
    host: str = "0.0.0.0",
    port: int = DEFAULT_PORT,
    static: Any = None,
) -> None:
    import uvicorn

    uvicorn.run(create_app(show, static), host=host, port=port, log_level="warning")
