"""person.json must carry voice, because the board's voice tier reads it there.

The tier was registered in the profile, coded in `evalkit.matrix`, and wired
into `derive`, and it still produced nothing: `snapshot.py` emitted every field
evalkit read except this one, so `spec.get("voice")` was None for all seven
seats and every voice case was skipped before it was built. Nothing failed. The
board just reported 91 cases instead of 105, and a tier that derives zero looks
exactly like a tier that does not exist.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from housecast import roster, snapshot
from housecast.roster import Roster


@pytest.fixture(scope="module")
def shipped() -> Roster:
    return roster.load()


@pytest.fixture(scope="module")
def emitted(shipped: Roster) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(snapshot.dumps(shipped))
    return payload


def test_every_role_emits_its_voice(emitted: dict[str, Any], shipped: Roster) -> None:
    for name in shipped.role_order:
        assert emitted["roles"][name].get("voice"), f"{name} lost its voice in the snapshot"


def test_every_personality_emits_its_voice(emitted: dict[str, Any], shipped: Roster) -> None:
    for name, personality in shipped.personalities.items():
        if personality.voice is None:
            continue
        assert emitted["personalities"][name].get("voice"), f"{name} lost its voice"


def test_the_banks_survive_the_round_trip(emitted: dict[str, Any], shipped: Roster) -> None:
    """A bank flattened to [] would derive a diction case with an empty rule."""
    science = shipped.roles["science"].voice
    assert science is not None
    carried = emitted["roles"]["science"]["voice"]
    assert carried["prefer"] == list(science.prefer)
    assert carried["avoid"] == list(science.avoid)
    assert carried["tell"] == science.tell
    assert carried["person"] == science.person


def test_empty_fields_are_dropped_rather_than_emitted_empty(shipped: Roster) -> None:
    """An absent bank must be absent, so nothing derives a case with no rule."""
    bare = snapshot._voice(roster.Voice(summary="only a summary"))
    assert bare == {"summary": "only a summary"}


def test_acts_stay_out_until_something_reads_them(emitted: dict[str, Any]) -> None:
    """`snapshot.py` emits what evalkit reads. Nothing reads acts yet."""
    assert "acts" not in emitted["roles"]["science"]
