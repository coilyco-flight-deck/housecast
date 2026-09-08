"""YAML on the boundary. Every committed record enters and leaves here."""

from __future__ import annotations

import re
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

# A grader name lands in a filename, so it is validated rather than escaped.
GRADER_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class GraderNameRejectedError(Exception):
    """A name that would not survive being a filename."""


def annotations_name(grader: str | None) -> str:
    """Which file this grader writes, so two of them on one board do not collide.

    Unnamed keeps `annotations.yaml`, because a solo run is the common one and
    renaming its output would strand every board already graded.
    """
    if grader is None:
        return "annotations.yaml"
    if not GRADER_NAME.fullmatch(grader):
        raise GraderNameRejectedError(
            f"{grader!r} is not a grader name: use lowercase letters, digits and hyphens, "
            "because the name becomes part of a filename"
        )
    return f"annotations.{grader}.yaml"


def grader_from_path(path: Path) -> str:
    """The fallback only. `read_grader` is the answer when the file carries one."""
    stem = path.name.removesuffix(".yaml").removesuffix(".yml")
    prefix = "annotations."
    return stem[len(prefix) :] if stem.startswith(prefix) and len(stem) > len(prefix) else stem


def read_grader(path: Path) -> str | None:
    """Who wrote this file, according to the file rather than to its name.

    A filename is the first thing a copy or an export changes, so an identity
    carried only there stops being attributable exactly when someone needs to
    attribute it. See docs/grading-surfaces.md.
    """
    if not path.exists():
        return None
    named = read_yaml(path).get("grader")
    return None if named is None else str(named)


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def dump_yaml(payload: dict[str, Any]) -> str:
    return yaml.safe_dump(payload, sort_keys=False, width=100, allow_unicode=True)


def load_dataset(path: Path) -> list[DatasetEntry]:
    raw = read_yaml(path)
    return [DatasetEntry.from_dict(entry) for entry in raw.get("dataset", [])]


def save_dataset(path: Path, dataset: list[DatasetEntry]) -> None:
    path.write_text(dump_yaml({"dataset": [entry.to_dict() for entry in dataset]}))


PIN_NAME = "pin.yaml"


def pin_path(dataset_path: Path) -> Path:
    """Beside the dataset it pins, so a run directory carries its own answer."""
    return dataset_path.parent / PIN_NAME


def load_pin(path: Path) -> dict[str, Any] | None:
    """None where a run was never pinned, which is a different state from drift."""
    return read_yaml(path) if path.exists() else None


def save_pin(path: Path, pinned: dict[str, Any]) -> None:
    path.write_text(dump_yaml(pinned))


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


def save_annotations(
    path: Path, annotations: dict[str, Annotation], grader: str | None = None
) -> None:
    """Rewritten whole after every single decision, by both grading surfaces.

    Atomic because of that frequency: a torn write here costs a whole grading
    session rather than one label, and the file is small enough that the
    temp-and-replace is free.

    `grader` is written into the file rather than left to the filename, so two
    testers stay attributable through a copy, a rename, or an export.
    """
    payload: dict[str, Any] = {}
    if grader is not None:
        payload["grader"] = grader
    payload["annotations"] = [annotations[key].to_dict() for key in sorted(annotations)]
    scratch = path.with_name(f".{path.name}.partial")
    scratch.write_text(dump_yaml(payload))
    scratch.replace(path)


def load_profile(path: Path | None) -> Profile:
    """A deployment's own taxonomy, or agent-compose's when none is named."""
    if path is None:
        return AGENT_COMPOSE
    return Profile.from_dict(read_yaml(path))
