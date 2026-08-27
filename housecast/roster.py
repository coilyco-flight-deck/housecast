"""The roster language: what YAML housecast reads, and what it refuses.

Ported from internal/person. The Go side parses KDL and this parses YAML, so
the loaders differ on purpose; what must not differ is the semantics either one
applies once the file is in memory.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

import yaml

from housecast import color

DATA = pathlib.Path(__file__).parent / "data" / "roster.yaml"


class RosterError(ValueError):
    """The roster is malformed, or a role asks for something incoherent."""


@dataclass(frozen=True)
class Emblem:
    names: list[str]
    emoji: str


@dataclass(frozen=True)
class Personality:
    name: str
    skill: str
    color: str
    motif: str
    emblem: Emblem
    body: str


@dataclass(frozen=True)
class Boundary:
    name: str
    skill: str
    owner: str
    summary: str
    body: str


@dataclass(frozen=True)
class Seat:
    key: str
    harness: str
    tier: str | None = None


@dataclass(frozen=True)
class Scoped:
    name: str
    scope: str


@dataclass(frozen=True)
class Adjacent:
    """The role most easily confused with this one, and why. evalkit reads it."""

    role: str
    reason: str


@dataclass
class Role:
    name: str
    display_name: str
    purpose: str
    skill: str
    skill_source: str
    stance: str
    supported_model_tiers: list[str]
    defers: list[str]
    scoped: list[Scoped]
    personalities: list[str]
    identity_name: str
    identity_pronouns: str
    seats: list[Seat]
    adjacents: list[Adjacent]
    body: str
    favorite_color: str = ""

    def active_boundaries(self, boundaries: dict[str, Boundary]) -> list[str]:
        """Deferred, then scoped, then the single boundary this role owns."""
        active = list(self.defers)
        active += [entry.name for entry in self.scoped]
        active += [name for name, b in boundaries.items() if b.owner == self.name]
        return active


@dataclass
class Roster:
    person: str
    source: str
    invariant: str
    boundary_order: list[str]
    boundaries: dict[str, Boundary]
    personalities: dict[str, Personality]
    role_order: list[str]
    roles: dict[str, Role]
    raw: bytes = field(default=b"", repr=False)

    def resolve_favorite_colors(self) -> None:
        """Derive every role's favorite together, in role order."""
        groups = []
        for name in self.role_order:
            role = self.roles[name]
            components = []
            for personality in role.personalities:
                if personality not in self.personalities:
                    raise RosterError(
                        f"role {name!r}: personality {personality!r} has no catalog binding"
                    )
                components.append(self.personalities[personality].color)
            if not components:
                raise RosterError(f"role {name!r} has no personalities to derive a favorite from")
            groups.append(components)
        try:
            derived = color.favorites(groups)
        except color.ColorError as exc:
            raise RosterError(f"derive role favorite colors: {exc}") from exc
        for name, value in zip(self.role_order, derived, strict=True):
            self.roles[name].favorite_color = value


def load(path: pathlib.Path | str = DATA) -> Roster:
    path = pathlib.Path(path)
    raw = path.read_bytes()
    doc = yaml.safe_load(raw)

    boundaries = {
        name: Boundary(
            name=name,
            skill=spec["skill"],
            owner=spec["owner"],
            summary=spec["summary"],
            body=spec["body"],
        )
        for name, spec in doc["boundaries"].items()
    }
    personalities = {
        name: Personality(
            name=name,
            skill=spec["skill"],
            color=spec["color"],
            motif=spec["motif"],
            emblem=Emblem(spec["emblem"]["names"], spec["emblem"]["emoji"]),
            body=spec["body"],
        )
        for name, spec in doc["personalities"].items()
    }
    roles = {}
    for name, spec in doc["roles"].items():
        roles[name] = Role(
            name=name,
            display_name=spec["display_name"],
            purpose=spec["purpose"],
            skill=spec["skill"],
            skill_source=spec["skill_source"],
            stance=spec["stance"],
            supported_model_tiers=list(spec["supported_model_tiers"]),
            defers=list(spec["defers"]),
            scoped=[Scoped(s["name"], s["scope"]) for s in spec.get("scoped") or []],
            personalities=list(spec["personalities"]),
            identity_name=spec["identity"]["name"],
            identity_pronouns=spec["identity"]["pronouns"],
            seats=[Seat(s["key"], s["harness"], s.get("tier")) for s in spec["seats"]],
            adjacents=[Adjacent(a["role"], a["reason"]) for a in spec.get("adjacents") or []],
            body=spec["body"],
        )
    roster = Roster(
        person=doc["person"],
        source=doc["source"],
        invariant=doc["invariant"],
        boundary_order=list(doc["boundary_order"]),
        boundaries=boundaries,
        personalities=personalities,
        role_order=list(doc["role_order"]),
        roles=roles,
        raw=raw,
    )
    validate(roster)
    roster.resolve_favorite_colors()
    return roster


def validate(roster: Roster) -> None:
    """Every rule the Go loader applies, in the order it applies them."""
    from housecast import validate as rules

    rules.check_boundary_ownership(roster)
    rules.check_personality_bindings(roster)
    rules.check_definition_set(roster)
    rules.check_personality_colors(roster)
    rules.check_skill_frontmatter(roster)
    rules.check_copy_contract(roster)
