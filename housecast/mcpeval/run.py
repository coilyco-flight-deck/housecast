"""A run: every prompt of one task against one definition set, concurrently.

A run that blocks the person is a failed requirement rather than a slow one.
The tester's hour is the binding constraint in this whole design - four hours,
four tasks, and forty of those minutes go to reading results - so a serial
twenty-prompt arm at a minute a prompt spends a third of the hour watching a
progress bar.

Concurrency is bounded by a semaphore rather than by `gather` over everything,
because the ceiling belongs to the declared rate limit rather than to how many
prompts a task happens to hold. A shed request is the caller's to slow down; it
is never this code's to retry harder.

Two runs of one task with one thing changed are the two arms of a controlled
experiment. What must be identical between them is recorded on the run as its
`fingerprint`, and `compare` refuses across a difference rather than averaging
through it.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from mcp.client.client import Client

from housecast.mcpeval.checks import DIMENSIONS, Grade, grade
from housecast.mcpeval.definitions import DefinitionSet
from housecast.mcpeval.models import ModelClient, ModelConfig
from housecast.mcpeval.runner import Trial, advertised_tools, run_prompt
from housecast.mcpeval.task import Task

DEFAULT_CONCURRENCY = 8


class RunError(RuntimeError):
    """Raised when a run cannot be executed as specified."""


@dataclass(frozen=True)
class RunConfig:
    """Where the subject is, which model, and how hard to push."""

    subject_url: str
    model: ModelConfig
    concurrency: int = DEFAULT_CONCURRENCY
    subject_version: str = ""
    dimensions: Sequence[str] = DIMENSIONS


@dataclass(frozen=True)
class Run:
    """One task, one definition set, every prompt, graded."""

    run_id: str
    task: str
    definition_digest: str
    definition_label: str
    definition_authored_by: str
    roster_digest: str
    started_at: str
    finished_at: str
    fingerprint: Mapping[str, Any]
    trials: tuple[Trial, ...] = field(default_factory=tuple)
    grades: tuple[Grade, ...] = field(default_factory=tuple)

    @property
    def by_prompt(self) -> dict[str, Grade]:
        return {g.prompt_id: g for g in self.grades}

    @property
    def trial_by_prompt(self) -> dict[str, Trial]:
        return {t.prompt_id: t for t in self.trials}

    @property
    def scored(self) -> tuple[Grade, ...]:
        return tuple(g for g in self.grades if g.score is not None)

    @property
    def errored(self) -> tuple[Grade, ...]:
        """Transport failures. Never scored, so they cannot enter a comparison as regressions."""
        return tuple(g for g in self.grades if g.score is None)

    @property
    def mean_score(self) -> float | None:
        """Present for a headline only. A comparison never reads two of these."""
        scored = self.scored
        if not scored:
            return None
        return sum(g.score or 0.0 for g in scored) / len(scored)

    @property
    def duration_seconds(self) -> float:
        start = dt.datetime.fromisoformat(self.started_at)
        end = dt.datetime.fromisoformat(self.finished_at)
        return (end - start).total_seconds()

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task": self.task,
            "definition_digest": self.definition_digest,
            "definition_label": self.definition_label,
            "definition_authored_by": self.definition_authored_by,
            "roster_digest": self.roster_digest,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "fingerprint": dict(self.fingerprint),
            "trials": [t.as_dict() for t in self.trials],
            "grades": [g.as_dict() for g in self.grades],
        }


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


async def execute(
    task: Task,
    definitions: DefinitionSet,
    config: RunConfig,
    *,
    on_progress: Any = None,
) -> Run:
    """Run every prompt of `task` against `definitions`, at `config.concurrency`.

    Each prompt opens its own MCP connection to the subject, because a customer's
    agent does, and because sharing one would serialise the calls the
    concurrency exists to overlap.
    """
    started = _now()
    run_id = f"run_{secrets.token_hex(5)}"
    gate = asyncio.Semaphore(max(1, config.concurrency))
    done = 0
    total = len(task.prompts)

    async with Client(config.subject_url) as probe:
        advertised = await advertised_tools(probe)
    subject_version = config.subject_version or "unknown"

    async with ModelClient(config.model) as model:

        async def one(prompt: Any) -> Trial:
            nonlocal done
            async with gate, Client(config.subject_url) as subject:
                trial = await run_prompt(
                    subject=subject,
                    model=model,
                    definitions=definitions,
                    advertised=advertised,
                    prompt_id=prompt.id,
                    prompt=prompt.text,
                    subject_version=subject_version,
                )
            done += 1
            if on_progress is not None:
                on_progress(done, total, trial)
            return trial

        trials = await asyncio.gather(*(one(prompt) for prompt in task.prompts))

    ordered = tuple(sorted(trials, key=lambda t: [p.id for p in task.prompts].index(t.prompt_id)))
    grades = tuple(
        grade(trial, task.rule_for(trial.prompt_id), config.dimensions) for trial in ordered
    )
    return Run(
        run_id=run_id,
        task=task.slug,
        definition_digest=definitions.digest,
        definition_label=definitions.label,
        definition_authored_by=definitions.authored_by,
        roster_digest=ordered[0].roster_digest if ordered else "",
        started_at=started,
        finished_at=_now(),
        # What must be identical between two arms. The tool-set digest is absent
        # on purpose: it is derived from the prose, which is the measurement.
        fingerprint={
            "task": task.slug,
            "subject_version": subject_version,
            "dimensions": list(config.dimensions),
            **config.model.fingerprint(),
        },
        trials=ordered,
        grades=grades,
    )
