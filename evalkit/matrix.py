"""Derive the unwritten challenges the roster implies.

The board is a consequence of the roster, not a hand-maintained list. Adding a
boundary or changing adjacency changes this output. A human writes the prompt
into each one. See docs/evaluation.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from aos_eval.schema import AGENT_COMPOSE, Challenge, Half

# The taxonomy is the profile's, not this module's. Unpacking by arity means
# a fourth test type fails loudly here rather than being silently unranked.
BOUNDARY, ROLE_FIT, PERSONALITY = (spec.name for spec in AGENT_COMPOSE.test_types)


def abbreviate(slug: str) -> str:
    return "".join(part[0] for part in slug.split("-"))


def boundary_challenges(roster: dict[str, Any]) -> list[Challenge]:
    challenges: list[Challenge] = []
    order = [name for name in AGENT_COMPOSE.attribute_order if name in roster.get("boundaries", {})]
    order += [name for name in roster.get("boundary_order", []) if name not in order]

    for boundary in order:
        spec = roster["boundaries"][boundary]
        owner = str(spec.get("owner", ""))
        deferring = [
            role
            for role in roster["role_order"]
            if boundary in roster["roles"][role].get("boundaries", [])
        ]
        scoped = scoped_grants(roster, boundary)
        short = abbreviate(boundary)
        behaviour = owner_behaviour(str(spec.get("summary", "")), owner, roster)
        for role in [*deferring, *scoped, owner]:
            if not role:
                continue
            purpose = _shorten(str(roster["roles"][role].get("purpose", "")))
            scope = scoped.get(role)
            for half in (Half.IN, Half.OUT):
                challenges.append(
                    Challenge(
                        id=f"{role}-{short}-{half.value}",
                        entity=role,
                        test_type=BOUNDARY,
                        attribute=boundary,
                        half=half,
                        pair_id=f"{role}-{short}",
                        target=_boundary_target(
                            role == owner, half, owner, behaviour, purpose, scope
                        ),
                    )
                )
    return challenges


def scoped_grants(roster: dict[str, Any], boundary: str) -> dict[str, str]:
    """Roles holding one boundary within a scope, in roster order.

    The grant is a third state rather than a weaker defer, so a scoped role
    appears in neither `boundaries` nor the owner slot and would derive as
    nothing without this. See docs/role-boundaries.md.
    """
    grants: dict[str, str] = {}
    for role in roster["role_order"]:
        for entry in roster["roles"][role].get("scoped_boundaries", []) or []:
            if str(entry.get("name", "")) == boundary:
                grants[role] = str(entry.get("scope", ""))
    return grants


def owner_behaviour(summary: str, owner: str, roster: dict[str, Any]) -> str:
    """The owner's clause of a summary reading '<Owner> <does X>, other roles ...'.

    Quoted verbatim downstream. The clause is conjugated for the owner's name, so
    negating it in prose would need inflection this renderer has no business doing.
    """
    head = summary.split(",", 1)[0].strip()
    display = str(roster["roles"].get(owner, {}).get("display_name", "")).strip()
    if display and head.lower().startswith(display.lower()):
        head = head[len(display) :].strip()
    return head or summary.strip()


def role_fit_challenges(roster: dict[str, Any]) -> list[Challenge]:
    challenges: list[Challenge] = []
    for role in roster["role_order"]:
        challenges.append(
            Challenge(
                id=f"{role}-fit-within",
                entity=role,
                test_type=ROLE_FIT,
                attribute="within",
                target=f"{role} correctly identifies work it should own",
            )
        )
        for adjacent in roster["roles"][role].get("adjacents", []):
            challenges.append(
                Challenge(
                    id=f"{role}-fit-{adjacent['role']}",
                    entity=role,
                    test_type=ROLE_FIT,
                    attribute=str(adjacent["role"]),
                    target=str(adjacent["reason"]),
                )
            )
    return challenges


def personality_challenges(roster: dict[str, Any]) -> list[Challenge]:
    """One challenge per trait, each run against the fully composed bundle."""
    challenges: list[Challenge] = []
    for role in roster["role_order"]:
        traits = list(roster["roles"][role]["personalities"])
        for trait in traits:
            peers = ", ".join(other for other in traits if other != trait)
            challenges.append(
                Challenge(
                    id=f"{role}-per-{trait}",
                    entity=role,
                    test_type=PERSONALITY,
                    attribute=trait,
                    target=f"{trait}, composed alongside {peers}" if peers else trait,
                )
            )
    return challenges


def derive(roster: dict[str, Any], group: str = "tier") -> list[Challenge]:
    derived = (
        boundary_challenges(roster) + role_fit_challenges(roster) + personality_challenges(roster)
    )
    if group != "role":
        return derived
    order = list(roster["role_order"])
    return sorted(derived, key=lambda c: (order.index(c.entity), AGENT_COMPOSE.rank(c.test_type)))


def render(challenges: list[Challenge]) -> str:
    lines: list[str] = []
    for index, challenge in enumerate(challenges, start=1):
        lines.append(f"{index:3d}. {challenge.id:<26} {challenge.entity:<9} {challenge.target}")

    tiers: dict[str, int] = {}
    per_role: dict[str, int] = {}
    for challenge in challenges:
        tiers[challenge.test_type] = tiers.get(challenge.test_type, 0) + 1
        per_role[challenge.entity] = per_role.get(challenge.entity, 0) + 1

    lines.append("")
    counts = ", ".join(f"{v} {k}" for k, v in tiers.items())
    lines.append(f"{len(challenges)} challenges: {counts}")
    lines.append("per role: " + ", ".join(f"{k} {v}" for k, v in sorted(per_role.items())))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the challenges the roster implies.")
    parser.add_argument("--roster", type=Path, required=True, help="person.json from the roster")
    parser.add_argument("--format", choices=("text", "yaml"), default="text")
    parser.add_argument("--group", choices=("role", "tier"), default="role")
    args = parser.parse_args(argv)

    derived = derive(json.loads(args.roster.read_text()), args.group)
    if args.format == "yaml":
        payload = [c.model_dump(mode="json", exclude_none=True) for c in derived]
        print(yaml.safe_dump({"challenges": payload}, sort_keys=False, width=100))
    else:
        print(render(derived))
    return 0


def _boundary_target(
    is_owner: bool, half: Half, owner: str, behaviour: str, purpose: str, scope: str | None = None
) -> str:
    if is_owner and half is Half.IN:
        return f'owns "{behaviour}"'
    if is_owner:
        return f'owns "{behaviour}", claims nothing past it'
    # A scoped grant keeps the in-half meaning it holds everywhere here, the
    # role acting on its own territory. The territory is the grant's limit.
    if scope:
        if half is Half.IN:
            return f'holds "{behaviour}" within: {scope}'
        return f'defers "{behaviour}" past that scope to {owner}'
    if half is Half.IN:
        return f"owns: {purpose}"
    return f'defers "{behaviour}" to {owner}'


def _shorten(purpose: str) -> str:
    text = purpose.strip().rstrip(".")
    return text[:1].lower() + text[1:] if text else text


if __name__ == "__main__":
    raise SystemExit(main())
