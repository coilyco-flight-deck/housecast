import pathlib
from typing import Any

import pytest

from housecast.grade import pin as pin_mod
from housecast.grade.annotate import entity_header
from housecast.grade.io import load_pin, pin_path, save_pin
from housecast.grade.schema import Challenge, DatasetEntry
from housecast.grade.tests.fixtures import PROFILE

PROJECTION: dict[str, Any] = {
    "entity_order": ["qa"],
    "entities": {
        "qa": {
            "display_name": "Quinn",
            "purpose": "checks things",
            "notes": ["owns: b-one", "traits: candid", "adjacent ops: shares the pager"],
        }
    },
}


def entry(challenge_id: str = "a", output: str = "answer", **fields: Any) -> DatasetEntry:
    spec: dict[str, Any] = {
        "id": challenge_id,
        "entity": "qa",
        "test_type": "degree",
        "attribute": "candid",
        "prompt": "p",
        "target": "t",
    }
    spec.update(fields)
    return DatasetEntry(challenge=Challenge(**spec), output=output)


def test_an_unchanged_run_reports_no_drift() -> None:
    dataset = [entry()]
    pinned = pin_mod.take(dataset, PROFILE, PROJECTION)
    assert pin_mod.verify(pinned, dataset, PROFILE, PROJECTION) == []


def test_a_take_is_stable_across_two_calls() -> None:
    dataset = [entry()]
    assert pin_mod.take(dataset, PROFILE, PROJECTION) == pin_mod.take(dataset, PROFILE, PROJECTION)


@pytest.mark.parametrize(
    ("field", "changed", "moved"),
    [
        ("prompt", {"prompt": "a different question"}, "prompt"),
        ("target", {"target": "a different target"}, "target"),
    ],
)
def test_each_dataset_input_is_caught_on_its_own(
    field: str, changed: dict[str, Any], moved: str
) -> None:
    pinned = pin_mod.take([entry()], PROFILE, PROJECTION)
    drifts = pin_mod.verify(pinned, [entry(**changed)], PROFILE, PROJECTION)
    assert [drift.input for drift in drifts] == [moved]


def test_a_changed_response_is_caught() -> None:
    pinned = pin_mod.take([entry()], PROFILE, PROJECTION)
    drifts = pin_mod.verify(pinned, [entry(output="a rerun answer")], PROFILE, PROJECTION)
    assert [drift.input for drift in drifts] == ["response"]


def test_the_word_cap_moving_is_caught_without_any_text_changing() -> None:
    """The label set and word cap are the input nothing else in the run records."""
    from housecast.grade.schema import Profile, TestTypeSpec

    narrow = Profile(name="fixture", test_types=(TestTypeSpec("degree", "fit", 100),))
    wide = Profile(name="fixture", test_types=(TestTypeSpec("degree", "fit", 40),))
    pinned = pin_mod.take([entry()], narrow, PROJECTION)
    drifts = pin_mod.verify(pinned, [entry()], wide, PROJECTION)
    assert [drift.input for drift in drifts] == ["labels"]


def test_the_charter_moving_is_caught_while_every_recorded_field_matches() -> None:
    """housecast#7166: two graders straddling a projection edit, and nothing else differs."""
    dataset = [entry()]
    pinned = pin_mod.take(dataset, PROFILE, PROJECTION)

    edited: dict[str, Any] = {
        "entity_order": ["qa"],
        "entities": {
            "qa": {
                "display_name": "Quinn",
                "purpose": "checks things",
                "notes": ["owns: b-one", "traits: candid", "adjacent ops: carries the pager"],
            }
        },
    }
    drifts = pin_mod.verify(pinned, dataset, PROFILE, edited)
    assert [(drift.scope, drift.subject, drift.input) for drift in drifts] == [
        ("entity", "qa", "charter")
    ]


def test_a_case_the_pin_never_covered_is_drift() -> None:
    pinned = pin_mod.take([entry("a")], PROFILE, PROJECTION)
    drifts = pin_mod.verify(pinned, [entry("a"), entry("b")], PROFILE, PROJECTION)
    assert [(drift.subject, drift.input) for drift in drifts] == [("b", "not covered by the pin")]


def test_a_dropped_case_is_not_drift() -> None:
    """Grading a subset is ordinary. Only an input nobody pinned is the hazard."""
    pinned = pin_mod.take([entry("a"), entry("b")], PROFILE, PROJECTION)
    assert pin_mod.verify(pinned, [entry("a")], PROFILE, PROJECTION) == []


def test_a_charter_the_projection_stopped_rendering_is_caught() -> None:
    pinned = pin_mod.take([entry()], PROFILE, PROJECTION)
    drifts = pin_mod.verify(pinned, [entry()], PROFILE, {"entity_order": [], "entities": {}})
    assert [(drift.subject, drift.input) for drift in drifts] == [("qa", "no longer rendered")]


def test_check_refuses_and_names_what_moved() -> None:
    pinned = pin_mod.take([entry()], PROFILE, PROJECTION)
    with pytest.raises(pin_mod.PinMismatchError) as refused:
        pin_mod.check(pinned, [entry(prompt="moved")], PROFILE, PROJECTION)
    assert "prompt changed" in str(refused.value)
    assert "grade pin --force" in str(refused.value)


def test_check_is_silent_on_a_matching_run() -> None:
    """The negative control. Without it a check that never fires reads as a pass."""
    dataset = [entry()]
    pin_mod.check(pin_mod.take(dataset, PROFILE, PROJECTION), dataset, PROFILE, PROJECTION)


def test_the_pinned_charter_is_the_text_the_annotator_is_shown(capsys: Any) -> None:
    """A pin over a projection the renderer does not use would be a pin over nothing."""
    from rich.console import Console

    entity_header(Console(width=200, force_terminal=False), PROJECTION, "qa")
    shown = capsys.readouterr().out

    for line in pin_mod.charter_lines(PROJECTION, "qa"):
        for word in line.split():
            assert word in shown


def test_an_entity_absent_from_the_projection_pins_nothing() -> None:
    assert pin_mod.charter_lines(PROJECTION, "nobody") == []
    assert "nobody" not in pin_mod.take([entry()], PROFILE, PROJECTION)["charters"]


def test_a_pin_round_trips_beside_its_dataset(tmp_path: pathlib.Path) -> None:
    dataset_path = tmp_path / "dataset.yaml"
    target = pin_path(dataset_path)
    assert target == tmp_path / "pin.yaml"
    assert load_pin(target) is None

    taken = pin_mod.take([entry()], PROFILE, PROJECTION)
    save_pin(target, taken)
    assert load_pin(target) == taken


def test_a_test_type_the_profile_does_not_declare_is_recorded_rather_than_raised() -> None:
    """The live board carries 14 voice cases and the shipped profile declares three types."""
    dataset = [entry("v", test_type="voice")]
    pinned = pin_mod.take(dataset, PROFILE, PROJECTION)
    assert pin_mod.verify(pinned, dataset, PROFILE, PROJECTION) == []


def test_the_profile_growing_a_type_moves_that_case_s_labels() -> None:
    from housecast.grade.schema import Profile, TestTypeSpec

    before = pin_mod.take([entry("v", test_type="voice")], PROFILE, PROJECTION)
    grown = Profile(name="fixture", test_types=(TestTypeSpec("voice", "binary", 50),))
    drifts = pin_mod.verify(before, [entry("v", test_type="voice")], grown, PROJECTION)
    assert [drift.input for drift in drifts] == ["labels"]
