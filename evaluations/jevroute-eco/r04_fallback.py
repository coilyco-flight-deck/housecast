"""Rescore r04's gate run as a plain choice with a low-confidence fallback to no tool."""

import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
for n in (1, 2):
    rows = [
        json.loads(line)
        for split in ("dev", "holdout", "sealed")
        for line in (run_dir / f"{split}.run{n}.jsonl").read_text().splitlines()
    ]
    tally = {"tool_pass": 0, "tool_n": 0, "tool_conf_wrong": 0, "nt_fallback": 0, "nt_n": 0}
    confident_on_no_tool = []
    for r in rows:
        tool = r["raw"]["answers"]["tool"]
        probs, conf = tool["probabilities"], tool["confidence"]
        win = max(probs, key=probs.get)
        if "no_tool" not in r["ok"]:
            tally["tool_n"] += 1
            tally["tool_pass"] += conf >= 0.9 and win in r["ok"]
            tally["tool_conf_wrong"] += conf >= 0.9 and win not in r["ok"]
        elif r["ok"] == ["no_tool"]:
            tally["nt_n"] += 1
            tally["nt_fallback"] += conf < 0.9
            if conf >= 0.9:
                confident_on_no_tool.append((win, conf, r["q"]))
    print(f"run{n}: {tally}")
    for item in confident_on_no_tool:
        print(f"  no_tool question routed with confidence: {item}")
