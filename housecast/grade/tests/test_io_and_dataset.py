import pathlib
from typing import Any

from housecast.grade.dataset import build, validate
from housecast.grade.io import (
    load_annotations,
    load_dataset,
    load_profile,
    save_annotations,
    save_dataset,
)
from housecast.grade.schema import (
    AGENT_COMPOSE,
    Annotation,
    Challenge,
    DatasetEntry,
    Fit,
    Response,
    Verdict,
)


def challenge(challenge_id: str, test_type: str = "personality", **fields: Any) -> Challenge:
    return Challenge(
        id=challenge_id, entity="qa", test_type=test_type, prompt="p", target="t", **fields
    )


def test_a_dataset_round_trips_through_yaml(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "dataset.yaml"
    original = [DatasetEntry(challenge=challenge("a", attribute="candid"), output="answer")]
    save_dataset(path, original)
    assert load_dataset(path) == original


def test_annotations_round_trip_across_both_label_sets(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "annotations.yaml"
    original = {
        "a": Annotation(id="a", label=Verdict.FAIL, critique="why", evidence="span"),
        "b": Annotation(id="b", label=Fit.NO_FIT),
    }
    save_annotations(path, original)
    assert load_annotations(path) == original


def test_a_missing_annotations_file_reads_as_nothing_graded(tmp_path: pathlib.Path) -> None:
    assert load_annotations(tmp_path / "absent.yaml") == {}


def test_no_profile_named_means_the_agent_compose_profile() -> None:
    assert load_profile(None) is AGENT_COMPOSE


def test_a_declared_profile_is_read_from_yaml(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text(
        "name: sirens-echo\n"
        "test_types:\n"
        "  - name: content-class\n"
        "    label_set: binary\n"
        "    word_cap: 40\n"
        "    requires: [attribute]\n"
        "entity_order: [echo, deep]\n"
    )
    profile = load_profile(path)
    assert profile.name == "sirens-echo"
    assert profile.spec("content-class").word_cap == 40
    assert profile.entity_order == ("echo", "deep")


def test_a_sample_with_no_run_is_dropped_rather_than_silently_missing() -> None:
    report = build(
        [challenge("a", attribute="t"), challenge("b", attribute="t")],
        [Response(challenge_id="a", epoch=1, text="x")],
    )
    assert [entry.id for entry in report.kept] == ["a"]
    assert report.dropped[0].challenge_id == "b"
    assert report.summary == "1 kept, 1 dropped"


def test_the_named_epoch_is_the_one_annotated() -> None:
    responses = [
        Response(challenge_id="a", epoch=2, text="second"),
        Response(challenge_id="a", epoch=1, text="first"),
    ]
    assert build([challenge("a", attribute="t")], responses).kept[0].output == "first"
    assert build([challenge("a", attribute="t")], responses, epoch=2).kept[0].output == "second"


def test_validate_reports_every_shape_problem_at_once() -> None:
    problems = validate(
        [challenge("a", test_type="role-fit"), challenge("b", test_type="boundary")]
    )
    assert len(problems) == 4


def test_an_empty_response_is_reported_rather_than_read_as_a_fail() -> None:
    """A blank card is not the seat failing, so a grader has to be told which one it is."""
    challenge = Challenge(
        id="solo", entity="e", test_type="role-fit", prompt="p", target="t", attribute="a"
    )
    report = build([challenge], [Response(challenge_id="solo", epoch=1, text="")])
    assert report.blank == ["solo"]
    assert [entry.challenge.id for entry in report.kept] == ["solo"]
    assert not report.dropped
    assert report.summary == "1 kept, 0 dropped, 1 blank"


def test_a_run_with_text_is_not_reported_blank() -> None:
    challenge = Challenge(
        id="solo", entity="e", test_type="role-fit", prompt="p", target="t", attribute="a"
    )
    report = build([challenge], [Response(challenge_id="solo", epoch=1, text="an answer")])
    assert not report.blank
    assert report.summary == "1 kept, 0 dropped"
