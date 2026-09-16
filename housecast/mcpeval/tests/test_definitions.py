"""The editable unit: identity by prose, an overlay that never touches the subject."""

from __future__ import annotations

import pytest

from housecast.mcpeval.definitions import DefinitionError, DefinitionSet, ToolProse, baseline_from

ADVERTISED = [
    {
        "name": "alpha",
        "description": "does alpha",
        "inputSchema": {
            "type": "object",
            "properties": {"x": {"type": "string", "description": "the x"}},
        },
    },
    {
        "name": "beta",
        "description": "does beta",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def base() -> DefinitionSet:
    return baseline_from(ADVERTISED, authored_by="human:test")


def test_baseline_is_taken_from_the_live_list_rather_than_written_beside_it() -> None:
    defs = base()
    assert defs.tools["alpha"].description == "does alpha"
    assert defs.tools["alpha"].parameters == {"x": "the x"}
    assert defs.parent is None


def test_overlay_does_not_mutate_what_tools_list_returned() -> None:
    """The prose edit never reaches the running subject. This is the whole architecture."""
    defs = base().edited(tool="alpha", description="clearer", authored_by="human:test")
    before = [dict(tool) for tool in ADVERTISED]
    out = defs.overlay(ADVERTISED)
    assert out[0]["description"] == "clearer"
    assert before == ADVERTISED, "overlay mutated the advertised list"
    assert ADVERTISED[0]["description"] == "does alpha"


def test_overlay_preserves_presentation_order() -> None:
    """Selection depends on what else was on offer and where."""
    out = base().overlay(ADVERTISED)
    assert [tool["name"] for tool in out] == ["alpha", "beta"]


def test_a_set_is_identified_by_its_prose_so_a_revert_collides_with_its_origin() -> None:
    start = base()
    changed = start.edited(tool="alpha", description="clearer", authored_by="human:test")
    reverted = changed.edited(tool="alpha", description="does alpha", authored_by="human:test")
    assert changed.digest != start.digest
    assert reverted.digest == start.digest, "a revert must not arrive as a third version"


def test_an_unattributable_author_is_refused() -> None:
    with pytest.raises(DefinitionError):
        DefinitionSet(tools={}, authored_by="evie")


def test_naming_a_tool_the_subject_does_not_advertise_is_refused() -> None:
    defs = DefinitionSet(tools={"gamma": ToolProse("x")}, authored_by="human:test")
    with pytest.raises(DefinitionError, match="does not advertise"):
        defs.overlay(ADVERTISED)


def test_naming_a_parameter_the_tool_does_not_take_is_refused() -> None:
    defs = DefinitionSet(tools={"alpha": ToolProse("x", {"nope": "y"})}, authored_by="human:test")
    with pytest.raises(DefinitionError, match="no parameter"):
        defs.overlay(ADVERTISED)


def test_validation_warns_rather_than_refuses() -> None:
    """A tester may be measuring exactly the defect the warning names."""
    defs = DefinitionSet(tools={"alpha": ToolProse("x" * 700)}, authored_by="human:test")
    notes = defs.validate()
    assert notes and "600" in notes[0]


def test_diff_names_the_field_that_moved() -> None:
    start = base()
    changed = start.edited(tool="alpha", description="clearer", authored_by="human:test")
    rows = start.diff(changed)
    assert rows == [
        {"tool": "alpha", "field": "description", "before": "does alpha", "after": "clearer"}
    ]
