"""Jev tool routing bench: can Jev pick the right MCP tool from its description alone.

One Jev `choice` per question, with the subject's own `tools/list` descriptions
as the criteria plus the call site's extra options. A case passes when the
winner is in its `ok` set at confidence >= the threshold. Confident-wrong (the
same threshold, wrong tool) is tracked apart because it is the costly failure.
    python -m housecast.jevroute.bench run --mcp-url URL --cases F --callsite F --out DIR
    python -m housecast.jevroute.bench diff DIR_A DIR_B
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

PROXY = "http://ser8:8080/v1/systemone"
THRESHOLD = 0.9


def parse_mcp_body(raw: str) -> dict[str, Any]:
    """An MCP HTTP reply is JSON or SSE. SSE carries the JSON on its last data line."""
    if raw.lstrip().startswith("{"):
        out: dict[str, Any] = json.loads(raw)
        return out
    lines = [ln[5:].strip() for ln in raw.splitlines() if ln.startswith("data:")]
    if not lines:
        raise ValueError(f"no JSON and no SSE data line in MCP reply: {raw[:200]!r}")
    last: dict[str, Any] = json.loads(lines[-1])
    return last


def fetch_tools(mcp_url: str) -> dict[str, str]:
    import httpx

    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    with httpx.Client(timeout=60) as client:
        init = client.post(
            mcp_url,
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
        sid = init.headers.get("mcp-session-id")
        if sid:
            headers["Mcp-Session-Id"] = sid
            client.post(
                mcp_url,
                headers=headers,
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )
        reply = client.post(
            mcp_url,
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
    tools = parse_mcp_body(reply.text)["result"]["tools"]
    return {t["name"]: t.get("description") or "" for t in tools}


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = yaml.safe_load(path.read_text())["cases"]
    seen: set[str] = set()
    for c in cases:
        if not c.get("q") or not c.get("ok"):
            raise ValueError(f"{path}: every case needs q and a non-empty ok: {c}")
        if c["q"] in seen:
            raise ValueError(f"{path}: duplicate question {c['q']!r}")
        seen.add(c["q"])
    return cases


def build_request(
    q: str, criteria: dict[str, str], callsite: dict[str, Any], model: str
) -> dict[str, Any]:
    return {
        "model": model,
        "state": {"player_message": q, "context": callsite.get("context", "")},
        "questions": {
            "tool": {
                "type": "choice",
                "instructions": callsite["instructions"],
                "criteria": criteria,
            }
        },
    }


def score(case: dict[str, Any], answer: dict[str, Any], threshold: float) -> dict[str, Any]:
    tool = answer.get("answers", {}).get("tool", {})
    probs: dict[str, float] = tool.get("probabilities") or {}
    if not probs:
        return {
            "q": case["q"],
            "ok": case["ok"],
            "win": None,
            "p": None,
            "conf": None,
            "correct": False,
            "pass": False,
            "confident_wrong": False,
            "error": answer.get("error") or "no probabilities",
        }
    win = max(probs, key=lambda k: probs[k])
    conf = tool.get("confidence")
    correct = win in case["ok"]
    sure = conf is not None and conf >= threshold
    runner_up = sorted(probs.items(), key=lambda kv: -kv[1])[1:2]
    return {
        "q": case["q"],
        "ok": case["ok"],
        "win": win,
        "p": round(probs[win], 3),
        "conf": conf,
        "runner_up": runner_up[0] if runner_up else None,
        "correct": correct,
        "pass": correct and sure,
        "confident_wrong": sure and not correct,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    return {
        "n": n,
        "pass": sum(r["pass"] for r in rows),
        "correct": sum(r["correct"] for r in rows),
        "confident_wrong": sum(r["confident_wrong"] for r in rows),
        "errors": sum(1 for r in rows if r.get("error")),
    }


def post_jev(body: dict[str, Any]) -> dict[str, Any]:
    import httpx

    try:
        reply = httpx.post(PROXY, json=body, timeout=120)
        reply.raise_for_status()
        out: dict[str, Any] = reply.json()
        return out
    except Exception as e:  # a failed call is recorded, never silently retried
        return {"error": repr(e)}


def run(a: argparse.Namespace) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tools = fetch_tools(a.mcp_url)
    callsite = yaml.safe_load(Path(a.callsite).read_text())
    criteria = {**tools, **callsite.get("extra_options", {})}
    blob = json.dumps(tools, sort_keys=True).encode()
    meta = {
        "mcp_url": a.mcp_url,
        "label": a.label,
        "model": a.model,
        "threshold": a.threshold,
        "tools_sha256": hashlib.sha256(blob).hexdigest(),
        "n_tools": len(tools),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (out / "tools.json").write_text(json.dumps(tools, indent=1, sort_keys=True))
    report: dict[str, Any] = {"meta": meta, "splits": {}}
    for cases_path in a.cases:
        split = Path(cases_path).stem.removeprefix("cases-")
        cases = load_cases(Path(cases_path))
        for rep in range(1, a.reps + 1):
            reqs = [build_request(c["q"], criteria, callsite, a.model) for c in cases]
            with ThreadPoolExecutor(a.par) as ex:
                answers = list(ex.map(post_jev, reqs))
            rows = [score(c, ans, a.threshold) for c, ans in zip(cases, answers, strict=True)]
            with (out / f"{split}.run{rep}.jsonl").open("w") as fh:
                for r, ans in zip(rows, answers, strict=True):
                    fh.write(json.dumps({**r, "raw": ans}) + "\n")
            s = summarize(rows)
            report["splits"].setdefault(split, []).append(s)
            print(
                f"{split} run{rep}: pass {s['pass']}/{s['n']}  correct {s['correct']}/{s['n']}"
                f"  confident_wrong {s['confident_wrong']}  errors {s['errors']}"
            )
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(f"tools_sha256 {meta['tools_sha256'][:12]}  n_tools {meta['n_tools']}  out {out}")
    return 0


def diff(a: argparse.Namespace) -> int:
    """Per-question movement between two rounds, run 1 against run 1."""
    for split_file in sorted(Path(a.before).glob("*.run1.jsonl")):
        after = Path(a.after) / split_file.name
        if not after.exists():
            continue
        old = {r["q"]: r for r in map(json.loads, split_file.read_text().splitlines())}
        new = {r["q"]: r for r in map(json.loads, after.read_text().splitlines())}
        print(f"== {split_file.name.split('.')[0]}")
        for q, r in new.items():
            o = old.get(q)
            if o is None or (o["win"], o["pass"]) == (r["win"], r["pass"]):
                continue
            print(
                f"  {'+' if r['pass'] and not o['pass'] else '-' if o['pass'] else '~'} "
                f"{o['win']}@{o['conf']} -> {r['win']}@{r['conf']}  ok={r['ok']}  | {q}"
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="jevroute")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--mcp-url", required=True)
    r.add_argument("--cases", nargs="+", required=True)
    r.add_argument("--callsite", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--label", default="")
    r.add_argument("--model", default="jev-latest")
    r.add_argument("--threshold", type=float, default=THRESHOLD)
    r.add_argument("--reps", type=int, default=2)
    r.add_argument("--par", type=int, default=16)
    d = sub.add_parser("diff")
    d.add_argument("before")
    d.add_argument("after")
    a = p.parse_args(argv)
    return run(a) if a.cmd == "run" else diff(a)


if __name__ == "__main__":
    sys.exit(main())
