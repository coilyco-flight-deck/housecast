"""Roster validation ported from internal/person.

The Go tests are the specification, so the messages here quote theirs closely
enough that a reader can find the Go check from a Python failure. Word and
paragraph counting reproduce roleSkillBodyWordCount and briefingParagraphCount
exactly, including dropping a leading `# ` heading before counting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from housecast import color

if TYPE_CHECKING:
    from housecast.roster import Roster

MIN_ROLE_BODY_WORDS = 140
MAX_ROLE_BODY_WORDS = 400
MIN_PERSONALITY_BODY_WORDS = 120
MAX_PERSONALITY_BODY_WORDS = 320
MIN_ROLE_PARAGRAPHS = 3

BOUNDARY_OWN_HEADING = "## If you own this boundary"
BOUNDARY_DEFER_HEADING = "## If you defer this boundary"
BOUNDARY_SCOPED_HEADING = "## If you hold this boundary within a scope"


def word_count(body: str) -> int:
    content = body.replace("\r\n", "\n").strip()
    first, _, remainder = content.partition("\n")
    if remainder and first.strip().startswith("# "):
        content = remainder
    return len(content.split())


def paragraph_count(body: str) -> int:
    normalized = body.replace("\r\n", "\n")
    return sum(1 for para in normalized.split("\n\n") if para.strip())


def split_frontmatter(raw: str, skill: str) -> tuple[str, str]:
    text = raw.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise _error(f"person skill {skill!r}: SKILL.md needs YAML frontmatter")
    end = text[4:].find("\n---\n")
    if end < 0:
        raise _error(f"person skill {skill!r}: SKILL.md has unterminated frontmatter")
    return text[4 : 4 + end], text[4 + end + 5 :]


def description(raw: str, skill: str) -> str:
    """The first sentence of the frontmatter description, as the card renders it."""
    frontmatter, _ = split_frontmatter(raw, skill)
    for line in frontmatter.split("\n"):
        if line.startswith("description: "):
            value = line[len("description: ") :]
            sentence, sep, _ = value.partition(". ")
            return sentence + "." if sep else value.strip()
    raise _error(f"person skill {skill!r}: missing description")


class RosterError(ValueError):
    pass


def _error(message: str) -> RosterError:
    return RosterError(message)


def check_boundary_ownership(roster: Roster) -> None:
    """An owner receives the body by owning it, never by declaring it."""
    for name in roster.boundary_order:
        boundary = roster.boundaries[name]
        if not boundary.owner:
            raise _error(f"boundary {name!r} has no owner")
        role = roster.roles.get(boundary.owner)
        if role is None:
            raise _error(f"boundary {name!r} names unknown owner {boundary.owner!r}")
        if name in role.defers:
            raise _error(f"boundary {name!r} owner {boundary.owner!r} also declares it")
        if any(entry.name == name for entry in role.scoped):
            raise _error(f"boundary {name!r} owner {boundary.owner!r} also scopes it")


def check_personality_bindings(roster: Roster) -> None:
    for role_name in roster.role_order:
        role = roster.roles[role_name]
        if not role.personalities:
            raise _error(f"role {role_name!r} activates no personalities")
        for personality in role.personalities:
            if personality not in roster.personalities:
                raise _error(
                    f"role {role_name!r}: personality {personality!r} has no catalog binding"
                )


def check_definition_set(roster: Roster) -> None:
    """Every declared name resolves, and every definition is reachable."""
    if set(roster.boundary_order) != set(roster.boundaries):
        raise _error("boundary_order and the boundary definitions are a mismatched set")
    if set(roster.role_order) != set(roster.roles):
        raise _error("role_order and the role definitions are a mismatched set")
    bound = {p for role in roster.roles.values() for p in role.personalities}
    orphans = sorted(set(roster.personalities) - bound)
    if orphans:
        raise _error(f"personalities defined but bound to no role: {', '.join(orphans)}")
    for role_name in roster.role_order:
        for name in roster.roles[role_name].defers:
            if name not in roster.boundaries:
                raise _error(f"role {role_name!r} defers unknown boundary {name!r}")
        for entry in roster.roles[role_name].scoped:
            if entry.name not in roster.boundaries:
                raise _error(f"role {role_name!r} scopes unknown boundary {entry.name!r}")


def check_personality_colors(roster: Roster) -> None:
    for name in sorted(roster.personalities):
        try:
            color.legible(roster.personalities[name].color)
        except color.ColorError as exc:
            raise _error(f"personality {name!r} color: {exc}") from exc


def check_skill_frontmatter(roster: Roster) -> None:
    """Every skill body declares its own name in frontmatter."""
    entries = [(r.skill, r.body) for r in roster.roles.values()]
    entries += [(p.skill, p.body) for p in roster.personalities.values()]
    entries += [(b.skill, b.body) for b in roster.boundaries.values()]
    for skill, body in entries:
        frontmatter, _ = split_frontmatter(body, skill)
        if f"\nname: {skill}\n" not in "\n" + frontmatter + "\n":
            raise _error(f"person skill {skill!r}: frontmatter does not declare name {skill!r}")
        description(body, skill)


def check_copy_contract(roster: Roster) -> None:
    """Prose bounds: the role charter, the personality entries, both boundary sides."""
    for role_name in roster.role_order:
        role = roster.roles[role_name]
        _, body = split_frontmatter(role.body, role.skill)
        words = word_count(body)
        if words > MAX_ROLE_BODY_WORDS:
            raise _error(
                f"role {role_name!r} skill body has {words} words, maximum is {MAX_ROLE_BODY_WORDS}"
            )
        if words < MIN_ROLE_BODY_WORDS:
            raise _error(
                f"role {role_name!r} body has {words} words, minimum is {MIN_ROLE_BODY_WORDS}"
            )
        paragraphs = paragraph_count(body)
        if paragraphs < MIN_ROLE_PARAGRAPHS:
            raise _error(
                f"role {role_name!r} skill needs at least three paragraphs, got {paragraphs}"
            )
    for name in sorted(roster.personalities):
        personality = roster.personalities[name]
        _, body = split_frontmatter(personality.body, personality.skill)
        words = word_count(body)
        if words > MAX_PERSONALITY_BODY_WORDS:
            raise _error(
                f"personality {name!r} skill body has {words} words, "
                f"maximum is {MAX_PERSONALITY_BODY_WORDS}"
            )
    for name in roster.boundary_order:
        boundary = roster.boundaries[name]
        _, body = split_frontmatter(boundary.body, boundary.skill)
        own = body.find(BOUNDARY_OWN_HEADING)
        defer = body.find(BOUNDARY_DEFER_HEADING)
        if own < 0 or defer < 0:
            raise _error(
                f"boundary {name!r} skill body needs both "
                f"{BOUNDARY_OWN_HEADING!r} and {BOUNDARY_DEFER_HEADING!r} sections"
            )
        if own > defer:
            raise _error(f"boundary {name!r} skill body states the defer side before the own side")
