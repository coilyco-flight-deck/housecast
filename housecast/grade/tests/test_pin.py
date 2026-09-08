import pathlib
from typing import Any

import pytest

from housecast.grade import pin as pin_mod
from housecast.grade.annotate import entity_header
from housecast.grade.io import load_pin, pin_path, save_pin
from housecast.grade.schema import Challenge, DatasetEntry

ROSTER: dict[str, Any] = {
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
        "test_type": "personality",
        "attribute": "candid",
        "prompt": "p",
        "target": "t",
    }
    spec.update(fields)
    return DatasetEntry(challenge=Challenge(**spec), output=output)


def test_an_unchanged_run_reports_no_drift() -> None:
    dataset = [entry()]
    pinned = pin_mod.take(dataset, roster=ROSTER)
    assert pin_mod.verify(pinned, dataset, roster=ROSTER) == []


def test_a_take_is_stable_across_two_calls() -> None:
    dataset = [entry()]
    assert pin_mod.take(dataset, roster=ROSTER) == pin_mod.take(dataset, roster=ROSTER)


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
    pinned = pin_mod.take([entry()], roster=ROSTER)
    drifts = pin_mod.verify(pinned, [entry(**changed)], roster=ROSTER)
    assert [drift.input for drift in drifts] == [moved]


def test_a_changed_response_is_caught() -> None:
    pinned = pin_mod.take([entry()], roster=ROSTER)
    drifts = pin_mod.verify(pinned, [entry(output="a rerun answer")], roster=ROSTER)
    assert [drift.input for drift in drifts] == ["response"]


def test_the_word_cap_moving_is_caught_without_any_text_changing() -> None:
    """The label set and word cap are the input nothing else in the run records."""
    from housecast.grade.schema import Profile, TestTypeSpec

    narrow = Profile(name="agent-compose", test_types=(TestTypeSpec("personality", "fit", 100),))
    wide = Profile(name="agent-compose", test_types=(TestTypeSpec("personality", "fit", 40),))
    pinned = pin_mod.take([entry()], narrow, ROSTER)
    drifts = pin_mod.verify(pinned, [entry()], wide, ROSTER)
    assert [drift.input for drift in drifts] == ["labels"]


def test_the_charter_moving_is_caught_while_every_recorded_field_matches() -> None:
    """housecast#7166: two graders straddling a roster edit, and nothing else differs."""
    dataset = [entry()]
    pinned = pin_mod.take(dataset, roster=ROSTER)

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
    drifts = pin_mod.verify(pinned, dataset, roster=edited)
    assert [(drift.scope, drift.subject, drift.input) for drift in drifts] == [
        ("entity", "qa", "charter")
    ]


def test_a_case_the_pin_never_covered_is_drift() -> None:
    pinned = pin_mod.take([entry("a")], roster=ROSTER)
    drifts = pin_mod.verify(pinned, [entry("a"), entry("b")], roster=ROSTER)
    assert [(drift.subject, drift.input) for drift in drifts] == [("b", "not covered by the pin")]


def test_a_dropped_case_is_not_drift() -> None:
    """Grading a subset is ordinary. Only an input nobody pinned is the hazard."""
    pinned = pin_mod.take([entry("a"), entry("b")], roster=ROSTER)
    assert pin_mod.verify(pinned, [entry("a")], roster=ROSTER) == []


def test_a_charter_the_roster_stopped_rendering_is_caught() -> None:
    pinned = pin_mod.take([entry()], roster=ROSTER)
    drifts = pin_mod.verify(pinned, [entry()], roster={"entity_order": [], "entities": {}})
    assert [(drift.subject, drift.input) for drift in drifts] == [("qa", "no longer rendered")]


def test_check_refuses_and_names_what_moved() -> None:
    pinned = pin_mod.take([entry()], roster=ROSTER)
    with pytest.raises(pin_mod.PinMismatchError) as refused:
        pin_mod.check(pinned, [entry(prompt="moved")], roster=ROSTER)
    assert "prompt changed" in str(refused.value)
    assert "grade pin --force" in str(refused.value)


def test_check_is_silent_on_a_matching_run() -> None:
    """The negative control. Without it a check that never fires reads as a pass."""
    dataset = [entry()]
    pin_mod.check(pin_mod.take(dataset, roster=ROSTER), dataset, roster=ROSTER)


def test_the_pinned_charter_is_the_text_the_annotator_is_shown(capsys: Any) -> None:
    """A pin over a projection the renderer does not use would be a pin over nothing."""
    from rich.console import Console

    entity_header(Console(width=200, force_terminal=False), ROSTER, "qa")
    shown = capsys.readouterr().out

    for line in pin_mod.charter_lines(ROSTER, "qa"):
        for word in line.split():
            assert word in shown


def test_an_entity_absent_from_the_roster_pins_nothing() -> None:
    assert pin_mod.charter_lines(ROSTER, "nobody") == []
    assert "nobody" not in pin_mod.take([entry()], roster=ROSTER)["charters"]


def test_a_pin_round_trips_beside_its_dataset(tmp_path: pathlib.Path) -> None:
    dataset_path = tmp_path / "dataset.yaml"
    target = pin_path(dataset_path)
    assert target == tmp_path / "pin.yaml"
    assert load_pin(target) is None

    taken = pin_mod.take([entry()], roster=ROSTER)
    save_pin(target, taken)
    assert load_pin(target) == taken


def test_a_test_type_the_profile_does_not_declare_is_recorded_rather_than_raised() -> None:
    """The live board carries 14 voice cases and the shipped profile declares three types."""
    dataset = [entry("v", test_type="voice")]
    pinned = pin_mod.take(dataset, roster=ROSTER)
    assert pin_mod.verify(pinned, dataset, roster=ROSTER) == []


def test_the_profile_growing_a_type_moves_that_case_s_labels() -> None:
    from housecast.grade.schema import Profile, TestTypeSpec

    before = pin_mod.take([entry("v", test_type="voice")], roster=ROSTER)
    grown = Profile(name="agent-compose", test_types=(TestTypeSpec("voice", "binary", 50),))
    drifts = pin_mod.verify(before, [entry("v", test_type="voice")], grown, ROSTER)
    assert [drift.input for drift in drifts] == ["labels"]
