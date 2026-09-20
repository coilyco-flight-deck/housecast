"""Tally one run against the claims in PREREGISTER.md.

Usage: python analyze.py cells.jsonl [--miss 0.15 --hit 0.003 --out 0.6 --jev 0.042]

Prices are USD per million tokens and default to the flash off-peak row read from
the provider's pricing page on the run date. Nothing here is edited by hand.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from harness import billed

ARM_ORDER = ["A", "B", "C", "D", "F"]


def load(path: str) -> tuple[list[dict], list[dict]]:
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line]
    return [r for r in rows if "error" not in r], [r for r in rows if "error" in r]


def per_cell(rows: list[dict], prices: argparse.Namespace) -> dict[tuple[str, str], dict]:
    cells: dict[tuple[str, str], dict] = defaultdict(
        lambda: defaultdict(float) | {"pass": None, "kind": None}
    )
    for r in rows:
        c = cells[(r["arm"], r["tid"])]
        c["kind"] = r["kind"]
        c["requests"] += 1
        c["prompt"] += r["prompt_tokens"]
        c["cached"] += r["cached_tokens"]
        c["completion"] += r["completion_tokens"]
        c["reasoning_chars"] += r["reasoning_chars"]
        c["content_chars"] += r["content_chars"]
        c["latency"] += r["latency_s"] + r.get("jev_ms", 0) / 1000
        c["jev_requests"] += r.get("jev_requests", 0)
        c["jev_tokens"] += r.get("jev_state_tokens", 0)
        c["rereads"] += 1 if r.get("reread") else 0
        if r.get("final"):
            c["pass"] = r["grade"]
            c["needle"] = r.get("needle_state")
            c["compaction"] = r.get("compaction")
    for c in cells.values():
        c["cost"] = billed(
            c["prompt"], c["cached"], c["completion"], prices.miss, prices.hit, prices.out
        )
        c["completion_cost"] = c["completion"] * prices.out / 1e6
        c["jev_cost"] = c["jev_tokens"] * prices.jev / 1e6
    return cells


def arm_of(name: str) -> str:
    return name[0]


def rate(cells: list[dict]) -> float:
    return mean(c["pass"] == "pass" for c in cells) if cells else float("nan")


def summarize(cells: dict[tuple[str, str], dict]) -> dict[str, dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for (arm, _), c in cells.items():
        groups[arm_of(arm)].append(c)
    out = {}
    for arm, cs in groups.items():
        graded = [c for c in cs if c["pass"]]
        out[arm] = {
            "cells": len(cs),
            "requests": mean(c["requests"] for c in cs),
            "prompt": mean(c["prompt"] for c in cs),
            "hit_share": sum(c["cached"] for c in cs) / sum(c["prompt"] for c in cs),
            "completion": mean(c["completion"] for c in cs),
            "rereads": mean(c["rereads"] for c in cs),
            "latency_s": mean(c["latency"] for c in cs),
            "cost": mean(c["cost"] for c in cs),
            "jev_cost": mean(c["jev_cost"] for c in cs),
            "pass_rate": rate(graded),
            "pass_early": rate([c for c in graded if c["kind"] == "early"]),
            "pass_recent": rate([c for c in graded if c["kind"] == "recent"]),
            "needle": {
                s: sum(c.get("needle") == s for c in graded) for s in ("full", "truncated", "gone")
            },
            "completion_share": sum(c["completion_cost"] for c in cs) / sum(c["cost"] for c in cs),
            "reasoning_share": sum(c["reasoning_chars"] for c in cs)
            / max(1, sum(c["reasoning_chars"] + c["content_chars"] for c in cs)),
        }
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("cells")
    p.add_argument("--miss", type=float, default=0.15)
    p.add_argument("--hit", type=float, default=0.003)
    p.add_argument("--out", type=float, default=0.6)
    p.add_argument("--jev", type=float, default=0.042)
    args = p.parse_args()

    rows, errors = load(args.cells)
    cells = per_cell(rows, args)
    print(f"requests={len(rows)} failed_cells={len(errors)} cells={len(cells)}")
    for e in errors:
        print("FAILED", e["arm"], e["tid"], e["error"][:120])

    print("\nper arm (mean over transcripts, all requests of the cell):")
    s = summarize(cells)
    for arm in ARM_ORDER:
        if arm not in s:
            continue
        a = s[arm]
        print(
            f"* {arm} n={a['cells']} req={a['requests']:.1f} prompt={a['prompt']:.0f} "
            f"hit={a['hit_share']:.1%} completion={a['completion']:.0f} rereads={a['rereads']:.2f} "
            f"lat={a['latency_s']:.1f}s cost=${a['cost']:.5f} +jevEST=${a['jev_cost']:.5f} "
            f"pass={a['pass_rate']:.0%} early={a['pass_early']:.0%} recent={a['pass_recent']:.0%} "
            f"needle={a['needle']}"
        )

    a_runs = defaultdict(list)
    for (arm, _), c in cells.items():
        if arm_of(arm) == "A":
            a_runs[arm].append(c)
    print("\nA repeats (noise floor):")
    for arm, cs in sorted(a_runs.items()):
        print(
            f"* {arm} cost=${mean(c['cost'] for c in cs):.5f} "
            f"hit={sum(c['cached'] for c in cs) / sum(c['prompt'] for c in cs):.1%} "
            f"pass={mean(c['pass'] == 'pass' for c in cs):.0%}"
        )
    costs = [mean(c["cost"] for c in cs) for cs in a_runs.values()]
    passes = [mean(c["pass"] == "pass" for c in cs) for cs in a_runs.values()]
    spread = (max(costs) - min(costs)) / mean(costs)
    print(
        f"* A cost spread={spread:.1%} of mean, A pass range={min(passes):.0%} to {max(passes):.0%}"
    )

    base = s["A"]
    print("\nclaims, by the thresholds in PREREGISTER.md:")
    if "D" in s:
        drop = base["hit_share"] - s["D"]["hit_share"]
        print(
            f"* C1 D hit share {s['D']['hit_share']:.1%} vs A {base['hit_share']:.1%}: "
            f"{drop * 100:+.1f} points lost, "
            f"{'HELD' if drop >= 0.10 else 'NOT HELD'} (threshold 10)"
        )
    cuts = {}
    for arm in ("B", "C", "D", "F"):
        if arm in s:
            total = s[arm]["cost"] + s[arm]["jev_cost"]
            cuts[arm] = 1 - total / base["cost"]
            print(
                f"* cost {arm} incl Jev EST: ${total:.5f} vs A ${base['cost']:.5f} "
                f"= {cuts[arm]:+.1%}"
            )
    best = max((cuts.get(a, -9) for a in ("C", "D")), default=-9)
    if best > -9:
        held = best >= 0.15
        print(
            f"* C2 best of C or D cuts cost {best:+.1%}: "
            f"{'HELD' if held else 'NOT HELD'} (threshold 15%)"
        )
        if "B" in cuts:
            gap = best - cuts["B"]
            print(
                f"  B cuts {cuts['B']:+.1%}, gap to best Jev arm {gap * 100:+.1f} points: "
                f"{'Jev earns its request' if gap > 0.10 else 'Jev NOT earning its extra request'}"
            )
    a_pass = base["pass_rate"]
    for arm in ("B", "C", "D", "F"):
        if arm in s:
            loss = a_pass - s[arm]["pass_rate"]
            print(
                f"* C3 {arm} pass {s[arm]['pass_rate']:.0%} vs A {a_pass:.0%}: "
                f"{loss * 100:+.0f} points lost, "
                f"{'HELD' if loss <= 0.05 else 'NOT HELD'} (threshold 5)"
            )
    print(
        f"* C4 completion cost share of A = {base['completion_share']:.1%}: "
        f"{'HELD' if base['completion_share'] >= 0.30 else 'NOT HELD'} (threshold 30%)"
    )
    print(
        f"* E gate, reasoning share of A output chars EST = {base['reasoning_share']:.1%} "
        f"(E runs only at 20% or more of completion tokens)"
    )
    c_cells = [c for (arm, _), c in cells.items() if arm == "C" and c.get("compaction")]
    if c_cells:
        alld = sum(
            c["compaction"]["callsDropped"] + c["compaction"]["resultsDropped"]
            == c["compaction"]["calls"] - c["compaction"]["pinned"]
            for c in c_cells
        )
        verdict = "F not informative" if alld / len(c_cells) >= 0.8 else "F usable"
        print(
            f"* F informative? C dropped every unpinned call in {alld} of "
            f"{len(c_cells)} transcripts ({verdict})"
        )


if __name__ == "__main__":
    main()
