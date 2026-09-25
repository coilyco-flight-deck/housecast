"""Snapshot every MCP server's description and tools, the criteria for server-first routing.

HTTP servers are read live (initialize instructions, tools/list). A stdio server is read
from its generated mcp-tools skill: SKILL.md description and references/tools*.md lines.

    python -m housecast.jevroute.inventory --mcporter F --skills DIR --out inventory.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from housecast.jevroute.bench import parse_mcp_body

HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def live(url: str) -> dict[str, Any]:
    import httpx

    headers = dict(HEADERS)
    with httpx.Client(timeout=30) as client:
        init = client.post(
            url,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "housecast-jevroute", "version": "0"},
                },
            },
        )
        result = parse_mcp_body(init.text).get("result", {})
        if sid := init.headers.get("mcp-session-id"):
            headers["Mcp-Session-Id"] = sid
            client.post(
                url, headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"}
            )
        reply = client.post(
            url,
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
    tools = parse_mcp_body(reply.text)["result"]["tools"]
    return {
        "source": "live",
        "description": result.get("instructions") or "",
        "tools": {t["name"]: t.get("description") or "" for t in tools},
    }


def generated(skill_dir: Path) -> dict[str, Any]:
    head = (skill_dir / "SKILL.md").read_text()
    match = re.search(r"^description:\s*(.+)$", head, re.M)
    tools: dict[str, str] = {}
    for ref in sorted((skill_dir / "references").glob("tools*.md")):
        for m in re.finditer(r"^\* `(\w[\w-]*)\(.*?\)` - (.+)$", ref.read_text(), re.M):
            tools[m.group(1)] = m.group(2)
    return {
        "source": "generated",
        "description": match.group(1).strip() if match else "",
        "tools": tools,
    }


def skill_name(server: str) -> str:
    return "mcp-tools-" + server.replace("_", "-")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="jevroute-inventory")
    p.add_argument("--mcporter", required=True)
    p.add_argument("--skills", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--skip", nargs="*", default=[])
    a = p.parse_args(argv)
    servers = json.loads(Path(a.mcporter).read_text()).get("mcpServers", {})
    inv: dict[str, Any] = {}
    for name, cfg in sorted(servers.items()):
        if name in a.skip:
            continue
        url = cfg.get("baseUrl") or cfg.get("url")
        skill = Path(a.skills) / skill_name(name)
        try:
            inv[name] = live(url) if url else generated(skill)
        except Exception as e:  # recorded, never silently dropped
            inv[name] = {"source": "error", "error": repr(e)[:200], "description": "", "tools": {}}
        if (skill / "SKILL.md").exists():
            inv[name]["skill_description"] = generated(skill)["description"]
        print(f"{name}: {inv[name]['source']} tools={len(inv[name]['tools'])}")
    Path(a.out).write_text(json.dumps(inv, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
