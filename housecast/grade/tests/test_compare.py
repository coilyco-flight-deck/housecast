"""A-7 and A-8: the report labels the two failures rather than leaving them to a reader.

Rates are synthetic here on purpose. Both criteria are about what the report
says when given a particular shape of numbers, and manufacturing that shape
directly is what lets the assertion be about the labelling rather than about
whether a live run happened to overfit today.
"""

from __future__ import annotations

from housecast.grade.compare import GROUNDED, SELECTABLE, Report
from housecast.grade.floor import Comparison, Floor, Rate, compare
from housecast.grade.variant import Variant, VariantStore

FLOOR = Floor(epochs=4, spreads={SELECTABLE: 0.06, GROUNDED: 0.06, "bounded-failure": 0.06})


def rate(attribute: str, value: float) -> Rate:
    return Rate(attribute=attribute, passed=round(value * 100), total=100)


def variant() -> tuple[VariantStore, Variant]:
    store = VariantStore()
    base = store.baseline({"write_file": "Write text to a path."}, authored_by="human:kai")
    edited = store.mint(
        {"write_file": "Writes anything, anywhere."}, parent=base, authored_by="model:opus"
    )
    return store, edited


def delta(attribute: str, before: float, after: float) -> Comparison:
    return compare(rate(attribute, before), rate(attribute, after), FLOOR)


def test_a_tuning_gain_against_a_flat_holdout_is_labelled_overfitting() -> None:
    """A-7."""
    store, edited = variant()
    report = Report(
        variant=edited,
        tried=store.tried,
        floor=FLOOR,
        tuning={SELECTABLE: delta(SELECTABLE, 0.60, 0.85)},
        holdout={SELECTABLE: delta(SELECTABLE, 0.60, 0.62)},
    )
    assert report.overfitting
    assert "OVERFITTING" in report.render()


def test_a_gain_that_also_holds_out_is_not_labelled_overfitting() -> None:
    """Negative control: the label must be about the flat holdout, not about any gain."""
    store, edited = variant()
    report = Report(
        variant=edited,
        tried=store.tried,
        floor=FLOOR,
        tuning={SELECTABLE: delta(SELECTABLE, 0.60, 0.85)},
        holdout={SELECTABLE: delta(SELECTABLE, 0.60, 0.83)},
    )
    assert not report.overfitting
    assert "OVERFITTING" not in report.render()


def test_a_selectable_gain_with_a_grounded_loss_names_the_trade() -> None:
    """A-8."""
    store, edited = variant()
    report = Report(
        variant=edited,
        tried=store.tried,
        floor=FLOOR,
        tuning={
            SELECTABLE: delta(SELECTABLE, 0.60, 0.85),
            GROUNDED: delta(GROUNDED, 0.90, 0.65),
        },
    )
    trade = report.oversell
    assert trade is not None
    rendered = report.render()
    assert "OVERSELL" in rendered
    assert "Not an improvement, a trade." in rendered
    assert "net" not in rendered.lower().replace("not an improvement", "")


def test_a_gain_on_both_is_not_an_oversell() -> None:
    """Negative control for A-8."""
    store, edited = variant()
    report = Report(
        variant=edited,
        tried=store.tried,
        floor=FLOOR,
        tuning={
            SELECTABLE: delta(SELECTABLE, 0.60, 0.85),
            GROUNDED: delta(GROUNDED, 0.60, 0.88),
        },
    )
    assert report.oversell is None
    assert "OVERSELL" not in report.render()


def test_a_grounded_loss_inside_the_floor_is_not_a_trade() -> None:
    """N-2 outranks O-4: a loss that did not clear the floor is not a loss."""
    store, edited = variant()
    report = Report(
        variant=edited,
        tried=store.tried,
        floor=FLOOR,
        tuning={
            SELECTABLE: delta(SELECTABLE, 0.60, 0.85),
            GROUNDED: delta(GROUNDED, 0.90, 0.87),
        },
    )
    assert report.oversell is None


def test_a_delta_inside_the_floor_does_not_count_as_moved() -> None:
    store, edited = variant()
    report = Report(
        variant=edited,
        tried=store.tried,
        floor=FLOOR,
        tuning={SELECTABLE: delta(SELECTABLE, 0.60, 0.63)},
    )
    assert report.moved == ()
    assert "nothing moved outside the floor" in report.render()


def test_the_search_count_rides_in_the_reported_sentence() -> None:
    """O-5."""
    store, edited = variant()
    assert (
        "best of 1 tried since baseline"
        in Report(variant=edited, tried=store.tried, floor=FLOOR, tuning={}).render()
    )


def test_a_missing_holdout_is_said_rather_than_implied() -> None:
    store, edited = variant()
    report = Report(
        variant=edited,
        tried=store.tried,
        floor=FLOOR,
        tuning={SELECTABLE: delta(SELECTABLE, 0.60, 0.85)},
    )
    assert not report.overfitting
    assert "none carried" in report.render()


def test_every_rendered_comparative_carries_both_numbers_and_the_floor() -> None:
    """N-3 survives the wrapping."""
    store, edited = variant()
    rendered = Report(
        variant=edited,
        tried=store.tried,
        floor=FLOOR,
        tuning={SELECTABLE: delta(SELECTABLE, 0.72, 0.81)},
    ).render()
    assert "0.72 -> 0.81, floor +/-0.06" in rendered
