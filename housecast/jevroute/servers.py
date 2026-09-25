"""Server-first Jev routing: pick an MCP server, then a tool inside it.

Call 1 asks the server choice (plus no_server) and the front question (one request or
several) together. Call 2 asks the tool choice over the winning server's tools. Both
metrics from bench.py apply per stage: strict (winner confidence) and any (probability
mass on acceptable answers), each at the threshold. End to end needs both stages.

    python -m housecast.jevroute.servers run --inventory F --cases F --front F --out DIR
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

from housecast.jevroute.bench import post_jev

NO_SERVER = "no_server"
SINGLE, MULTI = "one_request", "several_requests"
FRONT = {
    SINGLE: "The message asks for one thing, answerable by one lookup or one action.",
    MULTI: "The message asks for two or more separate things, each needing its own lookup or "
    "action, so it must be split before routing.",
}
SERVER_Q = "Which single MCP server's tools best answer the user's message?"
NO_SERVER_TEXT = (
    "No server here answers this. General knowledge, writing, arithmetic, and actions "
    "none of these servers can take."
)
TOOL_Q = "Which single tool of this MCP server best answers the user's message?"


def server_text(entry: dict[str, Any], prose: str) -> str:
    if prose == "skill" or not entry.get("description"):
        return str(entry.get("skill_description") or entry.get("description") or "")
    return str(entry["description"])


def judge(
    probs: dict[str, float], conf: float | None, ok: list[str], threshold: float
) -> dict[str, Any]:
    if not probs:
        return {"win": None, "conf": None, "strict": False, "any": False, "cw": False}
    win = max(probs, key=lambda k: probs[k])
    sure = conf is not None and conf >= threshold
    mass = sum(v for k, v in probs.items() if k in ok)
    return {
        "win": win,
        "conf": conf,
        "mass": round(mass, 3),
        "strict": win in ok and sure,
        "any": mass >= threshold,
        "cw": sure and win not in ok,
    }


def answer(reply: dict[str, Any], key: str) -> tuple[dict[str, float], float | None]:
    a = reply.get("answers", {}).get(key, {})
    return a.get("probabilities") or {}, a.get("confidence")


def route(
    case: dict[str, Any], inv: dict[str, Any], servers: dict[str, str], model: str, threshold: float
) -> dict[str, Any]:
    t0 = time.time()
    first = post_jev(
        {
            "model": model,
            "state": {"user_message": case["q"]},
            "questions": {
                "server": {"type": "choice", "instructions": SERVER_Q, "criteria": servers},
                "front": {
                    "type": "choice",
                    "instructions": "Does the message hold one request or several?",
                    "criteria": FRONT,
                },
            },
        }
    )
    t1 = time.time()
    front_ok = [MULTI] if case.get("multi") else [SINGLE]
    row: dict[str, Any] = {
        "q": case["q"],
        "front": judge(*answer(first, "front"), front_ok, threshold),
        "sec_server": round(t1 - t0, 3),
        "raw_server": first,
    }
    if "server" not in case:
        return row
    srv = judge(*answer(first, "server"), case["server"], threshold)
    row["server"] = srv
    chosen = srv["win"]
    if chosen in (None, NO_SERVER) or chosen not in inv:
        row["tool"] = {"skipped": True}
        e2e = chosen == NO_SERVER and NO_SERVER in case["server"]
        row["e2e_strict"], row["e2e_any"] = e2e and srv["strict"], e2e and srv["any"]
        return row
    second = post_jev(
        {
            "model": model,
            "state": {"user_message": case["q"], "server": chosen},
            "questions": {
                "tool": {"type": "choice", "instructions": TOOL_Q, "criteria": inv[chosen]["tools"]}
            },
        }
    )
    row["sec_tool"] = round(time.time() - t1, 3)
    row["raw_tool"] = second
    tool = judge(*answer(second, "tool"), case["tool"], threshold)
    row["tool"] = tool
    right_server = chosen in case["server"]
    row["e2e_strict"] = right_server and srv["strict"] and tool["strict"]
    row["e2e_any"] = right_server and srv["any"] and tool["any"]
    return row


def run(a: argparse.Namespace) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    inv = json.loads(Path(a.inventory).read_text())
    servers = {k: server_text(v, a.server_prose) for k, v in inv.items() if v.get("tools")}
    servers[NO_SERVER] = NO_SERVER_TEXT
    (out / "servers.json").write_text(json.dumps(servers, indent=1, sort_keys=True) + "\n")
    summary: dict[str, Any] = {
        "meta": {
            "inventory": a.inventory,
            "server_prose": a.server_prose,
            "model": a.model,
            "threshold": a.threshold,
            "n_servers": len(servers) - 1,
        },
        "splits": {},
    }
    for path in [*a.cases, *a.front]:
        split = Path(path).stem
        cases = yaml.safe_load(Path(path).read_text())["cases"]
        for rep in range(1, a.reps + 1):
            with ThreadPoolExecutor(a.par) as ex:
                rows = list(ex.map(lambda c: route(c, inv, servers, a.model, a.threshold), cases))
            with (out / f"{split}.run{rep}.jsonl").open("w") as fh:
                fh.writelines(json.dumps(r) + "\n" for r in rows)
            s = tally(rows)
            summary["splits"].setdefault(split, []).append(s)
            print(f"{split} run{rep}: " + "  ".join(f"{k} {v}" for k, v in s.items()))
    (out / "report.json").write_text(json.dumps(summary, indent=1) + "\n")
    return 0


def tally(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    s: dict[str, Any] = {"n": n}
    s["front_any"] = sum(r["front"]["any"] for r in rows)
    s["front_cw"] = sum(r["front"]["cw"] for r in rows)
    routed = [r for r in rows if "server" in r]
    if routed:
        s["server_any"] = sum(r["server"]["any"] for r in routed)
        s["server_strict"] = sum(r["server"]["strict"] for r in routed)
        s["server_cw"] = sum(r["server"]["cw"] for r in routed)
        s["tool_cw"] = sum(r["tool"].get("cw", False) for r in routed)
        s["e2e_any"] = sum(r["e2e_any"] for r in routed)
        s["e2e_strict"] = sum(r["e2e_strict"] for r in routed)
    secs = sorted(r["sec_server"] + r.get("sec_tool", 0) for r in rows)
    s["median_sec"] = round(secs[n // 2], 2) if secs else None
    s["errors"] = sum(
        1 for r in rows if "error" in r["raw_server"] or "error" in r.get("raw_tool", {})
    )
    return s


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="jevroute-servers")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--inventory", required=True)
    r.add_argument("--cases", nargs="*", default=[])
    r.add_argument("--front", nargs="*", default=[])
    r.add_argument("--out", required=True)
    r.add_argument("--server-prose", choices=["live", "skill"], default="live")
    r.add_argument("--model", default="jev-latest")
    r.add_argument("--threshold", type=float, default=0.9)
    r.add_argument("--reps", type=int, default=2)
    r.add_argument("--par", type=int, default=16)
    return run(p.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
