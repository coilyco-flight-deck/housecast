"""The room-facing artifact: rounds built once, reviewed, and never live-read.

`present` serves a deck rather than a run directory, and that is the whole
safety design. A deck is built deliberately, scanned, and looked at before it
reaches a room, so there is no path from an open grading session to a
projector. `serve` holds the private side and never listens past loopback.

Two sources meet here. The case comes from committed evidence. The commitments
block is authored prose and belongs to the exercise content, not to this
module. See docs/grading.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from housecast.grade.export import ExportRefusedError, scan_for_secrets
from housecast.grade.io import load_annotations, load_dataset, read_yaml
from housecast.grade.schema import Annotation, DatasetEntry

DECK_FORMAT = "housecast.deck.v1"

# Every slug the audience never sees, withheld here rather than suppressed in a
# page. See docs/deck.md.
WITHHELD = ("entity", "test_type", "attribute", "pair_id", "half", "seed", "required_tool")


@dataclass(frozen=True)
class Round:
    """One round as the room meets it, in the order the states unlock it."""

    id: str
    commitments: tuple[str, ...]
    prompt: str
    response: str
    label: str
    critique: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "commitments": list(self.commitments),
            "prompt": self.prompt,
            "response": self.response,
            "reveal": {
                "label": self.label,
                "critique": self.critique,
                "evidence": self.evidence,
            },
        }


def build(
    name: str,
    rounds: list[dict[str, Any]],
    dataset: list[DatasetEntry],
    annotations: dict[str, Annotation],
) -> list[Round]:
    """Join authored rounds to graded cases, refusing anything a room should not meet."""
    by_id = {entry.id: entry for entry in dataset}
    built: list[Round] = []
    problems: list[str] = []

    for position, raw in enumerate(rounds, start=1):
        case_id = str(raw.get("case", ""))
        entry = by_id.get(case_id)
        if entry is None:
            problems.append(f"round {position} names case {case_id!r}, which the run does not hold")
            continue

        annotation = annotations.get(case_id)
        if annotation is None:
            # The reveal is the teaching moment. A round cannot show Kai's
            # verdict on a case she has not graded.
            problems.append(f"round {position} uses ungraded case {case_id!r}, so it has no reveal")
            continue

        commitments = tuple(str(line) for line in raw.get("commitments", ()))
        if not commitments:
            problems.append(
                f"round {position} has no commitments, so there is nothing to grade against"
            )
            continue

        built.append(
            Round(
                id=str(raw.get("id", case_id)),
                commitments=commitments,
                prompt=entry.challenge.prompt or "",
                response=entry.output,
                label=annotation.label.value,
                critique=annotation.critique,
                evidence=annotation.evidence,
            )
        )

    problems.extend(_unsafe(built))
    if problems:
        raise ExportRefusedError(
            "refusing to build this deck, because a room is a public surface:\n  "
            + "\n  ".join(problems)
        )
    if not built:
        raise ExportRefusedError(f"{name} declares no rounds, so there is nothing to present")
    return built


def _unsafe(rounds: list[Round]) -> list[str]:
    """The exporter's scan, applied to the artifact that actually reaches a room.

    The critique is included here on purpose, unlike in a public export, because
    the reveal is the point of the round. That makes scanning it necessary
    rather than optional.
    """
    problems: list[str] = []
    for round_ in rounds:
        fields = {
            "prompt": round_.prompt,
            "response": round_.response,
            "critique": round_.critique,
            "evidence": round_.evidence,
            "commitments": "\n".join(round_.commitments),
        }
        for field_name, text in fields.items():
            problems.extend(
                f"{round_.id}.{field_name} contains what looks like {reason}"
                for reason in scan_for_secrets(text)
            )
    return problems


def build_from_dirs(rounds_path: Path, run_dir: Path) -> dict[str, Any]:
    """Authored rounds beside a committed run, joined into one reviewable file."""
    raw = read_yaml(rounds_path)
    dataset_path = run_dir / "dataset.yaml"
    if not dataset_path.exists():
        raise ExportRefusedError(f"{run_dir} has no dataset.yaml, so there are no cases to draw on")

    rounds = build(
        str(raw.get("deck", rounds_path.stem)),
        list(raw.get("rounds", [])),
        load_dataset(dataset_path),
        load_annotations(run_dir / "annotations.yaml"),
    )
    return {
        "format": DECK_FORMAT,
        "deck": str(raw.get("deck", rounds_path.stem)),
        "rounds": [round_.to_dict() for round_ in rounds],
    }


def load(path: Path) -> dict[str, Any]:
    """Read a built deck, scanning again rather than trusting the build that made it.

    A deck is a file, and a file can be hand-edited between building it and
    standing in front of a room with it.
    """
    raw = read_yaml(path) if path.suffix in (".yaml", ".yml") else _read_json(path)
    if raw.get("format") != DECK_FORMAT:
        raise ExportRefusedError(f"{path} is not a {DECK_FORMAT} deck")

    rounds = [
        Round(
            id=str(entry.get("id", "")),
            commitments=tuple(str(line) for line in entry.get("commitments", ())),
            prompt=str(entry.get("prompt", "")),
            response=str(entry.get("response", "")),
            label=str(entry.get("reveal", {}).get("label", "")),
            critique=str(entry.get("reveal", {}).get("critique", "")),
            evidence=str(entry.get("reveal", {}).get("evidence", "")),
        )
        for entry in raw.get("rounds", [])
    ]
    if problems := _unsafe(rounds):
        raise ExportRefusedError("refusing to present this deck:\n  " + "\n  ".join(problems))
    if not rounds:
        raise ExportRefusedError(f"{path} declares no rounds, so there is nothing to present")
    return {"format": DECK_FORMAT, "deck": str(raw.get("deck", path.stem)), "rounds": rounds}


def _read_json(path: Path) -> dict[str, Any]:
    import json

    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded
