"""YAML on the boundary. Every committed record enters and leaves here."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from housecast.grade.schema import (
    AGENT_COMPOSE,
    Annotation,
    DatasetEntry,
    Profile,
    decode_label,
)


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def dump_yaml(payload: dict[str, Any]) -> str:
    return yaml.safe_dump(payload, sort_keys=False, width=100, allow_unicode=True)


def load_dataset(path: Path) -> list[DatasetEntry]:
    raw = read_yaml(path)
    return [DatasetEntry.from_dict(entry) for entry in raw.get("dataset", [])]


def save_dataset(path: Path, dataset: list[DatasetEntry]) -> None:
    path.write_text(dump_yaml({"dataset": [entry.to_dict() for entry in dataset]}))


def load_annotations(path: Path) -> dict[str, Annotation]:
    if not path.exists():
        return {}
    raw = read_yaml(path)
    return {
        str(entry["id"]): Annotation(
            id=str(entry["id"]),
            label=decode_label(str(entry["label"])),
            critique=str(entry.get("critique", "")),
            evidence=str(entry.get("evidence", "")),
        )
        for entry in raw.get("annotations", [])
    }


def save_annotations(path: Path, annotations: dict[str, Annotation]) -> None:
    """Rewritten whole after every single decision, by both grading surfaces.

    Atomic because of that frequency: a torn write here costs a whole grading
    session rather than one label, and the file is small enough that the
    temp-and-replace is free.
    """
    payload = {"annotations": [annotations[key].to_dict() for key in sorted(annotations)]}
    scratch = path.with_name(f".{path.name}.partial")
    scratch.write_text(dump_yaml(payload))
    scratch.replace(path)


def load_profile(path: Path | None) -> Profile:
    """A deployment's own taxonomy, or agent-compose's when none is named."""
    if path is None:
        return AGENT_COMPOSE
    return Profile.from_dict(read_yaml(path))
