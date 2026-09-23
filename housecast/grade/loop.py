"""The iteration loop: measure, propose, mint, re-measure, compare.

Built last, after its controls, because a loop without the floor and the
overfitting labels reports improvements that are not there. What this module
adds is the order the guards fire in. It refuses to start rather than warning,
because a warning at the top of an unwatched run is no control at all.
Rules in `teable:coilyco-flight-deck/housecast#7802`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from housecast.grade.compare import Report
from housecast.grade.floor import Comparison, Floor, Rate, compare
from housecast.grade.variant import Variant, VariantStore


class LoopError(RuntimeError):
    """Raised when the loop is asked to run without a control it requires."""


class ProseEditor(Protocol):
    """Proposes the next variant's prose from the last report.

    A protocol because an editor is usually a model, and which model is
    transport's business rather than the loop's. Whatever implements this is
    recorded as the variant's author.
    """

    @property
    def authored_by(self) -> str:
        """`human:<name>` or `model:<id>`, recorded on every variant it mints."""
        ...

    def propose(self, current: Mapping[str, str], report: Report) -> Mapping[str, str]:
        """The next prose to try."""
        ...


class Measurer(Protocol):
    """Runs a board against one variant's prose and returns per-attribute rates."""

    def measure(self, prose: Mapping[str, str], *, holdout: bool = False) -> dict[str, Rate]: ...


@dataclass(frozen=True)
class Budget:
    """O-2: a holdout consulted repeatedly is a tuning set with extra steps."""

    holdout_runs: int

    def spend(self, spent: int) -> None:
        if spent >= self.holdout_runs:
            raise LoopError(
                f"holdout budget of {self.holdout_runs} is spent. "
                "Consulting it again would make it a tuning set."
            )


@dataclass
class Loop:
    """One board, one subject, and the variants tried against it."""

    store: VariantStore
    measurer: Measurer
    editor: ProseEditor
    floor: Floor
    declared_epochs: int
    budget: Budget | None = None
    _holdout_spent: int = 0
    _base_holdout: dict[str, Rate] | None = None

    def __post_init__(self) -> None:
        if self.floor.epochs != self.declared_epochs:
            raise LoopError(
                f"the floor was established at E={self.floor.epochs} and this loop "
                f"declares E={self.declared_epochs}. N-4: E is declared before the "
                "first run and never raised after seeing a result."
            )
        if not self.floor.spreads:
            raise LoopError(
                "no floor was established, so every delta this loop reports would be "
                "unreadable. Establish it with two runs of one variant first."
            )

    def run(self, baseline: Variant, rounds: int) -> list[Report]:
        """`rounds` proposals, each measured and reported against the baseline."""
        base_rates = self.measurer.measure(baseline.prose)
        # Taken once: comparing a variant's holdout against itself makes every
        # delta zero, which labels every gain as overfitting.
        self._base_holdout = (
            self.measurer.measure(baseline.prose, holdout=True) if self.budget else None
        )
        reports: list[Report] = []
        current = baseline
        for _ in range(rounds):
            proposed = self.editor.propose(
                current.prose, reports[-1] if reports else self._empty_report(baseline, base_rates)
            )
            minted = self.store.mint(proposed, parent=current, authored_by=self.editor.authored_by)
            if minted.digest == current.digest:
                # The editor proposed prose already tried. Not an error, and not
                # a new result either, so the round is spent rather than counted.
                continue
            reports.append(self._report(minted, base_rates))
            current = minted
        return reports

    def _report(self, variant: Variant, base_rates: Mapping[str, Rate]) -> Report:
        tuning = self._deltas(base_rates, self.measurer.measure(variant.prose))
        holdout = None
        if self.budget is not None and self._base_holdout is not None:
            self.budget.spend(self._holdout_spent)
            self._holdout_spent += 1
            holdout = self._deltas(
                self._base_holdout,
                self.measurer.measure(variant.prose, holdout=True),
            )
        return Report(
            variant=variant,
            tried=self.store.tried,
            floor=self.floor,
            tuning=tuning,
            holdout=holdout,
        )

    def _empty_report(self, variant: Variant, rates: Mapping[str, Rate]) -> Report:
        return Report(
            variant=variant,
            tried=self.store.tried,
            floor=self.floor,
            tuning=self._deltas(rates, rates),
        )

    def _deltas(
        self, before: Mapping[str, Rate], after: Mapping[str, Rate]
    ) -> dict[str, Comparison]:
        return {
            attribute: compare(before[attribute], after[attribute], self.floor)
            for attribute in sorted(before.keys() & after.keys())
        }


def render_all(reports: Sequence[Report]) -> str:
    """Every round, in order, so a reader sees the search rather than its winner."""
    if not reports:
        return "no variant cleared minting, so the loop reported nothing"
    return "\n\n".join(report.render() for report in reports)
