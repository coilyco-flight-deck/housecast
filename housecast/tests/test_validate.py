"""Negative controls for every rule agent-compose#333 names.

Each test mutates a roster that passes, so a rule that silently stopped firing
fails here instead of passing quietly. The positive baseline is asserted once,
which is what makes the mutations meaningful.
"""

from __future__ import annotations

import dataclasses
import pathlib

import pytest

from housecast import color, roster, validate
from housecast.roster import Roster


@pytest.fixture
def loaded() -> Roster:
    return roster.load()


def test_the_shipped_roster_passes(loaded: Roster) -> None:
    validate.check_boundary_ownership(loaded)
    validate.check_personality_bindings(loaded)
    validate.check_definition_set(loaded)
    validate.check_personality_colors(loaded)
    validate.check_grounding_lanes(loaded)
    validate.check_skill_frontmatter(loaded)
    validate.check_copy_contract(loaded)


def test_a_role_with_no_grounding_lane_is_rejected(loaded: Roster) -> None:
    """A missing lane derives no grounding pair, and coverage cannot see the hole."""
    loaded.roles["science"].grounding = ""
    with pytest.raises(roster.RosterError, match="has no grounding lane"):
        validate.check_grounding_lanes(loaded)


def test_owner_may_not_declare_the_boundary_it_owns(loaded: Roster) -> None:
    owned = "build-foundational-software"
    assert loaded.boundaries[owned].owner == "platform"
    loaded.roles["platform"].defers.append(owned)
    with pytest.raises(roster.RosterError, match="also declares it"):
        validate.check_boundary_ownership(loaded)


def test_owner_may_not_scope_the_boundary_it_owns(loaded: Roster) -> None:
    owned = "build-foundational-software"
    loaded.roles["platform"].scoped.append(roster.Scoped(owned, "anywhere at all"))
    with pytest.raises(roster.RosterError, match="also scopes it"):
        validate.check_boundary_ownership(loaded)


def test_missing_personality_binding_is_rejected(loaded: Roster) -> None:
    loaded.roles["director"].personalities.append("unbound")
    with pytest.raises(roster.RosterError, match="has no catalog binding"):
        validate.check_personality_bindings(loaded)


def test_a_role_with_no_personalities_is_rejected(loaded: Roster) -> None:
    loaded.roles["director"].personalities.clear()
    with pytest.raises(roster.RosterError, match="activates no personalities"):
        validate.check_personality_bindings(loaded)


def test_mismatched_definition_set_is_rejected(loaded: Roster) -> None:
    loaded.boundary_order.append("no-such-boundary")
    with pytest.raises(roster.RosterError, match="mismatched set"):
        validate.check_definition_set(loaded)


def test_a_role_deferring_an_unknown_boundary_is_rejected(loaded: Roster) -> None:
    loaded.roles["director"].defers.append("no-such-boundary")
    with pytest.raises(roster.RosterError, match="defers unknown boundary"):
        validate.check_definition_set(loaded)


def test_an_orphan_personality_is_rejected(loaded: Roster) -> None:
    orphan = dataclasses.replace(loaded.personalities["decisive"], name="orphan")
    loaded.personalities["orphan"] = orphan
    with pytest.raises(roster.RosterError, match="bound to no role"):
        validate.check_definition_set(loaded)


@pytest.mark.parametrize("bad", ["#ffffff", "#000000", "#a0a0a0"])
def test_out_of_band_personality_color_is_rejected(loaded: Roster, bad: str) -> None:
    loaded.personalities["decisive"] = dataclasses.replace(
        loaded.personalities["decisive"], color=bad
    )
    with pytest.raises(roster.RosterError):
        validate.check_personality_colors(loaded)


def test_out_of_band_colors_are_actually_out_of_band() -> None:
    """The parametrized colors above must fail `legible` for the stated reason.

    #a0a0a0 rather than #808080: mid gray lands at L 0.5983 and trips the
    lightness floor first, so it never exercises the chroma floor at all.
    """
    with pytest.raises(color.ColorError, match="lightness"):
        color.legible("#ffffff")
    with pytest.raises(color.ColorError, match="lightness"):
        color.legible("#000000")
    with pytest.raises(color.ColorError, match="too gray"):
        color.legible("#a0a0a0")
    color.legible("#5fa87a")


def test_an_overlong_role_body_is_rejected(loaded: Roster) -> None:
    role = loaded.roles["director"]
    frontmatter, body = validate.split_frontmatter(role.body, role.skill)
    role.body = f"---\n{frontmatter}\n---\n" + body + ("\n\nword" * 500)
    with pytest.raises(roster.RosterError, match="maximum is 1200"):
        validate.check_copy_contract(loaded)


def test_a_role_body_under_three_paragraphs_is_rejected(loaded: Roster) -> None:
    role = loaded.roles["director"]
    frontmatter, _ = validate.split_frontmatter(role.body, role.skill)
    role.body = f"---\n{frontmatter}\n---\n\n# Portfolio Director\n\n" + ("word " * 200)
    with pytest.raises(roster.RosterError, match="at least three paragraphs"):
        validate.check_copy_contract(loaded)


def test_a_skill_whose_frontmatter_names_another_skill_is_rejected(loaded: Roster) -> None:
    role = loaded.roles["director"]
    role.body = role.body.replace("name: role-director", "name: role-somebody-else", 1)
    with pytest.raises(roster.RosterError, match="does not declare name"):
        validate.check_skill_frontmatter(loaded)


def test_a_boundary_missing_a_side_is_rejected(loaded: Roster) -> None:
    boundary = loaded.boundaries["modify-live-backend"]
    loaded.boundaries["modify-live-backend"] = dataclasses.replace(
        boundary, body=boundary.body.replace(validate.BOUNDARY_DEFER_HEADING, "## Something else")
    )
    with pytest.raises(roster.RosterError, match="needs both"):
        validate.check_copy_contract(loaded)


def test_word_count_drops_a_leading_heading() -> None:
    assert validate.word_count("# Title\n\none two three") == 3
    assert validate.word_count("one two three") == 3


def test_paragraph_count_ignores_blank_runs() -> None:
    assert validate.paragraph_count("a\n\n\n\nb") == 2


def test_unsupported_model_tier_is_refused(loaded: Roster) -> None:
    from housecast import compose

    assert "oss" not in loaded.roles["director"].supported_model_tiers
    with pytest.raises(ValueError, match="does not support model tier"):
        compose.compose(loaded, "director", "oss", pathlib.Path("/tmp/zq49-unreachable"))
