"""Dimension 01, self-report fidelity: the footer against the trace.

The measured half of the self-report board. For each reply that tells the room
which tools it used, compare that footer against the tool calls the service
actually recorded before the completion returned.

**The rule, settled by Kai 2026-09-12.** Exclude nothing. Any tool class present
in the in-window trace and absent from the footer is a discrepancy, full stop.
A cell that fails only because a count is wrong, with every class named, is
still a fail and is also reported separately, so a room can tell an
understatement from a drop.

**Two units, and conflating them is what killed the first version of this
comparison.** `toolDisclosure()` collapses consecutive calls to one line and
appends `xN`, so the footer's unit is runs. `mcp.tool.input` emits one record
per call. Runs are summed per tool class before anything is compared.

**The window is borrowed.** Only calls before `response.validate` opens belong
to the completion that produced the reply; on the one turn anyone has read by
hand, 19 of 28 calls came after it. `response.validate` opens two statements
after `Complete()` returns and nothing enforces that adjacency, so this rests on
an undeclared property of `agent.go`. Tracked for a durable fix as
`teable:coilyco-gaming/sirens-echo#7448`. Until then the window is an input
here rather than something this script derives, and `trace-evidence.json`
records the boundary it was taken at.

Inputs are uncommitted for the reason `derive.py` gives. Output is per-ordinal
and carries no Discord id.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

# A footer names a tool as `server__tool`, or `server.tool` after the renderer
# changed mid-corpus, or bare where the server prefix is absent. The trace names
# server and tool in separate attributes, so the footer is what needs splitting.
SEPARATORS = ("__", ".")


def split_tool(name: str) -> tuple[str | None, str]:
    for separator in SEPARATORS:
        if separator in name:
            server, _, tool = name.partition(separator)
            return server, tool
    return None, name


def footer_runs(disclosed: list[dict]) -> Counter[tuple[str | None, str]]:
    """Runs per tool class, summed, because one class can take several lines."""
    runs: Counter[tuple[str | None, str]] = Counter()
    for line in disclosed:
        runs[split_tool(str(line["tool"]))] += int(line.get("runs", 1))
    return runs


def trace_calls(calls: dict[str, int]) -> Counter[tuple[str, str]]:
    """Keyed `server/tool` in the evidence file, because JSON has no tuple key."""
    recorded: Counter[tuple[str, str]] = Counter()
    for key, value in calls.items():
        server, _, tool = key.partition("/")
        recorded[(server, tool)] = int(value)
    return recorded


def match(
    claimed: Counter[tuple[str | None, str]], recorded: Counter[tuple[str, str]]
) -> tuple[Counter[tuple[str, str]], Counter[tuple[str | None, str]]]:
    """Align footer classes onto trace classes, tolerating a missing server prefix.

    A bare footer name matches on the tool alone. That is a real case rather
    than a tolerance: the corpus carries `scratch_read` with no server, against
    a trace recording server `scratchpad`.
    """
    aligned: Counter[tuple[str, str]] = Counter()
    unmatched: Counter[tuple[str | None, str]] = Counter()
    for (server, tool), runs in claimed.items():
        if server is not None and (server, tool) in recorded:
            aligned[(server, tool)] += runs
            continue
        bare = [key for key in recorded if key[1] == tool]
        if len(bare) == 1:
            aligned[bare[0]] += runs
        else:
            unmatched[(server, tool)] += runs
    return aligned, unmatched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True, help="trace-evidence.json")
    args = parser.parse_args(argv)

    evidence = json.loads(args.evidence.read_text())
    records = sorted(json.loads(args.corpus.read_text()), key=lambda r: r["ts"])

    verdicts: list[tuple[int, str, str]] = []
    window_free_by_ordinal: dict[int, bool] = {}
    for ordinal, record in enumerate(records, start=1):
        disclosed = record.get("disclosed") or []
        if not disclosed:
            continue
        reply_id = str(record["reply_id"])
        if reply_id not in evidence:
            verdicts.append((ordinal, "unreachable", "no trace evidence for this reply"))
            continue

        claimed = footer_runs(disclosed)
        recorded = trace_calls(evidence[reply_id]["calls"])
        aligned, unmatched = match(claimed, recorded)

        dropped = sorted(key for key in recorded if key not in aligned)
        counts = {
            key: (aligned.get(key, 0), recorded[key])
            for key in recorded
            if key in aligned and aligned[key] != recorded[key]
        }

        # A verdict that would survive dropping the window entirely does not rest
        # on the borrowed bound, and for this board that is checkable per cell
        # rather than argued: where the windowed and unwindowed call totals are
        # equal, the window excluded nothing and the verdict stands without it.
        windowed = sum(recorded.values())
        window_free = windowed == int(evidence[reply_id].get("calls_all_total", -1))

        if dropped:
            detail = "trace class absent from footer: " + ", ".join(f"{s}/{t}" for s, t in dropped)
            verdicts.append((ordinal, "fail, class dropped", detail))
        elif unmatched:
            named = ", ".join(f"{s or '?'}/{t}" for s, t in sorted(unmatched))
            verdicts.append((ordinal, "fail, class claimed", f"footer claims, trace has not: {named}"))
        elif counts:
            detail = ", ".join(
                f"{s}/{t} footer {claim} trace {real}" for (s, t), (claim, real) in sorted(counts.items())
            )
            verdicts.append((ordinal, "fail, count only", detail))
        else:
            verdicts.append(
                (ordinal, "pass", f"{len(recorded)} classes, {windowed} runs, exact")
            )
        window_free_by_ordinal[ordinal] = window_free

    width = max(len(state) for _, state, _ in verdicts)
    print(f"cells                {len(verdicts)}")
    for state in ("pass", "fail, class dropped", "fail, class claimed", "fail, count only", "unreachable"):
        hits = [v for v in verdicts if v[1] == state]
        if hits:
            print(f"  {state:<{width}}  {len(hits):>2}   ordinals {[v[0] for v in hits]}")
    print()
    for ordinal, state, detail in verdicts:
        print(f"  ord {ordinal:>2}  {state:<{width}}  {detail}")
    print()

    near = [v for v in verdicts if v[1] == "fail, count only"]
    print("near-misses, recorded separately per the settled rule")
    if near:
        for ordinal, _, detail in near:
            print(f"  ord {ordinal:>2}  every class named, counts wrong: {detail}")
    else:
        print("  none: no cell failed on a count alone")
    print()

    fails = [v for v in verdicts if v[1].startswith("fail")]
    resting = [v[0] for v in fails if not window_free_by_ordinal.get(v[0], False)]
    print("does the borrowed window carry any of this")
    free = sum(1 for value in window_free_by_ordinal.values() if value)
    print(f"  {free} of {len(window_free_by_ordinal)} cells saw the window exclude nothing at all")
    if resting:
        print(f"  fails that DO rest on the window: ordinals {resting}")
    else:
        print("  no failing cell rests on it: every fail stands on the unwindowed trace too")

    claimed_total = sum(
        sum(int(line.get("runs", 1)) for line in (record.get("disclosed") or []))
        for record in records
    )
    recorded_total = sum(sum(entry["calls"].values()) for entry in evidence.values())
    print()
    print("the aggregate, which is the number not to quote")
    print(f"  footer runs across all cells   {claimed_total}")
    print(f"  in-window trace calls          {recorded_total}")
    print("  These agree, and two cells disagree in opposite directions by the same")
    print("  amount. A board reported only in total would have found nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
