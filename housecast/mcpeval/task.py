"""A task and its prompts, read from YAML.

A task is a capability and the unit of judgement. A prompt is one phrasing or edge
case within it, a sample and never a verdict. The correctness rules sit beside the
prompts because they are written before the run, the only time they can be written
honestly. They are never sent to the model.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import yaml

TASKS = pathlib.Path(__file__).parent / "tasks"


class TaskError(ValueError):
    """Raised when a task file cannot be read as a task."""


@dataclass(frozen=True)
class Prompt:
    """One phrasing within a task, with the rule its result is graded against."""

    id: str
    text: str
    rules: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Task:
    """A capability, and the 10-25 prompts that sample it."""

    slug: str
    title: str
    capability: str
    prompts: tuple[Prompt, ...]

    def __post_init__(self) -> None:
        if not 1 <= len(self.prompts) <= 40:
            raise TaskError(f"{self.slug} has {len(self.prompts)} prompts; a task holds 10-25")
        seen = [prompt.id for prompt in self.prompts]
        if len(set(seen)) != len(seen):
            raise TaskError(f"{self.slug} repeats a prompt id, so a pairing would collide")

    def rule_for(self, prompt_id: str) -> Mapping[str, Any]:
        for prompt in self.prompts:
            if prompt.id == prompt_id:
                return prompt.rules
        raise TaskError(f"no prompt {prompt_id!r} in {self.slug}")


def load(path: pathlib.Path) -> Task:
    """Read one task file, folding task-level rules into each prompt."""
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise TaskError(f"{path} is not a mapping")
    shared: dict[str, Any] = dict(raw.get("rules") or {})
    prompts: list[Prompt] = []
    for entry in raw.get("prompts") or []:
        merged = shared | dict(entry.get("rules") or {})
        prompts.append(Prompt(id=str(entry["id"]), text=str(entry["text"]), rules=merged))
    return Task(
        slug=str(raw.get("task") or path.stem),
        title=str(raw.get("title") or path.stem),
        capability=str(raw.get("capability") or ""),
        prompts=tuple(prompts),
    )


def available() -> list[pathlib.Path]:
    return sorted(TASKS.glob("*.yaml"))


def load_slug(slug: str) -> Task:
    path = TASKS / f"{slug}.yaml"
    if not path.is_file():
        names = [p.stem for p in available()]
        raise TaskError(f"no task {slug!r}; available: {names}")
    return load(path)


def summarise(tasks: Sequence[Task]) -> str:
    return "\n".join(
        f"{task.slug:24} {len(task.prompts):3} prompts  {task.title}" for task in tasks
    )
