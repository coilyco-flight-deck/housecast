"""The noise floor, and the refusal to read a delta through it.

Two runs of one variant differ, so without that spread every delta is
unreadable. The floor belongs to the board, model and subject together, and is
re-measured when any of them moves. A floor wider than the effect you care about
means there is no experiment, and `Floor.render` says so after one pair of runs.
Rules N-1 to N-5 in `teable:coilyco-flight-deck/housecast#7802`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from housecast.grade.schema import PairResult


class FloorError(ValueError):
    """Raised when the epoch count moves after it was declared."""


@dataclass(frozen=True)
class Rate:
    """One attribute's pass rate over the pairs that scored it."""

    attribute: str
    passed: int
    total: int

    @property
    def value(self) -> float:
        return self.passed / self.total if self.total else 0.0


@dataclass(frozen=True)
class Floor:
    """Per-attribute spread between two runs of one variant."""

    epochs: int
    spreads: Mapping[str, float]

    def of(self, attribute: str) -> float:
        """An attribute absent from both runs has no measured floor, so it reads as unbounded."""
        return self.spreads.get(attribute, float("inf"))

    @property
    def widest(self) -> float:
        return max(self.spreads.values(), default=0.0)

    def render(self) -> str:
        """N-5: reportable with no comparison in sight."""
        if not self.spreads:
            return f"floor not established, E={self.epochs}, no attribute scored in both runs"
        lines = [f"noise floor over two runs at E={self.epochs}, widest +/-{self.widest:.2f}"]
        lines += [
            f"  {attribute:<24} +/-{spread:.2f}"
            for attribute, spread in sorted(self.spreads.items())
        ]
        return "\n".join(lines)


@dataclass(frozen=True)
class Comparison:
    """One attribute's delta, read against the floor rather than against zero."""

    attribute: str
    before: float
    after: float
    floor: float

    @property
    def delta(self) -> float:
        return self.after - self.before

    @property
    def within_noise(self) -> bool:
        return abs(self.delta) <= self.floor

    def render(self) -> str:
        """N-3: both numbers and the floor, every time. N-2: never improved, regressed, or tied."""
        body = f"{self.before:.2f} -> {self.after:.2f}, floor +/-{self.floor:.2f}"
        return f"{self.attribute}: {body}" + (", within noise" if self.within_noise else "")


def rates(pairs: Iterable[PairResult]) -> dict[str, Rate]:
    """Pass rate per attribute. Only complete pairs score, because a half is not a result."""
    passed: dict[str, int] = {}
    total: dict[str, int] = {}
    for pair in pairs:
        if not pair.complete:
            continue
        total[pair.attribute] = total.get(pair.attribute, 0) + 1
        passed[pair.attribute] = passed.get(pair.attribute, 0) + (1 if pair.passed else 0)
    return {
        attribute: Rate(attribute=attribute, passed=passed[attribute], total=count)
        for attribute, count in total.items()
    }


def establish(
    first: Iterable[PairResult],
    second: Iterable[PairResult],
    *,
    epochs: int,
    declared_epochs: int | None = None,
) -> Floor:
    """N-1: one variant, two runs at E epochs, the per-attribute spread between them.

    `declared_epochs` is N-4. Passing the number written down before the first
    run makes raising E after seeing a result fail here rather than pass
    quietly. Enforcement across sessions arrives with the variant store, which
    is where a declaration outlives a process.
    """
    if epochs < 1:
        raise FloorError(f"epochs must be at least 1, got {epochs}")
    if declared_epochs is not None and epochs != declared_epochs:
        raise FloorError(
            f"E was declared as {declared_epochs} and this run used {epochs}. "
            "Raising epochs until a delta clears the floor is the error N-4 names."
        )
    left, right = rates(first), rates(second)
    shared = left.keys() & right.keys()
    return Floor(
        epochs=epochs,
        spreads={
            attribute: abs(left[attribute].value - right[attribute].value) for attribute in shared
        },
    )


def compare(before: Rate, after: Rate, floor: Floor) -> Comparison:
    """N-2 and N-3 together: the delta, both its numbers, and the floor it is read against."""
    if before.attribute != after.attribute:
        raise FloorError(
            f"cannot compare {before.attribute!r} against {after.attribute!r}: "
            "a delta spans one attribute"
        )
    return Comparison(
        attribute=before.attribute,
        before=before.value,
        after=after.value,
        floor=floor.of(before.attribute),
    )
