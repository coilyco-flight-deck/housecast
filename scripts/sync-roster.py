#!/usr/bin/env python3
"""Sync data/roster.yaml's vendored bodies and acts from the roster source tree.

Scaffolding, not architecture. agent-compose/seed/roster/data is the author
surface, and until it is the only one roster.yaml is a vendored mirror that
drifts silently. checks/tests/test_source_drift.py in agent-compose is what
catches the drift; this is what closes it.

Reading the source is a real YAML parse. Writing roster.yaml stays textual on
purpose: it carries a hand-written header and block scalars that a round-trip
destroys, which is why only the source side uses a parser.
"""

from __future__ import annotations

import pathlib
import re
import sys

import yaml

ROSTER = pathlib.Path(__file__).resolve().parent.parent / "housecast" / "data" / "roster.yaml"

KINDS = {"role": "roles", "personality": "personalities", "boundary": "boundaries"}
SIDES = {"own", "scoped", "defer"}


def skill_body(path: pathlib.Path) -> str:
    return path.read_text()


def read_acts(spec: pathlib.Path) -> list[dict]:
    """The acts a single entity declares, in file order.

    An entity carrying no `acts:` is legal and yields none. A malformed act is
    not: this file feeds a drift test, so a silently dropped act would read as
    drift in roster.yaml and send the next reader to the wrong side of it.
    """
    document = yaml.safe_load(spec.read_text()) or {}
    acts = []
    for position, act in enumerate(document.get("acts") or [], start=1):
        if not isinstance(act, dict) or not act.get("tool") or not act.get("text"):
            raise SystemExit(f"{spec}: act {position} needs both tool and text")
        side = act.get("side")
        if side is not None and side not in SIDES:
            raise SystemExit(f"{spec}: act {position} has side {side!r}, want one of {sorted(SIDES)}")
        acts.append({"side": side, "tool": str(act["tool"]), "text": str(act["text"])})
    return acts


def read_source(data: pathlib.Path) -> dict[str, dict[str, dict]]:
    found: dict[str, dict[str, dict]] = {section: {} for section in KINDS.values()}
    for entry in sorted(data.iterdir()):
        if not entry.is_dir() or entry.name == "invariant":
            continue
        kind, _, slug = entry.name.partition("-")
        if kind not in KINDS:
            raise SystemExit(f"unexpected entity directory {entry.name}")
        spec = entry / f"{kind}.yaml"
        if not spec.is_file():
            raise SystemExit(f"missing {spec}")
        found[KINDS[kind]][slug] = {
            "acts": read_acts(spec),
            "body": skill_body(entry / "SKILL.md"),
        }
    return found


def render_acts(acts: list[dict], indent: str) -> list[str]:
    lines = [f"{indent}acts:"]
    for act in acts:
        lines.append(f'{indent}  - tool: "{act["tool"]}"')
        lines.append(f'{indent}    text: "{act["text"]}"')
        if act["side"]:
            lines.append(f'{indent}    side: {act["side"]}')
    return lines


def rewrite(text: str, source: dict[str, dict[str, dict]]) -> str:
    lines = text.split("\n")
    out: list[str] = []
    section = ""
    entity = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        if re.fullmatch(r"(roles|personalities|boundaries):", line):
            section = line[:-1]
            out.append(line)
            index += 1
            continue
        entity_match = re.fullmatch(r"  ([a-z0-9-]+):", line)
        if section and entity_match:
            entity = entity_match.group(1)
            out.append(line)
            index += 1
            continue
        if section and entity and line == "    body: |":
            out.extend(render_acts(source[section][entity]["acts"], "    "))
            out.append(line)
            body = source[section][entity]["body"].rstrip("\n")
            out.extend(("      " + b).rstrip() for b in body.split("\n"))
            index += 1
            # Skip the vendored body, indented past the field level. Blank
            # lines trailing the block are the file's separator style and stay.
            trailing = 0
            while index < len(lines) and (lines[index].startswith("      ") or not lines[index].strip()):
                trailing = trailing + 1 if not lines[index].strip() else 0
                index += 1
            out.extend([""] * trailing)
            continue
        if re.fullmatch(r"    acts:", line):
            index += 1
            while index < len(lines) and lines[index].startswith("      "):
                index += 1
            continue
        out.append(line)
        index += 1
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <agent-compose/seed/roster/data>", file=sys.stderr)
        return 2
    data = pathlib.Path(sys.argv[1])
    if not data.is_dir():
        print(f"not a directory: {data}", file=sys.stderr)
        return 2
    ROSTER.write_text(rewrite(ROSTER.read_text(), read_source(data)))
    print(f"synced {ROSTER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
