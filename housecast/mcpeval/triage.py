"""The queue a tester actually reads, and the budget it costs them.

Forty minutes at two minutes a result is about twenty results one person can
genuinely examine per task-hour, and that figure is fixed no matter how many
prompts ran. So the queue is ordered by what is worth those minutes and the
rows that passed are not in it at all - a tester scrolling past fifteen green
rows to reach three red ones has spent attention the budget cannot refund.

Order: failures first, then the prompts a comparison moved, then inefficiency.
The budget is reported in minutes rather than in rows, because rows are not the
currency the hour is spent in.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from housecast.mcpeval.checks import EFFICIENCY, OUTCOME
from housecast.mcpeval.run import Run

# The brief's own figure: reading a result properly takes a minute or two and
# does not compress.
MINUTES_PER_RESULT = 2.0

FAILURE = "failure"
MOVED = "moved"
INEFFICIENCY = "inefficiency"
TRANSPORT = "transport"

RANK = {TRANSPORT: 0, FAILURE: 1, MOVED: 2, INEFFICIENCY: 3}


@dataclass(frozen=True)
class QueueRow:
    """One prompt worth a person's attention, and why it is here."""

    prompt_id: str
    reason: str
    headline: str
    score: float | None
    calls: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "reason": self.reason,
            "headline": self.headline,
            "score": self.score,
            "calls": list(self.calls),
        }


@dataclass(frozen=True)
class Queue:
    """The triaged rows and what reading them costs."""

    rows: tuple[QueueRow, ...]
    total_prompts: int

    @property
    def minutes(self) -> float:
        return len(self.rows) * MINUTES_PER_RESULT

    @property
    def hidden(self) -> int:
        return self.total_prompts - len(self.rows)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rows": [row.as_dict() for row in self.rows],
            "total_prompts": self.total_prompts,
            "minutes": self.minutes,
            "hidden": self.hidden,
            "minutes_per_result": MINUTES_PER_RESULT,
        }


def build(run: Run, moved: Sequence[str] = ()) -> Queue:
    """Triage one run, optionally knowing which prompts a comparison moved."""
    moved_set = set(moved)
    trials = run.trial_by_prompt
    rows: list[QueueRow] = []
    for grade in run.grades:
        trial = trials.get(grade.prompt_id)
        calls = trial.call_names if trial is not None else ()
        if grade.score is None:
            rows.append(
                QueueRow(
                    prompt_id=grade.prompt_id,
                    reason=TRANSPORT,
                    headline=f"transport error, not graded: {grade.error[:120]}",
                    score=None,
                    calls=calls,
                )
            )
            continue
        failed = grade.failed
        outcome_failed = [c for c in failed if c.name == OUTCOME]
        if outcome_failed:
            rows.append(
                QueueRow(
                    prompt_id=grade.prompt_id,
                    reason=FAILURE,
                    headline=outcome_failed[0].detail,
                    score=grade.score,
                    calls=calls,
                )
            )
            continue
        if grade.prompt_id in moved_set:
            rows.append(
                QueueRow(
                    prompt_id=grade.prompt_id,
                    reason=MOVED,
                    headline="this prompt moved between the two arms",
                    score=grade.score,
                    calls=calls,
                )
            )
            continue
        other = [c for c in failed if c.name != OUTCOME]
        if other:
            inefficiency = [c for c in other if c.name == EFFICIENCY]
            lead = inefficiency[0] if inefficiency else other[0]
            rows.append(
                QueueRow(
                    prompt_id=grade.prompt_id,
                    reason=INEFFICIENCY,
                    headline=f"{lead.name}: {lead.detail}",
                    score=grade.score,
                    calls=calls,
                )
            )
    rows.sort(key=lambda row: (RANK[row.reason], row.score if row.score is not None else -1.0))
    return Queue(rows=tuple(rows), total_prompts=len(run.grades))
