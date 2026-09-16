"""The report that reads a variant's numbers without overstating them.

Three pressures the loop creates on purpose, each with its label here:

* a delta inside the noise floor is not a result (N-2), so it never renders as
  an improvement
* a tuning gain against a flat holdout is the overfitting signature (O-3), so
  it is labelled rather than left for a reader to notice
* a `selectable` gain bought with a `description-grounded` loss is an oversell
  (O-4), so the trade is named rather than netted

None of the three is a judgement the report defers to whoever reads it. They
are the reasons the loop needs a report at all rather than a number.

Rules O-3, O-4 and O-5, and acceptance A-7 and A-8, in
`teable:coilyco-flight-deck/housecast#7802`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from housecast.grade.floor import Comparison, Floor
from housecast.grade.variant import Variant

SELECTABLE = "selectable"
GROUNDED = "description-grounded"


@dataclass(frozen=True)
class Report:
    """One variant's result, with every control that qualifies it attached."""

    variant: Variant
    tried: int
    floor: Floor
    tuning: Mapping[str, Comparison]
    holdout: Mapping[str, Comparison] | None = None

    @property
    def moved(self) -> tuple[Comparison, ...]:
        """Only the attributes whose delta clears the floor. The rest are not results."""
        return tuple(c for c in self.tuning.values() if not c.within_noise)

    @property
    def overfitting(self) -> bool:
        """O-3: a tuning gain with a flat holdout.

        Flat means inside the floor rather than exactly zero, because a holdout
        delta is as stochastic as a tuning one and demanding zero would never fire.
        """
        if self.holdout is None:
            return False
        gained = [c for c in self.moved if c.delta > 0]
        if not gained:
            return False
        return all(
            self.holdout[c.attribute].within_noise for c in gained if c.attribute in self.holdout
        )

    @property
    def oversell(self) -> tuple[Comparison, Comparison] | None:
        """O-4: a `selectable` gain bought with a `description-grounded` loss."""
        gain = self.tuning.get(SELECTABLE)
        loss = self.tuning.get(GROUNDED)
        if gain is None or loss is None:
            return None
        if gain.within_noise or loss.within_noise:
            return None
        return (gain, loss) if gain.delta > 0 and loss.delta < 0 else None

    def render(self) -> str:
        """O-5 rides in the sentence carrying the delta, not in a log."""
        lines = [
            f"variant {self.variant.short()}, best of {self.tried} tried since baseline, "
            f"authored by {self.variant.authored_by}"
        ]
        lines += [f"  tuning   {c.render()}" for c in sorted_by_attribute(self.tuning)]
        if self.holdout is not None:
            lines += [f"  holdout  {c.render()}" for c in sorted_by_attribute(self.holdout)]
        else:
            lines.append("  holdout  none carried, so no tuning gain here is checked against one")

        trade = self.oversell
        if trade is not None:
            gain, loss = trade
            lines.append(
                f"  OVERSELL {gain.attribute} gained {gain.delta:+.2f} while "
                f"{loss.attribute} lost {loss.delta:+.2f}. Not an improvement, a trade."
            )
        if self.overfitting:
            lines.append(
                "  OVERFITTING tuning gained and the holdout stayed inside the floor. "
                "The gain is against these cases rather than against the task."
            )
        if not self.moved:
            lines.append("  nothing moved outside the floor")
        return "\n".join(lines)


def sorted_by_attribute(comparisons: Mapping[str, Comparison]) -> list[Comparison]:
    return [comparisons[key] for key in sorted(comparisons)]
