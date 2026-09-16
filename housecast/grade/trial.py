"""One measured turn, and everything a comparison of two of them depends on.

An unrecorded input is an uncontrolled variable. This is where most homegrown
prompt-optimization tooling quietly fails: the prose changes, the model version
changes underneath it the same week, and the improvement is attributed to the
edit. Refusing to pool is cheap and is the difference between a measurement and
an anecdote.

The refusals here never average across a difference. They name which side moved
and stop.

Rules D-5, K-3, K-4 and K-5 in `teable:coilyco-flight-deck/housecast#7802`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

from housecast.digest import digest


class ProvenanceError(ValueError):
    """Raised when a comparison would span a difference it cannot see through."""


@dataclass(frozen=True)
class Provenance:
    """Every input that changes what was measured.

    `variant` is deliberately not in the equality check used by the refusals:
    across variants differing prose IS the measurement, and everything else
    must be identical. Within one variant the pin refuses exactly as it did
    before this loop existed.
    """

    board: str
    fixture: str
    roster: str
    subject_version: str
    model: str
    temperature: float
    harness_mode: str
    seed: int | None = None

    def canonical(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, sort_keys=True)

    @property
    def digest(self) -> str:
        return digest(self.canonical())

    def differences(self, other: Provenance) -> tuple[str, ...]:
        return tuple(
            field
            for field in sorted(self.__dict__)
            if getattr(self, field) != getattr(other, field)
        )


@dataclass(frozen=True)
class Trial:
    """One case, driven once, against one variant."""

    challenge_id: str
    variant: str
    epoch: int
    provenance: Provenance
    response: str
    tools_called: tuple[str, ...] = ()

    def rebased(self, provenance: Provenance) -> Trial:
        """K-5: committed evidence is never rewritten, so this returns a copy."""
        return replace(self, provenance=provenance)


def require_poolable(trials: Sequence[Trial]) -> None:
    """D-5: refuse to pool trials whose provenance differs, and say which side moved."""
    if not trials:
        return
    first = trials[0].provenance
    for trial in trials[1:]:
        moved = first.differences(trial.provenance)
        if moved:
            raise ProvenanceError(
                f"cannot pool {trials[0].challenge_id} with {trial.challenge_id}: "
                f"{', '.join(moved)} moved between the two runs"
            )


def require_one_variant(trials: Iterable[Trial]) -> str:
    """K-4: grades are never pooled across variants, and no denominator spans two."""
    variants = {trial.variant for trial in trials}
    if len(variants) > 1:
        raise ProvenanceError(
            f"a denominator cannot span {len(variants)} variants: {sorted(variants)}. "
            "Variants are compared, never combined."
        )
    return variants.pop() if variants else ""


def require_comparable(left: Sequence[Trial], right: Sequence[Trial]) -> None:
    """K-3: across variants, differing prose is the measurement and nothing else may move."""
    require_poolable(left)
    require_poolable(right)
    if not left or not right:
        return
    moved = left[0].provenance.differences(right[0].provenance)
    if moved:
        raise ProvenanceError(
            f"cannot compare these variants: {', '.join(moved)} moved as well as the prose. "
            "Differing prose is the measurement, so every other input must be identical."
        )
    if require_one_variant(left) == require_one_variant(right):
        raise ProvenanceError("both sides are the same variant, so there is nothing to compare")
