"""The `housecast grade` dispatcher's error path.

`housecast.__main__._grade` forwards with `standalone_mode=False` so it can
return an int rather than exiting. That also turns off click's own error
printing, so without a handler every usage error reaches the terminal as a
traceback. See housecast#7196.
"""

import pathlib

import pytest

from housecast.__main__ import main


def test_a_missing_required_option_is_a_message_rather_than_a_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["grade", "pin"])

    assert code != 0
    assert "Missing option '--dataset'" in capsys.readouterr().err


def test_the_roster_guard_reaches_the_terminal_as_one_line(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    person = tmp_path / "person.json"
    person.write_text('{"role_order": [], "roles": {}}')
    dataset = tmp_path / "dataset.yaml"
    dataset.write_text("entries: []\n")

    code = main(["grade", "pin", "--dataset", str(dataset), "--roster", str(person)])

    captured = capsys.readouterr().err
    assert code != 0
    assert "carries no 'entities' key" in captured
    assert "Traceback" not in captured
