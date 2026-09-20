"""Replay frozen transcripts through deepseek under each compaction arm.

Usage: python run_ladder.py --workload DIR --out DIR --lib JEV_LIB --repo REPO
See PREREGISTER.md for the arms and what each measurement is for.

Every (transcript, arm) is a ladder: the history up to turn k plus a short prompt,
sent sequentially at the ladder steps, then the final question. The next-step
replies are discarded, so the history is teacher-forced. A per-cell salt sits in
the system prompt so no arm shares a cache prefix with another. The final
question may be answered by a re-read, which is how a dropped result is
recovered in a live loop, and every re-read is a counted request.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from build_workload import N_CALLS, load_files, number
from harness import (
    MAX_REREADS,
    NUDGE,
    SYSTEM,
    cached_tokens,
    drop_counts,
    grade,
    reread_target,
    sha256,
    to_chat,
)

HERE = Path(__file__).parent
DEFAULT_PROXY = "http://ser8:8080/v1"
DEFAULT_MODEL = "evaluation/deepseek-v4-flash"


class Ctx:
    def __init__(self, args: argparse.Namespace, files: dict[str, dict[str, str]]) -> None:
        self.proxy = args.proxy
        self.model = args.model
        self.lib = str(Path(args.lib).resolve())
        self.run_id = args.run_id
        self.steps = {int(s) for s in args.steps.split(",")}
        self.gap = args.gap
        self.files = files
        self.out = Path(args.out) / "cells.jsonl"
        self.lock = threading.Lock()
        self.counts: dict[str, dict[str, int]] = {}

    def write(self, record: dict[str, Any]) -> None:
        with self.lock, self.out.open("a") as fh:
            fh.write(json.dumps(record) + "\n")


def chat(ctx: Ctx, messages: list[dict[str, str]], max_tokens: int) -> tuple[dict, float, int]:
    body = {
        "model": ctx.model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "seed": 7,
    }
    last = ""
    for attempt in range(4):
        started = time.monotonic()
        try:
            request = urllib.request.Request(
                f"{ctx.proxy}/chat/completions",
                json.dumps(body).encode(),
                {"content-type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.load(response), time.monotonic() - started, attempt
        except urllib.error.HTTPError as err:
            last = f"HTTP {err.code}: {err.read()[:200]!r}"
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            last = repr(err)
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(last)


def compact(ctx: Ctx, mode: str, messages: list[dict], counts: dict | None = None) -> dict:
    payload = {
        "lib": ctx.lib,
        "mode": mode,
        "messages": messages,
        "baseUrl": ctx.proxy.removesuffix("/v1") + "/v1/systemone",
        "counts": counts or {},
    }
    done = subprocess.run(
        ["node", str(HERE / "compact_cli.mjs")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if done.returncode:
        raise RuntimeError(f"compact {mode}: {done.stderr[-300:]}")
    return json.loads(done.stdout)


def send(
    ctx: Ctx, cell: dict, step: str, messages: list[dict[str, str]], max_tokens: int
) -> tuple[dict, str]:
    data, latency, retries = chat(ctx, messages, max_tokens)
    choice = data["choices"][0]
    message = choice["message"]
    usage = data.get("usage") or {}
    content = message.get("content") or ""
    record = {
        **cell,
        "step": step,
        "at": datetime.now(UTC).isoformat(),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "cached_tokens": cached_tokens(usage),
        "completion_tokens": usage.get("completion_tokens", 0),
        "reasoning_chars": len(message.get("reasoning_content") or ""),
        "content_chars": len(content),
        "finish": choice.get("finish_reason"),
        "latency_s": round(latency, 2),
        "retries": retries,
        "prompt_chars": sum(len(m["content"]) for m in messages),
        "prompt_sha256": sha256(messages),
    }
    return record, content


def needle_state(t: dict, history: list[dict]) -> str:
    tool_id = f"toolu_{t['id'][1:]}_{t['needle_call'] - 1:02d}"
    for message in history:
        for result in message.get("toolResults") or []:
            if result["tool_use_id"] == tool_id:
                original = next(
                    r["text"]
                    for m in t["messages"]
                    for r in m.get("toolResults") or []
                    if r["tool_use_id"] == tool_id
                )
                return "full" if result["text"] == original else "truncated"
    return "gone"


def run_cell(ctx: Ctx, t: dict, arm: str) -> None:
    cell = {"run_id": ctx.run_id, "arm": arm, "tid": t["id"], "kind": t["kind"], "model": ctx.model}
    base = arm[0]
    system = f"{SYSTEM} Run tag: {ctx.run_id}/{arm}/{t['id']}."
    msgs = t["messages"]
    question = {"role": "user", "text": t["question"], "toolUses": []}
    state = [msgs[0]]
    pending = {"jev_requests": 0, "jev_ms": 0, "jev_state_tokens": 0}

    def absorb(result: dict) -> None:
        pending["jev_requests"] += result["stats"].get("requests", 0)
        pending["jev_ms"] += result["stats"].get("ms", 0)
        pending["jev_state_tokens"] += result["stats"].get("stateTokens", 0)

    def flush() -> dict:
        out = dict(pending)
        pending.update(jev_requests=0, jev_ms=0, jev_state_tokens=0)
        return out

    try:
        for turn in range(1, N_CALLS + 1):
            if base == "D":
                state = state + msgs[2 * turn - 1 : 2 * turn + 1]
                result = compact(ctx, "jev", state)
                state = result["messages"]
                absorb(result)
            if turn not in ctx.steps:
                continue
            raw = msgs[: 2 * turn + 1]
            if base == "B":
                history = compact(ctx, "rule", raw)["messages"]
            else:
                history = state if base == "D" else raw
            record, _ = send(ctx, cell, f"turn{turn}", to_chat(history, system, NUDGE), 2000)
            ctx.write({**record, **flush()})
            time.sleep(ctx.gap)

        full = [*msgs, question]
        result = None
        if base == "B":
            result = compact(ctx, "rule", full)
        elif base == "C":
            result = compact(ctx, "jev", full)
            ctx.counts[t["id"]] = drop_counts(result["decisions"])
        elif base == "D":
            result = compact(ctx, "jev", [*state, question])
        elif base == "F":
            result = compact(ctx, "random", full, ctx.counts[t["id"]])
        if result:
            absorb(result)
        history = result["messages"] if result else full
        conversation = to_chat(history, system)
        for attempt in range(MAX_REREADS + 1):
            record, content = send(ctx, cell, f"final{attempt}", conversation, 4000)
            path = reread_target(content)
            if path in ctx.files[t["ref"]] and attempt < MAX_REREADS:
                ctx.write({**record, "reread": path, **flush()})
                reply = f"[result reread {path}]\n{number(ctx.files[t['ref']][path])}"
                conversation = [
                    *conversation,
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": reply},
                ]
                continue
            ctx.write(
                {
                    **record,
                    **flush(),
                    "final": True,
                    "rereads": attempt,
                    "answer": content,
                    "grade": grade(content, t["expected"]),
                    "needle_state": needle_state(t, history),
                    "compaction": result["stats"] if result else None,
                }
            )
            break
    except RuntimeError as err:
        ctx.write({**cell, "error": str(err), "at": datetime.now(UTC).isoformat()})
        print(f"FAILED {arm} {t['id']}: {err}", file=sys.stderr)
    else:
        print(f"done {arm} {t['id']}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--lib", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--proxy", default=os.environ.get("MCPEVAL_MODEL_BASE_URL", DEFAULT_PROXY))
    parser.add_argument("--model", default=os.environ.get("MCPEVAL_MODEL", DEFAULT_MODEL))
    parser.add_argument("--arms", default="A1,A2,A3,B,C,D,F")
    parser.add_argument("--only", default="")
    parser.add_argument("--steps", default="6,10,14,18,22,26")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--gap", type=float, default=2.0)
    parser.add_argument("--run-id", default=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    args = parser.parse_args()

    only = set(filter(None, args.only.split(",")))
    transcripts = [
        json.loads(p.read_text())
        for p in sorted(Path(args.workload).glob("t*.json"))
        if not only or p.stem in only
    ]
    files = {ref: load_files(args.repo, ref)[0] for ref in {t["ref"] for t in transcripts}}
    Path(args.out).mkdir(parents=True, exist_ok=True)
    ctx = Ctx(args, files)
    meta = {k: v for k, v in vars(args).items()} | {"started_at": datetime.now(UTC).isoformat()}
    (Path(args.out) / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    arms = args.arms.split(",")
    first = [(t, a) for t in transcripts for a in arms if a[0] != "F"]
    with ThreadPoolExecutor(args.concurrency) as pool:
        list(pool.map(lambda job: run_cell(ctx, *job), first))
    second = [(t, a) for t in transcripts for a in arms if a[0] == "F" and t["id"] in ctx.counts]
    with ThreadPoolExecutor(args.concurrency) as pool:
        list(pool.map(lambda job: run_cell(ctx, *job), second))


if __name__ == "__main__":
    main()
