"""The roster language: what YAML housecast reads, and what it refuses.

Ported from internal/person. The Go side parses KDL and this parses YAML, so
the loaders differ on purpose; what must not differ is the semantics either one
applies once the file is in memory.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any

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
class Voice:
    """Register. Role authors the baseline, personalities modulate it."""

    summary: str
    cadence: str = ""
    person: str = ""
    tell: str = ""
    prefer: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Outro:
    """What a session says as it closes. Role only, and not melded.

    Voice melds because it is read once as doctrine. An outro is read in half a
    second by somebody already leaving, and role plus two personalities runs to
    three sentences, which is a paragraph rather than a banner.
    """

    clean: str = ""
    failure: str = ""


@dataclass(frozen=True)
class Act:
    """One thing an attribute requires a seat to actually run.

    `tool` is carried separately from `text` so the coverage check is exact
    rather than a grep over prose. `side` is set on boundary acts only, because
    owning, scoping, and deferring are three different acts.
    """

    tool: str
    text: str
    side: str = ""


@dataclass(frozen=True)
class Personality:
    name: str
    skill: str
    color: str
    motif: str
    emblem: Emblem
    body: str
    voice: Voice | None = None
    acts: list[Act] = field(default_factory=list)


@dataclass(frozen=True)
class Boundary:
    name: str
    skill: str
    owner: str
    summary: str
    body: str
    acts: list[Act] = field(default_factory=list)

    def acts_for_side(self, side: str) -> list[Act]:
        """A deferred boundary is a different act, never the owner's withheld."""
        return [act for act in self.acts if act.side == side]


@dataclass(frozen=True)
class Seat:
    key: str
    harness: str
    tier: str | None = None
    channel: str | None = None
    # The seat's own product name, authored rather than derived. Absent stays
    # absent: identity describes and grants nothing (agent-compose#396).
    legal_name: str | None = None


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
    methods: list[str] = field(default_factory=list)
    favorite_color: str = ""
    # Per-role rather than per-meld (agent-compose#396): a meld is not a unique
    # key, since two roles sharing one fail the favorite-colour floor.
    creature: str = ""
    # Selects the animal clade a seat is drawn from, never its colour. Kai's
    # assignment, mirrored by the renderer (agentic-os-xxx#60).
    element: str = ""
    outro: Outro | None = None
    voice: Voice | None = None
    acts: list[Act] = field(default_factory=list)

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


def _voice(spec: dict[str, Any] | None) -> Voice | None:
    if not spec:
        return None
    return Voice(
        summary=str(spec["summary"]),
        cadence=str(spec.get("cadence", "")),
        person=str(spec.get("person", "")),
        tell=str(spec.get("tell", "")),
        prefer=[str(x) for x in spec.get("prefer", []) or []],
        avoid=[str(x) for x in spec.get("avoid", []) or []],
    )


def _acts(spec: list[dict[str, Any]] | None) -> list[Act]:
    return [
        Act(tool=str(a["tool"]), text=str(a["text"]), side=str(a.get("side", "")))
        for a in spec or []
    ]


def _outro(spec: dict[str, Any] | None) -> Outro | None:
    if not spec:
        return None
    return Outro(clean=str(spec.get("clean", "")), failure=str(spec.get("failure", "")))


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
            acts=_acts(spec.get("acts")),
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
            voice=_voice(spec.get("voice")),
            acts=_acts(spec.get("acts")),
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
            voice=_voice(spec.get("voice")),
            supported_model_tiers=list(spec["supported_model_tiers"]),
            defers=list(spec["defers"]),
            scoped=[Scoped(s["name"], s["scope"]) for s in spec.get("scoped") or []],
            personalities=list(spec["personalities"]),
            identity_name=spec["identity"]["name"],
            identity_pronouns=spec["identity"]["pronouns"],
            seats=[
                Seat(s["key"], s["harness"], s.get("tier"), s.get("channel"), s.get("legal_name"))
                for s in spec["seats"]
            ],
            adjacents=[Adjacent(a["role"], a["reason"]) for a in spec.get("adjacents") or []],
            body=spec["body"],
            methods=list(spec.get("methods") or []),
            creature=str(spec.get("creature", "")),
            element=str(spec.get("element", "")),
            outro=_outro(spec.get("outro")),
            acts=_acts(spec.get("acts")),
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
    rules.check_creature_names(roster)
    rules.check_skill_frontmatter(roster)
    rules.check_copy_contract(roster)
