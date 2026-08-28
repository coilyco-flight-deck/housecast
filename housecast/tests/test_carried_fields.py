"""Fields the #333 port dropped silently, and the round trip that proves they stay.

Role methods and seat channels are the sharpest of the gaps in agent-compose#373
precisely because no shipped role or seat carries either. Nothing renders
differently today, so the parity suite against Go cannot see the loss, and a
roster that added one would lose it with no error. These tests carry the fixture
the shipped roster does not.
"""

from __future__ import annotations

import pytest
import yaml

from housecast import render, roster
from housecast.roster import Roster

METHODS = ["adversarial-verification", "state-machine-verification"]
CHANNEL = "sirens-deep"


@pytest.fixture(scope="module")
def carrying(tmp_path_factory: pytest.TempPathFactory) -> Roster:
    """The shipped roster with methods and a channel injected onto one role."""
    doc = yaml.safe_load(roster.DATA.read_bytes())
    role = doc["roles"]["eval"]
    role["methods"] = list(METHODS)
    role["seats"][0]["channel"] = CHANNEL
    path = tmp_path_factory.mktemp("roster") / "roster.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return roster.load(path)


def test_role_methods_survive_the_loader(carrying: Roster) -> None:
    assert carrying.roles["eval"].methods == METHODS


def test_seat_channel_survives_the_loader(carrying: Roster) -> None:
    assert carrying.roles["eval"].seats[0].channel == CHANNEL


def test_the_identity_card_renders_role_methods(carrying: Roster) -> None:
    """Go emits this line between the role skill and the boundaries."""
    card = render.identity_card(carrying, "eval")
    assert "**Role methods // `adversarial-verification` // `state-machine-verification`**" in card
    skill_at = card.index("**Role skill //")
    methods_at = card.index("**Role methods //")
    assert skill_at < methods_at
    if "**Boundaries //" in card:
        assert methods_at < card.index("**Boundaries //")


# Negative control. Without the fields the card must not grow the line, or the
# test above passes on a renderer that emits it unconditionally.
def test_the_shipped_roster_renders_no_methods_line() -> None:
    loaded = roster.load()
    assert loaded.roles["eval"].methods == []
    assert loaded.roles["eval"].seats[0].channel is None
    assert "**Role methods //" not in render.identity_card(loaded, "eval")
