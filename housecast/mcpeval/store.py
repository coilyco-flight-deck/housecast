"""Runs and definition sets on disk, as committed evidence.

A run is written once and never rewritten: it records what was true when it executed.
One directory per run, because a run is the unit a comparison reads, and JSON rather
than a database, so the evidence is readable without this tool.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

from housecast.mcpeval.checks import CheckResult, Grade
from housecast.mcpeval.definitions import DefinitionSet, ToolProse
from housecast.mcpeval.run import Run
from housecast.mcpeval.runner import CallRecord, Trial

DEFAULT_ROOT = pathlib.Path(".mcpeval")


class StoreError(RuntimeError):
    """Raised when evidence cannot be written or read back."""


def _root(root: pathlib.Path | None) -> pathlib.Path:
    return root if root is not None else DEFAULT_ROOT


def save_run(run: Run, root: pathlib.Path | None = None) -> pathlib.Path:
    """Write one run. Refuses to overwrite: evidence is written once."""
    base = _root(root) / "runs"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{run.run_id}.json"
    if path.exists():
        raise StoreError(f"{path} already exists. A committed run is never rewritten.")
    path.write_text(json.dumps(run.as_dict(), indent=2, ensure_ascii=False))
    return path


def save_definitions(defs: DefinitionSet, root: pathlib.Path | None = None) -> pathlib.Path:
    """Write one definition set, keyed by its own digest so a revert collides."""
    base = _root(root) / "definitions"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{defs.short()}.json"
    path.write_text(
        json.dumps(
            {
                "digest": defs.digest,
                "parent": defs.parent,
                "authored_by": defs.authored_by,
                "label": defs.label,
                "instructions": defs.instructions,
                "tools": {name: defs.tools[name].as_dict() for name in sorted(defs.tools)},
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return path


def load_definitions(path: pathlib.Path) -> DefinitionSet:
    raw = json.loads(path.read_text())
    return DefinitionSet(
        tools={
            name: ToolProse(
                description=value["description"], parameters=dict(value.get("parameters") or {})
            )
            for name, value in (raw.get("tools") or {}).items()
        },
        instructions=raw.get("instructions") or "",
        authored_by=raw.get("authored_by") or "human:unknown",
        parent=raw.get("parent"),
        label=raw.get("label") or "",
    )


def load_run(path: pathlib.Path) -> Run:
    raw = json.loads(path.read_text())
    trials = tuple(_trial(entry) for entry in raw.get("trials") or [])
    grades = tuple(_grade(entry) for entry in raw.get("grades") or [])
    return Run(
        run_id=raw["run_id"],
        task=raw["task"],
        definition_digest=raw["definition_digest"],
        definition_label=raw.get("definition_label") or "",
        definition_authored_by=raw.get("definition_authored_by") or "",
        roster_digest=raw.get("roster_digest") or "",
        started_at=raw["started_at"],
        finished_at=raw["finished_at"],
        fingerprint=raw.get("fingerprint") or {},
        trials=trials,
        grades=grades,
    )


def _trial(entry: dict[str, Any]) -> Trial:
    return Trial(
        prompt_id=entry["prompt_id"],
        prompt=entry["prompt"],
        definition_digest=entry["definition_digest"],
        roster_digest=entry["roster_digest"],
        roster_names=tuple(entry.get("roster_names") or ()),
        subject_version=entry.get("subject_version") or "",
        model=entry.get("model") or {},
        calls=tuple(
            CallRecord(
                name=call["name"],
                arguments=call.get("arguments") or {},
                result=call.get("result") or "",
                is_error=bool(call.get("is_error")),
                advertised=bool(call.get("advertised", True)),
                duration_ms=int(call.get("duration_ms") or 0),
            )
            for call in entry.get("calls") or []
        ),
        answer=entry.get("answer") or "",
        turns=int(entry.get("turns") or 0),
        finished=bool(entry.get("finished")),
        duration_ms=int(entry.get("duration_ms") or 0),
        prompt_tokens=int(entry.get("prompt_tokens") or 0),
        completion_tokens=int(entry.get("completion_tokens") or 0),
        error=entry.get("error") or "",
    )


def _grade(entry: dict[str, Any]) -> Grade:
    return Grade(
        prompt_id=entry["prompt_id"],
        checks=tuple(
            CheckResult(name=c["name"], passed=bool(c["passed"]), detail=c.get("detail") or "")
            for c in entry.get("checks") or []
        ),
        score=entry.get("score"),
        error=entry.get("error") or "",
    )


def runs(root: pathlib.Path | None = None) -> list[pathlib.Path]:
    base = _root(root) / "runs"
    return sorted(base.glob("run_*.json")) if base.is_dir() else []


def definitions(root: pathlib.Path | None = None) -> list[pathlib.Path]:
    base = _root(root) / "definitions"
    return sorted(base.glob("*.json")) if base.is_dir() else []


def latest_runs(task: str, root: pathlib.Path | None = None) -> list[Run]:
    """Every run of one task, newest last."""
    found = [load_run(path) for path in runs(root)]
    return sorted((r for r in found if r.task == task), key=lambda r: r.started_at)
