"""Every role names a creature, and no two name the same one.

The creature is one of the four parts a seat states as its identity, alongside
preferred name, role, and legal name. Two seats answering with the same creature
makes that sentence stop identifying anybody, which is why uniqueness is checked
rather than assumed.

Nothing renders it yet. agent-compose#396 item 4 is the prose rendering, and it
is held behind the parity pin: the Go engine composes the same identity card from
its own KDL, so a new card line has to move in both engines at once.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest
import yaml

from housecast import render, roster
from housecast.roster import Roster

# `validate` defines its own RosterError, distinct from `roster`'s. The checks
# dispatched from `roster.validate` raise that one, so a test catching the other
# passes on the raise and fails on the class.
from housecast.validate import RosterError


@pytest.fixture(scope="module")
def shipped() -> Roster:
    return roster.load()


def rewritten(tmp_path: pathlib.Path, mutate: Any) -> pathlib.Path:
    doc = yaml.safe_load(roster.DATA.read_bytes())
    mutate(doc)
    path = tmp_path / "roster.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return path


def test_every_role_names_a_creature(shipped: Roster) -> None:
    for name in shipped.role_order:
        assert shipped.roles[name].creature, f"{name} has no creature"


def test_the_seven_are_unique(shipped: Roster) -> None:
    creatures = [shipped.roles[n].creature for n in shipped.role_order]
    assert len(set(creatures)) == len(creatures)


def test_a_missing_creature_is_refused(tmp_path: pathlib.Path) -> None:
    def drop(doc: dict[str, Any]) -> None:
        del doc["roles"]["science"]["creature"]

    with pytest.raises(RosterError, match="has no creature"):
        roster.load(rewritten(tmp_path, drop))


def test_a_duplicate_creature_is_refused(tmp_path: pathlib.Path) -> None:
    def collide(doc: dict[str, Any]) -> None:
        doc["roles"]["science"]["creature"] = doc["roles"]["platform"]["creature"]

    with pytest.raises(RosterError, match="is on both"):
        roster.load(rewritten(tmp_path, collide))


def test_the_card_does_not_render_it_yet(shipped: Roster) -> None:
    """Held behind the parity pin, deliberately. When this starts failing the
    Go engine and the pin have to move in the same change."""
    card = render.identity_card(shipped, "science")
    assert shipped.roles["science"].creature not in card
