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

from housecast import roster
from housecast.roster import Roster

METHODS = ["adversarial-verification", "state-machine-verification"]
CHANNEL = "sirens-deep"


@pytest.fixture(scope="module")
def carrying(tmp_path_factory: pytest.TempPathFactory) -> Roster:
    """The shipped roster with methods and a channel injected onto one role."""
    doc = yaml.safe_load(roster.DATA.read_bytes())
    role = doc["roles"]["science"]
    role["methods"] = list(METHODS)
    role["seats"][0]["channel"] = CHANNEL
    path = tmp_path_factory.mktemp("roster") / "roster.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return roster.load(path)


def test_role_methods_survive_the_loader(carrying: Roster) -> None:
    assert carrying.roles["science"].methods == METHODS


def test_seat_channel_survives_the_loader(carrying: Roster) -> None:
    assert carrying.roles["science"].seats[0].channel == CHANNEL


@pytest.fixture(scope="module")
def archived(tmp_path_factory: pytest.TempPathFactory) -> Roster:
    """The shipped roster with one role archived.

    These three tests used to read the flag off whichever shipped role happened
    to carry it, which was analyst and only analyst. Un-archiving that role
    deleted the coverage rather than failing it, so the fixture makes its own
    archived role the way the rest of this file makes its own methods and
    channel.

    It archives platform rather than analyst for the same reason, from the other
    direction. Analyst, psych and reporter were archived on 2026-09-15, which
    left the live half of these assertions with no subject. Platform is the seat
    least likely to retire, so the pair stays testable whichever way the roster
    moves.
    """
    doc = yaml.safe_load(roster.DATA.read_bytes())
    doc["roles"]["platform"]["archived"] = True
    path = tmp_path_factory.mktemp("archived") / "roster.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return roster.load(path)


def test_archived_defaults_false_and_survives_the_loader(archived: Roster) -> None:
    """Absent means live, so every roster authored before the field still loads."""
    assert roster.load().roles["platform"].archived is False
    assert archived.roles["platform"].archived is True


def test_the_projection_carries_archived(archived: Roster) -> None:
    """evalkit reads person.json rather than the YAML, so the flag has to cross."""
    from housecast import snapshot

    assert snapshot.person_snapshot(archived)["roles"]["platform"]["archived"] is True
    assert snapshot.person_snapshot(roster.load())["roles"]["platform"]["archived"] is False
