"""Axial coding. Groups critiques into a ranked failure taxonomy.

The practitioner references describe error analysis as open coding, then axial
coding, then a taxonomy. Critiques are the open codes. This is the axial step,
and the taxonomy is what you act on.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from housecast.grade.schema import Annotation, DatasetEntry

# Open codes are prose. Grouping them needs a shared vocabulary, so the
# taxonomy keys off the axes the dataset already carries.
STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "it",
        "its",
        "is",
        "was",
        "be",
        "been",
        "are",
        "and",
        "or",
        "but",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "without",
        "that",
        "this",
        "these",
        "those",
        "then",
        "than",
        "as",
        "at",
        "by",
        "from",
        "into",
        "over",
        "under",
        "not",
        "no",
        "non",
        "do",
        "does",
        "did",
        "done",
        "have",
        "has",
        "had",
        "you",
        "your",
        "they",
        "their",
        "them",
        "role",
        "instead",
        "rather",
    ]
)


@dataclass
class FailureMode:
    """One axial category: a recurring failure with the challenges that show it."""

    key: str
    challenge_ids: list[str] = field(default_factory=list)
    entities: Counter[str] = field(default_factory=Counter)
    test_types: Counter[str] = field(default_factory=Counter)
    evidence: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.challenge_ids)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "failure_mode": self.key,
            "count": self.count,
            "entities": dict(self.entities.most_common()),
            "test_types": dict(self.test_types.most_common()),
            "challenges": sorted(self.challenge_ids),
        }
        if self.evidence:
            payload["evidence"] = self.evidence[:3]
        return payload


def axis_of(entry: DatasetEntry) -> str:
    """The structural axis a failure sits on, before its prose is considered.

    Derived rather than enumerated, so a deployment declaring a test type this
    layer has never heard of still gets an axis with detail on it.
    """
    challenge = entry.challenge
    if not challenge.attribute:
        return challenge.test_type
    axis = f"{challenge.test_type}:{challenge.attribute}"
    return f"{axis}:{challenge.half.value}" if challenge.half else axis


def salient_terms(critique: str, limit: int = 3) -> list[str]:
    words = [w for w in re.findall(r"[a-z][a-z-]{2,}", critique.lower()) if w not in STOPWORDS]
    return [word for word, _ in Counter(words).most_common(limit)]


def build(dataset: list[DatasetEntry], annotations: dict[str, Annotation]) -> list[FailureMode]:
    """Group every deduction by structural axis, then by shared critique terms."""
    by_id = {entry.id: entry for entry in dataset}
    modes: dict[str, FailureMode] = {}

    for annotation in annotations.values():
        if not annotation.is_deduction:
            continue
        entry = by_id.get(annotation.id)
        if entry is None:
            continue
        terms = salient_terms(annotation.critique)
        key = axis_of(entry)
        if terms:
            key = f"{key} / {' '.join(sorted(terms))}"
        mode = modes.setdefault(key, FailureMode(key=key))
        mode.challenge_ids.append(annotation.id)
        mode.entities[entry.challenge.entity] += 1
        mode.test_types[entry.challenge.test_type] += 1
        if annotation.evidence:
            mode.evidence.append(annotation.evidence)

    return sorted(modes.values(), key=lambda mode: (-mode.count, mode.key))


def render(modes: list[FailureMode], total: int) -> str:
    if not modes:
        return "no deductions recorded, so there is no taxonomy to build"
    lines = [f"{sum(mode.count for mode in modes)} deductions across {total} challenges", ""]
    for index, mode in enumerate(modes, start=1):
        entities = ", ".join(f"{e} x{n}" for e, n in mode.entities.most_common())
        lines.append(f"{index:2d}. [{mode.count}] {mode.key}")
        lines.append(f"      entities: {entities}")
        lines.append(f"      challenges: {', '.join(sorted(mode.challenge_ids))}")
    return "\n".join(lines)
