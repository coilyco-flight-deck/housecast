"""Replay the Sirens Echo tool router's Jev request against committed cases.

Mirrors sirens-echo internal/community/toolroute.go at a pinned rev: one request holding
the server pick (servers plus none) and one tool pick per server (its tools plus no_tool),
state {"message": text}, and a direct call only when both winners reach 0.9.

    python -m housecast.jevroute.echorouter --roster F --cases F... --out DIR
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

from housecast.jevroute.bench import post_jev

# Copied verbatim from toolroute.go at sirens-echo 0506b64, so a drift there is visible.
THRESHOLD = 0.9
SERVER_KEY = "tool.server"
PICK_PREFIX = "tool.pick:"
NONE = "none"
NO_TOOL = "no_tool"
NONE_TEXT = (
    "No server's tools are needed: social talk, opinions, how-to answerable from knowledge, "
    "or a request addressed to a person."
)
NO_TOOL_TEXT = (
    "No tool from this server answers this. Game mechanics and how-to, client crashes and bug "
    "reports, wipe or patch schedules, requests addressed to a specific person, and anything "
    "outside this server's data."
)
SERVER_PROMPT = "Which MCP server's tools, if any, would answer the member's message?"


def tool_prompt(server: str) -> str:
    return (
        f'Which single tool from the MCP server "{server}" best answers the member\'s message? '
        f"Pick {NO_TOOL} when no tool's data can answer it."
    )


CONTESTED = 0.5  # sirens-echo 9e03ab1 jevToolContested


def request_no_server(message: str, roster: dict[str, Any], model: str) -> dict[str, Any]:
    """sirens-echo 9e03ab1: no server pick, one tool pick per server with its guidance."""
    questions: dict[str, Any] = {}
    for name in sorted(roster):
        entry = roster[name]
        tools = {k: v for k, v in entry["tools"].items() if k and k != NO_TOOL}
        if not tools or len(tools) + 1 > 240:
            continue
        prompt = tool_prompt(name)
        if entry.get("description"):
            prompt += " The server describes itself: " + entry["description"]
        questions[PICK_PREFIX + name] = {
            "type": "choice",
            "instructions": prompt,
            "criteria": {**tools, NO_TOOL: NO_TOOL_TEXT},
        }
    return {"model": model, "state": {"message": message}, "questions": questions}


def score_no_server(case: dict[str, Any], reply: dict[str, Any]) -> dict[str, Any]:
    best: tuple[str | None, str | None, float] = (None, None, 0.0)
    rival = 0.0
    for key, answer in reply.get("answers", {}).items():
        if not key.startswith(PICK_PREFIX):
            continue
        tool, p = top(answer)
        if tool in (None, NO_TOOL):
            continue
        if p > best[2]:
            rival = max(rival, best[2])
            best = (key[len(PICK_PREFIX) :], tool, p)
        else:
            rival = max(rival, p)
    server, tool, tp = best
    declined = tool is None
    want_decline = NO_TOOL in case["ok"]
    right_route = (declined and want_decline) or (
        not declined and server == case["server"] and tool in case["ok"]
    )
    direct = not declined and tp >= THRESHOLD and rival < CONTESTED
    return {
        "q": case["q"],
        "ok": case["ok"],
        "server": server,
        "tool": tool,
        "tool_p": round(tp, 3),
        "rival_p": round(rival, 3),
        "declined": declined,
        "right_route": right_route,
        "direct_right": direct and right_route,
        "direct_wrong": direct and not right_route,
        "contested": not declined and tp >= THRESHOLD and rival >= CONTESTED,
    }


def score_tiered(case: dict[str, Any], reply: dict[str, Any], general: set[str]) -> dict[str, Any]:
    """sirens-echo 557d539: a domain pick at >= CONTESTED keeps general servers out."""
    picks = []
    for key, answer in reply.get("answers", {}).items():
        if not key.startswith(PICK_PREFIX):
            continue
        tool, p = top(answer)
        if tool not in (None, NO_TOOL):
            picks.append((p, key[len(PICK_PREFIX) :], tool))
    domain = sorted((x for x in picks if x[1] not in general), reverse=True)
    field = domain if domain and domain[0][0] >= CONTESTED else sorted(picks, reverse=True)
    tp, server, tool = field[0] if field else (0.0, None, None)
    rival_p, rival = (
        (field[1][0], f"{field[1][1]}:{field[1][2]}") if len(field) > 1 else (0.0, None)
    )
    declined = tool is None
    want_decline = NO_TOOL in case["ok"]
    right_route = (declined and want_decline) or (
        not declined and server == case["server"] and tool in case["ok"]
    )
    direct = not declined and tp >= THRESHOLD and rival_p < CONTESTED
    return {
        "q": case["q"],
        "ok": case["ok"],
        "server": server,
        "tool": tool,
        "tool_p": round(tp, 3),
        "rival_p": round(rival_p, 3),
        "rival": rival,
        "declined": declined,
        "right_route": right_route,
        "direct_right": direct and right_route,
        "direct_wrong": direct and not right_route,
        "contested": not declined and tp >= THRESHOLD and rival_p >= CONTESTED,
    }


def request(message: str, roster: dict[str, Any], model: str) -> dict[str, Any]:
    servers = {NONE: NONE_TEXT}
    questions: dict[str, Any] = {}
    for name in sorted(roster):
        entry = roster[name]
        tools = {k: v for k, v in entry["tools"].items() if k and k != NO_TOOL}
        if not tools or len(tools) + 1 > 240:
            continue
        servers[name] = entry.get("description") or f'Tools from the MCP server "{name}".'
        questions[PICK_PREFIX + name] = {
            "type": "choice",
            "instructions": tool_prompt(name),
            "criteria": {**tools, NO_TOOL: NO_TOOL_TEXT},
        }
    return {
        "model": model,
        "state": {"message": message},
        "questions": {
            SERVER_KEY: {"type": "choice", "instructions": SERVER_PROMPT, "criteria": servers},
            **questions,
        },
    }


def top(answer: dict[str, Any]) -> tuple[str | None, float]:
    probs = answer.get("probabilities") or {}
    if not probs:
        return None, 0.0
    win = max(probs, key=lambda k: probs[k])
    return win, float(probs[win])


def score(case: dict[str, Any], reply: dict[str, Any]) -> dict[str, Any]:
    answers = reply.get("answers", {})
    server, sp = top(answers.get(SERVER_KEY, {}))
    tool, tp = (
        top(answers.get(PICK_PREFIX + server, {})) if server not in (None, NONE) else (None, 0.0)
    )
    declined = server == NONE or tool == NO_TOOL
    want_decline = NO_TOOL in case["ok"]
    right_route = (declined and want_decline) or (
        not declined and server == case["server"] and tool in case["ok"]
    )
    direct = not declined and sp >= THRESHOLD and tp >= THRESHOLD
    return {
        "q": case["q"],
        "ok": case["ok"],
        "server": server,
        "server_p": round(sp, 3),
        "tool": tool,
        "tool_p": round(tp, 3),
        "declined": declined,
        "right_route": right_route,
        "direct_right": direct and right_route,
        "direct_wrong": direct and not right_route,
        "decline_confident": declined and (sp if server == NONE else tp) >= THRESHOLD,
    }


def main(argv: list[str] | None = None) -> int:
    # allow_abbrev off: "--mode" once silently matched "--model" and sent a bad model id.
    p = argparse.ArgumentParser(prog="jevroute-echorouter", allow_abbrev=False)
    p.add_argument("--roster", required=True)
    p.add_argument("--cases", nargs="+", required=True)
    p.add_argument("--server", required=True, help="roster name the cases' tools belong to")
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="jev-latest")
    p.add_argument("--reps", type=int, default=2)
    p.add_argument("--par", type=int, default=8)
    p.add_argument(
        "--mode", choices=["server-pick", "no-server-pick", "tiered"], default="server-pick"
    )
    p.add_argument("--general", nargs="*", default=[], help="general-tier servers (tiered)")
    p.add_argument(
        "--skip", nargs="*", default=[], help="tool or server__tool (sirens-echo 3682f81)"
    )
    a = p.parse_args(argv)
    roster = json.loads(Path(a.roster).read_text())
    skip = set(a.skip)
    for name, entry in roster.items():
        entry["tools"] = {
            t: d for t, d in entry["tools"].items() if t not in skip and f"{name}__{t}" not in skip
        }
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    general = set(a.general)
    build, judge = {
        "server-pick": (request, score),
        "no-server-pick": (request_no_server, score_no_server),
        "tiered": (request_no_server, lambda c, r: score_tiered(c, r, general)),
    }[a.mode]
    for path in a.cases:
        split = Path(path).stem.removeprefix("cases-")
        cases = [{**c, "server": a.server} for c in yaml.safe_load(Path(path).read_text())["cases"]]
        for rep in range(1, a.reps + 1):
            with ThreadPoolExecutor(a.par) as ex:
                replies = list(ex.map(lambda c: post_jev(build(c["q"], roster, a.model)), cases))
            rows = [judge(c, r) for c, r in zip(cases, replies, strict=True)]
            with (out / f"{split}.run{rep}.jsonl").open("w") as fh:
                fh.writelines(
                    json.dumps({**r, "raw": x}) + "\n" for r, x in zip(rows, replies, strict=True)
                )
            n = len(rows)
            print(
                f"{split} run{rep}: right_route {sum(r['right_route'] for r in rows)}/{n}"
                f"  direct_right {sum(r['direct_right'] for r in rows)}"
                f"  direct_wrong {sum(r['direct_wrong'] for r in rows)}"
                f"  declined {sum(r['declined'] for r in rows)}"
                f"  contested {sum(r.get('contested', False) for r in rows)}"
                f"  errors {sum('error' in x for x in replies)}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
