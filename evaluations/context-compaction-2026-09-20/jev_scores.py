"""Exploratory: Jev's per-call scores at the final compaction, one transcript at a time.

Usage: python jev_scores.py WORKLOAD_DIR JEV_LIB [PROXY_BASE]

Not a claim under test. It shows why the run's C arm dropped every unpinned call
and where the needle's result ranked among the calls Jev scored.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def score(transcript: dict, lib: str, base: str) -> list[dict]:
    question = {"role": "user", "text": transcript["question"], "toolUses": []}
    payload = {
        "lib": lib,
        "mode": "jev",
        "messages": [*transcript["messages"], question],
        "baseUrl": f"{base}/v1/systemone",
    }
    done = subprocess.run(
        ["node", str(HERE / "compact_cli.mjs")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=300,
        check=True,
    )
    return json.loads(done.stdout)["decisions"]


def main(workload: str, lib: str, base: str = "http://ser8:8080") -> None:
    print("tid   kind    needle keepResult rank/n  max_other  n>=0.5 n>=0.3 n>=0.2")
    for path in sorted(Path(workload).glob("t*.json")):
        t = json.loads(path.read_text())
        decisions = [d for d in score(t, lib, base) if d["reason"] != "pinned"]
        needle_id = f"t{t['needle_call']}"
        needle = next((d for d in decisions if d["id"] == needle_id), None)
        ranked = sorted(decisions, key=lambda d: -d["keepResult"])
        rank = next((i + 1 for i, d in enumerate(ranked) if d["id"] == needle_id), None)
        others = [d["keepResult"] for d in decisions if d["id"] != needle_id]
        counts = [sum(d["keepResult"] >= th for d in decisions) for th in (0.5, 0.3, 0.2)]
        shown = f"{needle['keepResult']:.2f}" if needle else "pinned"
        rank_text = f"{rank}/{len(decisions)}" if rank else "-"
        top = f"{max(others):.2f}" if others else "-"
        print(
            f"{t['id']}  {t['kind']:<7} {needle_id:>4} {shown:>10} {rank_text:>7}  {top:>9}"
            f"  {counts[0]:>6} {counts[1]:>6} {counts[2]:>6}"
        )


if __name__ == "__main__":
    main(*sys.argv[1:4])
