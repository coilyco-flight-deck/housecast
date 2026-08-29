"""Project a committed run into a display payload. One way, never back.

A display surface is read-only here: nothing is authored in it, so nothing
returns from it. Committed records stay canonical.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from housecast.grade.io import load_annotations, load_dataset, read_yaml
from housecast.grade.schema import Annotation, DatasetEntry, Provenance, pair_results

# Wire format, not a package name. Consumers read it.
EXPORT_FORMAT = "aos-eval.export.v1"

# A refusal list, not a redaction list: the exporter stops rather than scrubs,
# so a record cannot reach a public surface by having a pattern missed.
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("an AWS key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "a bearer or API token",
        re.compile(r"\b(?:ghp|gho|github_pat|xox[baprs])[-_][A-Za-z0-9_]{16,}"),
    ),
    ("a JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("a private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "an SSM parameter path",
        re.compile(r"/[a-z0-9][a-z0-9-]*/[a-z0-9-]*(?:token|password|secret|key)\b", re.IGNORECASE),
    ),
    ("a Discord snowflake", re.compile(r"\b\d{17,20}\b")),
    ("a tailnet host", re.compile(r"\b[a-z0-9-]+\.ts\.net\b", re.IGNORECASE)),
    ("an email address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
)


class ExportRefusedError(Exception):
    """Raised instead of exporting. The caller fixes the record or opts out."""


@dataclass(frozen=True)
class ExportCase:
    """One case as a display surface needs it."""

    id: str
    entity: str
    test_type: str
    prompt: str
    target: str
    output: str
    label: str | None = None
    half: str | None = None
    pair_id: str | None = None
    attribute: str | None = None
    critique: str = ""
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.__dict__.items()
            if value not in (None, "") or key in ("id", "entity", "test_type")
        }


@dataclass
class ExportRun:
    """A whole run, plus the pair structure that makes a board legible."""

    name: str
    cases: list[ExportCase] = field(default_factory=list)
    pairs: list[dict[str, Any]] = field(default_factory=list)
    includes_private: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": EXPORT_FORMAT,
            "run": self.name,
            "includes_private_fields": self.includes_private,
            "provenance": self.provenance,
            "counts": self.counts(),
            "pairs": self.pairs,
            "cases": [case.to_dict() for case in self.cases],
        }

    def counts(self) -> dict[str, int]:
        return {
            "cases": len(self.cases),
            "annotated": sum(1 for case in self.cases if case.label),
            "pairs": len(self.pairs),
            "pairs_passed": sum(1 for pair in self.pairs if pair["passed"]),
        }


def scan_for_secrets(text: str) -> list[str]:
    """Every reason a string is unsafe, so one pass reports all of them."""
    return [reason for reason, pattern in SECRET_PATTERNS if pattern.search(text)]


def build_run(
    name: str,
    dataset: list[DatasetEntry],
    annotations: dict[str, Annotation],
    include_private: bool = False,
    provenance: Provenance | None = None,
) -> ExportRun:
    """Join a dataset to its annotations, refusing anything unsafe to display."""
    run = ExportRun(
        name=name,
        includes_private=include_private,
        provenance=provenance.model_dump(mode="json") if provenance else {},
    )
    problems: list[str] = []

    for entry in dataset:
        challenge = entry.challenge
        annotation = annotations.get(entry.id)
        scanned = {"prompt": challenge.prompt, "target": challenge.target, "output": entry.output}
        if include_private and annotation:
            scanned["critique"] = annotation.critique
            scanned["evidence"] = annotation.evidence
        for field_name, text in scanned.items():
            problems.extend(
                f"{entry.id}.{field_name} contains what looks like {reason}"
                for reason in scan_for_secrets(text or "")
            )

        run.cases.append(
            ExportCase(
                id=entry.id,
                entity=challenge.entity,
                test_type=challenge.test_type,
                prompt=challenge.prompt or "",
                target=challenge.target or "",
                output=entry.output,
                label=annotation.label.value if annotation else None,
                half=challenge.half.value if challenge.half else None,
                pair_id=challenge.pair_id,
                attribute=challenge.attribute,
                critique=annotation.critique if (include_private and annotation) else "",
                evidence=annotation.evidence if (include_private and annotation) else "",
            )
        )

    if problems:
        raise ExportRefusedError(
            "refusing to export, because the display target is public:\n  " + "\n  ".join(problems)
        )

    # The pair is the scoring unit, so it travels as its own structure rather
    # than being reconstructed from case rows by whatever renders this.
    run.pairs = [
        {
            "pair_id": pair.pair_id,
            "entity": pair.entity,
            "attribute": pair.attribute,
            "halves": {half: verdict.value for half, verdict in sorted(pair.halves.items())},
            "complete": pair.complete,
            "passed": pair.passed,
        }
        for pair in pair_results(dataset, annotations)
    ]
    return run


def export_run_dir(run_dir: Path, include_private: bool = False) -> ExportRun:
    """Read a committed run directory: dataset.yaml beside annotations.yaml."""
    dataset_path = run_dir / "dataset.yaml"
    if not dataset_path.exists():
        raise ExportRefusedError(f"{run_dir} has no dataset.yaml, so there is nothing to display")

    provenance_path = run_dir / "provenance.yaml"
    provenance = (
        Provenance.model_validate(read_yaml(provenance_path).get("provenance", {}))
        if provenance_path.exists()
        else None
    )
    return build_run(
        run_dir.name,
        load_dataset(dataset_path),
        load_annotations(run_dir / "annotations.yaml"),
        include_private,
        provenance,
    )
