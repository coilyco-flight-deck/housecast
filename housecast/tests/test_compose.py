"""Self-contained compose tests, with no Go engine in reach.

The differential oracle against Go lives in agent-compose, which is the only
place both engines exist. These are the checks that must keep working after
agent-compose#339 deletes it, so they assert shape and internal consistency
rather than bytes against a reference.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from housecast import compose, roster, snapshot
from housecast.roster import Roster


@pytest.fixture(scope="module")
def loaded() -> Roster:
    return roster.load()


def _cases() -> list[tuple[str, str]]:
    loaded_roster = roster.load()
    return [
        (name, tier)
        for name in loaded_roster.role_order
        for tier in loaded_roster.roles[name].supported_model_tiers
    ]


@pytest.mark.parametrize(("role", "tier"), _cases())
def test_native_bundle_is_internally_consistent(
    loaded: Roster,
    tmp_path: pathlib.Path,
    role: str,
    tier: str,
) -> None:
    out = compose.compose(loaded, role, tier, tmp_path / "bundle")
    manifest = json.loads((out / "manifest.json").read_text())
    trace = json.loads((out / "trace.json").read_text())

    assert manifest["model_tier"] == tier
    assert manifest["role_skill"] == f"role-{role}"
    selected = [
        d["subject"].removeprefix("skill:")
        for d in trace["decisions"]
        if d["kind"] == "skill" and d["outcome"] == "selected"
    ]
    on_disk = sorted(p.parent.name for p in out.rglob("SKILL.md"))
    assert sorted(selected) == on_disk

    provider = trace["providers"][0]
    assert provider["skills"] == len(selected)
    measured = sum(p.stat().st_size for p in out.rglob("SKILL.md"))
    assert provider["context_bytes"] == measured
    assert provider["approximate_tokens"] == (measured + 3) // 4
    assert manifest["delivery"]["body_bytes"] == len(
        (out / "content" / "instructions.md").read_bytes()
    )


@pytest.mark.parametrize("role", roster.load().role_order)
def test_compiled_bundle_carries_every_body(
    loaded: Roster,
    tmp_path: pathlib.Path,
    role: str,
) -> None:
    out = compose.compose(loaded, role, "frontier", tmp_path / "bundle", "compiled")
    document = (out / "delivery" / "compiled.md").read_text()
    assert document.startswith((out / "content" / "instructions.md").read_text())
    for body in out.rglob("SKILL.md"):
        assert body.read_text() in document


def test_every_role_owns_exactly_one_boundary(loaded: Roster) -> None:
    """The allocation rule the whole roster language rests on."""
    for name in loaded.role_order:
        owned = [b for b, spec in loaded.boundaries.items() if spec.owner == name]
        assert len(owned) <= 1, f"{name} owns {owned}"
    owners = {spec.owner for spec in loaded.boundaries.values()}
    assert owners <= set(loaded.roles)


def test_snapshot_round_trips_through_json(loaded: Roster) -> None:
    text = snapshot.dumps(loaded)
    parsed = json.loads(text)
    assert parsed["role_order"] == loaded.role_order
    assert set(parsed["roles"]) == set(loaded.roles)
    for name in loaded.role_order:
        assert parsed["roles"][name]["favorite_color"] == loaded.roles[name].favorite_color


def test_favorite_colors_are_distinct(loaded: Roster) -> None:
    colors = [loaded.roles[n].favorite_color for n in loaded.role_order]
    assert len(set(colors)) == len(colors)
