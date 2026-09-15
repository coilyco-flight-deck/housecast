"""Join authored challenges to what a runner returned, and record every drop.

There is no mechanical scorer here. On agent-compose's first graded board a
regex tier disagreed with the human on every case where either deviated from a
pass, so it was removed rather than tuned. Selection is structural only.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from housecast.grade.schema import AGENT_COMPOSE, Challenge, DatasetEntry, Profile, Response


@dataclass(frozen=True)
class Dropped:
    challenge_id: str
    reason: str


@dataclass
class DatasetReport:
    """Silent truncation reads as full coverage, so every drop is recorded."""

    kept: list[DatasetEntry] = field(default_factory=list)
    dropped: list[Dropped] = field(default_factory=list)
    # Kept rather than dropped: the case ran and the other epochs are in the
    # log. A blank card a grader cannot score is still not a fail by the seat.
    blank: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        line = f"{len(self.kept)} kept, {len(self.dropped)} dropped"
        return f"{line}, {len(self.blank)} blank" if self.blank else line


def build(challenges: list[Challenge], responses: list[Response], epoch: int = 1) -> DatasetReport:
    """One entry per challenge, carrying the named epoch's text for annotation.

    The other epochs stay in the runner's own log as evidence a reader can open.
    """
    by_challenge: dict[str, list[Response]] = defaultdict(list)
    for response in responses:
        by_challenge[response.challenge_id].append(response)

    report = DatasetReport()
    for challenge in challenges:
        runs = sorted(by_challenge[challenge.id], key=lambda run: run.epoch)
        if not runs:
            report.dropped.append(Dropped(challenge.id, "no subject runs"))
            continue
        chosen = next((run for run in runs if run.epoch == epoch), runs[0])
        if not chosen.text:
            report.blank.append(challenge.id)
        report.kept.append(
            DatasetEntry(challenge=challenge, output=chosen.text, note=tool_note(challenge, chosen))
        )
    return report


def tool_note(challenge: Challenge, response: Response) -> str:
    """Whether the answer took the shape the case required, as a note not a score.

    A missing call is not a fail. The grader decides that, and a subject can be
    right about the task while reaching for the wrong tool. What the note removes
    is the grader having to infer from prose whether a call happened at all.
    """
    if not challenge.required_tool:
        return ""
    if response.called(challenge.required_tool):
        return f"called {challenge.required_tool}"
    called = ", ".join(response.tools)
    return f"did not call {challenge.required_tool}, called: {called or 'nothing'}"


def validate(challenges: list[Challenge], profile: Profile = AGENT_COMPOSE) -> list[str]:
    """Profile-level shape for a whole challenge list, in one pass."""
    problems: list[str] = []
    for challenge in challenges:
        problems.extend(challenge.check_against(profile))
    return problems
