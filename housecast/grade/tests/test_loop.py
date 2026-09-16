"""The loop refuses to start without its controls, and labels what it finds.

The measurer is scripted rather than live. What these tests own is the order
the guards fire in and what the loop does with the numbers, and scripting the
numbers is what makes an assertion about the labelling rather than about
whether today's run happened to overfit.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from housecast.grade.compare import GROUNDED, SELECTABLE, Report
from housecast.grade.floor import Floor, Rate
from housecast.grade.loop import Budget, Loop, LoopError, render_all
from housecast.grade.variant import Variant, VariantStore

FLOOR = Floor(epochs=4, spreads={SELECTABLE: 0.06, GROUNDED: 0.06})
BASE_PROSE = {"write_file": "Write text to a path."}


def rates(selectable: float, grounded: float) -> dict[str, Rate]:
    return {
        SELECTABLE: Rate(SELECTABLE, round(selectable * 100), 100),
        GROUNDED: Rate(GROUNDED, round(grounded * 100), 100),
    }


class ScriptedMeasurer:
    """Baseline prose scores one way, anything else scores the scripted way."""

    def __init__(self, tuning: dict[str, Rate], holdout: dict[str, Rate] | None = None) -> None:
        self.base = rates(0.60, 0.90)
        self.base_holdout = rates(0.60, 0.90)
        self.tuning = tuning
        self.holdout = holdout or rates(0.60, 0.90)
        self.holdout_calls = 0

    def measure(self, prose: Mapping[str, str], *, holdout: bool = False) -> dict[str, Rate]:
        """Baseline prose scores one way on each side, anything else the scripted way.

        The holdout branches on prose too. A fixture returning one holdout for
        both sides makes every holdout delta zero, which is indistinguishable
        from the loop comparing the holdout against itself.
        """
        baseline = dict(prose) == BASE_PROSE
        if holdout:
            self.holdout_calls += 1
            return self.base_holdout if baseline else self.holdout
        return self.base if baseline else self.tuning


class CountingEditor:
    """Proposes a fresh description each round."""

    authored_by = "model:opus"

    def __init__(self) -> None:
        self.calls = 0

    def propose(self, current: Mapping[str, str], report: Report) -> Mapping[str, str]:
        self.calls += 1
        return {"write_file": f"Writes anything, anywhere. Revision {self.calls}."}


def build(measurer: ScriptedMeasurer, budget: Budget | None = None) -> tuple[Loop, Variant]:
    store = VariantStore()
    baseline = store.baseline(BASE_PROSE, authored_by="human:kai")
    loop = Loop(
        store=store,
        measurer=measurer,
        editor=CountingEditor(),
        floor=FLOOR,
        declared_epochs=4,
        budget=budget,
    )
    return loop, baseline


def test_a_loop_without_a_floor_refuses_to_start() -> None:
    """A board whose floor is unestablished cannot report a readable delta."""
    with pytest.raises(LoopError, match="no floor was established"):
        Loop(
            store=VariantStore(),
            measurer=ScriptedMeasurer(rates(0.85, 0.90)),
            editor=CountingEditor(),
            floor=Floor(epochs=4, spreads={}),
            declared_epochs=4,
        )


def test_a_floor_at_a_different_epoch_count_refuses() -> None:
    """N-4, enforced where the loop can see both numbers."""
    with pytest.raises(LoopError, match="never raised after seeing a result"):
        Loop(
            store=VariantStore(),
            measurer=ScriptedMeasurer(rates(0.85, 0.90)),
            editor=CountingEditor(),
            floor=FLOOR,
            declared_epochs=8,
        )


def test_a_matching_declaration_starts() -> None:
    """Negative control for the two refusals above."""
    loop, baseline = build(ScriptedMeasurer(rates(0.85, 0.90)))
    assert loop.run(baseline, rounds=1)


def test_the_loop_labels_an_oversell_it_produced() -> None:
    """A-8, reached through the loop rather than through a hand-built report."""
    loop, baseline = build(ScriptedMeasurer(rates(0.85, 0.65)))
    rendered = render_all(loop.run(baseline, rounds=1))
    assert "OVERSELL" in rendered
    assert "Not an improvement, a trade." in rendered


def test_the_loop_labels_overfitting_it_produced() -> None:
    """A-7, reached through the loop."""
    measurer = ScriptedMeasurer(rates(0.85, 0.90), holdout=rates(0.60, 0.90))
    loop, baseline = build(measurer, budget=Budget(holdout_runs=4))
    rendered = render_all(loop.run(baseline, rounds=1))
    assert "OVERFITTING" in rendered


def test_the_holdout_budget_refuses_once_spent() -> None:
    """O-2."""
    measurer = ScriptedMeasurer(rates(0.85, 0.90), holdout=rates(0.60, 0.90))
    loop, baseline = build(measurer, budget=Budget(holdout_runs=2))
    with pytest.raises(LoopError, match="budget of 2 is spent"):
        loop.run(baseline, rounds=3)


def test_a_gain_that_also_holds_out_is_not_labelled_overfitting() -> None:
    """The control the first cut of this loop lacked.

    Comparing a variant's holdout against itself makes every holdout delta zero,
    which labels every gain as overfitting. Only a variant whose holdout also
    moved can prove the comparison is against the baseline holdout.
    """
    measurer = ScriptedMeasurer(rates(0.85, 0.90), holdout=rates(0.84, 0.90))
    loop, baseline = build(measurer, budget=Budget(holdout_runs=4))
    rendered = render_all(loop.run(baseline, rounds=1))
    assert "OVERFITTING" not in rendered


def test_a_holdout_within_budget_does_not_refuse() -> None:
    """Negative control for the budget."""
    measurer = ScriptedMeasurer(rates(0.85, 0.90), holdout=rates(0.60, 0.90))
    loop, baseline = build(measurer, budget=Budget(holdout_runs=5))
    assert len(loop.run(baseline, rounds=3)) == 3


def test_the_search_count_climbs_with_the_rounds() -> None:
    """O-5: the reader is shown how wide the search was, not just its winner."""
    loop, baseline = build(ScriptedMeasurer(rates(0.85, 0.90)))
    reports = loop.run(baseline, rounds=4)
    assert [r.tried for r in reports] == [1, 2, 3, 4]
    assert "best of 4 tried since baseline" in reports[-1].render()


def test_a_variant_that_did_nothing_is_not_reported_as_a_gain() -> None:
    """N-2 survives the whole way up."""
    loop, baseline = build(ScriptedMeasurer(rates(0.63, 0.90)))
    rendered = render_all(loop.run(baseline, rounds=1))
    assert "nothing moved outside the floor" in rendered
    assert "OVERSELL" not in rendered


def test_every_variant_the_loop_mints_is_attributed() -> None:
    """The three-way circularity control reaches the variants the loop makes itself."""
    loop, baseline = build(ScriptedMeasurer(rates(0.85, 0.90)))
    reports = loop.run(baseline, rounds=2)
    assert all(r.variant.authored_by == "model:opus" for r in reports)
