"""The annotator reads --roster with json.loads, so the projection must be JSON."""

from __future__ import annotations

import json
from pathlib import Path

from evalkit import roster

PERSON = {
    "role_order": ["sysadmin", "tpm"],
    "boundaries": {"modify-live-backend": {"owner": "sysadmin"}},
    "roles": {
        "sysadmin": {
            "display_name": "Systems Administrator",
            "purpose": "Operate the real hosted systems.",
            "boundaries": ["suggest-external-comms"],
            "personalities": ["protective", "grounded"],
            "scoped_boundaries": [{"name": "build-foundational-software", "scope": "own estate"}],
            "adjacents": [{"role": "platform", "reason": "implementing the fix itself"}],
        },
        "tpm": {"display_name": "Portfolio Director", "purpose": "Decide what is next."},
    },
}


def test_projection_carries_what_the_annotator_renders() -> None:
    projected = roster.to_entity_roster(PERSON)
    assert projected["entity_order"] == ["sysadmin", "tpm"]
    spec = projected["entities"]["sysadmin"]
    assert spec["display_name"] == "Systems Administrator"
    assert spec["purpose"]
    joined = " ".join(spec["notes"])
    assert "owns: modify-live-backend" in joined
    assert "scoped build-foundational-software: own estate" in joined
    assert "defers: suggest-external-comms" in joined
    assert "traits: protective, grounded" in joined
    assert "adjacent platform: implementing the fix itself" in joined


def test_written_file_parses_as_json(tmp_path: Path) -> None:
    person = tmp_path / "person.json"
    person.write_text(json.dumps(PERSON))
    out = tmp_path / "entities.json"
    assert roster.main(["--person", str(person), "--out", str(out)]) == 0
    reloaded = json.loads(out.read_text())
    assert reloaded == roster.to_entity_roster(PERSON)
