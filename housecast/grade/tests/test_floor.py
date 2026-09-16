"""A-6 and the rules around it.

The fixture is deliberately stochastic because a floor measured against a
deterministic one is zero, and a zero floor makes every later assertion pass
for the wrong reason. Seeded, so the numbers below are reproducible rather
than merely plausible.
"""

from __future__ import annotations

import random

import pytest

from housecast.grade.floor import (
    Comparison,
    Floor,
    FloorError,
    Rate,
    compare,
    establish,
    rates,
)
from housecast.grade.schema import PairResult, Verdict

ATTRIBUTES = ("selectable", "schema-honest", "bounded-failure")
PAIRS_PER_ATTRIBUTE = 12


def rate_at(attribute: str, value: float, total: int = 100) -> Rate:
    return Rate(attribute=attribute, passed=round(value * total), total=total)


def run(seed: int, pass_rate: float = 0.6) -> list[PairResult]:
    """One board run. Each pair passes or fails on its own coin, which is the stochasticity."""
    rng = random.Random(seed)
    results = []
    for attribute in ATTRIBUTES:
        for index in range(PAIRS_PER_ATTRIBUTE):
            verdict = Verdict.PASS if rng.random() < pass_rate else Verdict.FAIL
            results.append(
                PairResult(
                    pair_id=f"{attribute}-{index}",
                    entity="filesystem.write_file",
                    attribute=attribute,
                    halves={"in": verdict, "out": Verdict.PASS},
                )
            )
    return results


def test_two_runs_of_one_variant_produce_a_non_zero_floor() -> None:
    """A-6, first half."""
    floor = establish(run(1), run(2), epochs=4)
    assert set(floor.spreads) == set(ATTRIBUTES)
    assert floor.widest > 0.0


def test_a_delta_smaller_than_the_floor_is_reported_within_noise() -> None:
    """A-6, second half. The synthetic delta is half the measured floor."""
    floor = establish(run(1), run(2), epochs=4)
    attribute = max(floor.spreads, key=lambda a: floor.spreads[a])
    width = floor.of(attribute)
    before = rate_at(attribute, 0.50)
    after = rate_at(attribute, 0.50 + width / 2)
    result = compare(before, after, floor)
    assert result.within_noise
    assert "within noise" in result.render()


def test_a_delta_larger_than_the_floor_is_not_within_noise() -> None:
    floor = Floor(epochs=4, spreads={"selectable": 0.06})
    result = compare(rate_at("selectable", 0.72), rate_at("selectable", 0.90), floor)
    assert not result.within_noise


def test_every_comparative_carries_both_numbers_and_the_floor() -> None:
    """N-3. `improved` is not a result."""
    rendered = Comparison(attribute="selectable", before=0.72, after=0.81, floor=0.06).render()
    assert "0.72 -> 0.81" in rendered
    assert "floor +/-0.06" in rendered
    for banned in ("improved", "regressed", "tie", "better", "worse"):
        assert banned not in rendered


def test_the_floor_reports_with_no_comparison_made() -> None:
    """N-5."""
    rendered = establish(run(1), run(2), epochs=4).render()
    assert "noise floor over two runs at E=4" in rendered
    for attribute in ATTRIBUTES:
        assert attribute in rendered


def test_raising_epochs_after_declaring_them_refuses() -> None:
    """N-4."""
    with pytest.raises(FloorError, match="declared as 4"):
        establish(run(1), run(2), epochs=8, declared_epochs=4)


def test_matching_the_declaration_is_accepted() -> None:
    """Negative control for the rule above: the refusal is about the mismatch, not the argument."""
    assert establish(run(1), run(2), epochs=4, declared_epochs=4).epochs == 4


def test_an_incomplete_pair_does_not_score() -> None:
    half_only = [
        PairResult(pair_id="p1", entity="e", attribute="selectable", halves={"in": Verdict.PASS})
    ]
    assert rates(half_only) == {}


def test_an_attribute_absent_from_both_runs_has_no_floor() -> None:
    """Unbounded rather than zero, so a missing measurement cannot read as a tight floor."""
    floor = establish(run(1), run(2), epochs=4)
    assert floor.of("never-measured") == float("inf")
    wide = compare(rate_at("never-measured", 0.10), rate_at("never-measured", 0.90), floor)
    assert wide.within_noise, "an unmeasured attribute cannot report a readable delta"


def test_comparing_two_different_attributes_refuses() -> None:
    floor = Floor(epochs=4, spreads={"selectable": 0.06})
    with pytest.raises(FloorError, match="a delta spans one attribute"):
        compare(rate_at("selectable", 0.5), rate_at("schema-honest", 0.5), floor)


def test_the_fixture_is_actually_stochastic() -> None:
    """Negative control: if the two runs were identical the floor would be zero throughout."""
    assert rates(run(1)) != rates(run(2))
