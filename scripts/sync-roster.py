#!/usr/bin/env python3
"""Sync data/roster.yaml's vendored bodies and acts from the Go source tree.

Scaffolding, not architecture. agent-compose/internal/person/data is the author
surface until #339 deletes the Go engine, and until then roster.yaml is a
vendored mirror that drifts silently. checks/tests/test_source_drift.py in
agent-compose is what catches the drift; this is what closes it.

The edits are textual on purpose. roster.yaml carries a hand-written header and
block scalars that a YAML round-trip destroys.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROSTER = pathlib.Path(__file__).resolve().parent.parent / "housecast" / "data" / "roster.yaml"
ACT = re.compile(r'^\s*act\s+(?:"(?P<side>own|scoped|defer)"\s+)?tool="(?P<tool>[^"]+)"\s+"(?P<text>.+)"\s*$')

KINDS = {"role": "roles", "personality": "personalities", "boundary": "boundaries"}


def skill_body(path: pathlib.Path) -> str:
    return path.read_text()


def read_source(data: pathlib.Path) -> dict[str, dict[str, dict]]:
    found: dict[str, dict[str, dict]] = {section: {} for section in KINDS.values()}
    for entry in sorted(data.iterdir()):
        if not entry.is_dir() or entry.name == "invariant":
            continue
        kind, _, slug = entry.name.partition("-")
        if kind not in KINDS:
            raise SystemExit(f"unexpected entity directory {entry.name}")
        kdl = entry / f"{kind}.kdl"
        acts = []
        for line in kdl.read_text().splitlines():
            match = ACT.match(line)
            if match:
                acts.append(match.groupdict())
        found[KINDS[kind]][slug] = {
            "acts": acts,
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
            # Skip the vendored body: every line indented past the field level,
            # plus the blank lines inside it. Blank lines trailing the block are
            # the file's own separator style and survive.
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
        print(f"usage: {sys.argv[0]} <agent-compose/internal/person/data>", file=sys.stderr)
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
