"""The shape half of a response: which tool the subject reached for.

`required_tool` shipped documented as checked by the runner and was checked
nowhere, so these are the tests that would have failed before it was wired.
"""

from typing import Any

from housecast.grade.dataset import build, tool_note
from housecast.grade.schema import Challenge, DatasetEntry, Response, ToolCall


def challenge(challenge_id: str = "c1", **fields: Any) -> Challenge:
    return Challenge(
        id=challenge_id,
        entity="filesystem.write_file",
        test_type="boundary",
        prompt="p",
        target="t",
        **fields,
    )


def response(challenge_id: str = "c1", **fields: Any) -> Response:
    return Response(challenge_id=challenge_id, epoch=1, text="an answer", **fields)


def test_names_read_off_the_calls() -> None:
    made = response(calls=(ToolCall(name="write_file"), ToolCall(name="read_file")))
    assert made.tools == ("write_file", "read_file")
    assert made.called("write_file")
    assert not made.called("delete_file")


def test_a_call_carries_its_arguments_and_its_error() -> None:
    """The failing half of a schema attribute is the error, so it is evidence."""
    call = ToolCall(
        name="write_file",
        arguments={"path": "../../etc/passwd"},
        error="path escapes the declared root",
    )
    made = response(calls=(call,))
    assert made.calls[0].arguments["path"] == "../../etc/passwd"
    assert made.calls[0].error == "path escapes the declared root"


def test_note_records_the_required_call_that_happened() -> None:
    made = response(calls=(ToolCall(name="write_file"),))
    assert tool_note(challenge(required_tool="write_file"), made) == "called write_file"


def test_note_names_what_was_called_instead() -> None:
    """The point of the note: which neighbour fired, not merely that one did."""
    made = response(calls=(ToolCall(name="read_file"),))
    note = tool_note(challenge(required_tool="write_file"), made)
    assert note == "did not call write_file, called: read_file"


def test_note_distinguishes_a_wrong_call_from_no_call() -> None:
    note = tool_note(challenge(required_tool="write_file"), response())
    assert note == "did not call write_file, called: nothing"


def test_a_case_with_no_expectation_gets_no_note() -> None:
    """The negative control. A note on every entry would read as coverage."""
    made = response(calls=(ToolCall(name="read_file"),))
    assert tool_note(challenge(), made) == ""


def test_build_carries_the_note_onto_the_entry() -> None:
    written = [challenge(required_tool="write_file")]
    report = build(written, [response(calls=(ToolCall(name="read_file"),))])
    assert report.kept[0].note == "did not call write_file, called: read_file"


def test_the_note_is_not_a_drop_and_not_a_score() -> None:
    """A missing call is the grader's call, so the entry is kept and unscored."""
    report = build([challenge(required_tool="write_file")], [response()])
    assert len(report.kept) == 1
    assert not report.dropped
    assert not report.blank


def test_a_dataset_written_before_the_note_reads_back_unchanged() -> None:
    entry = DatasetEntry(challenge=challenge(), output="an answer")
    assert "note" not in entry.to_dict()
    assert DatasetEntry.from_dict(entry.to_dict()).note == ""


def test_a_note_survives_the_round_trip() -> None:
    entry = DatasetEntry(challenge=challenge(), output="an answer", note="called write_file")
    assert DatasetEntry.from_dict(entry.to_dict()).note == "called write_file"
