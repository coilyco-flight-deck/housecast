"""Rescore committed jevroute-servers rows against current labels, from the raw answers."""

import json
import sys
from pathlib import Path

import yaml

from housecast.jevroute.servers import answer, judge

cases_path, *dirs = sys.argv[1:]
labels = {c["q"]: c for c in yaml.safe_load(Path(cases_path).read_text())["cases"]}
stem = Path(cases_path).stem
for d in dirs:
    for f in sorted(Path(d).glob(f"{stem}.run*.jsonl")):
        tot = {"server_any": 0, "server_cw": 0, "e2e_any": 0}
        for r in map(json.loads, f.read_text().splitlines()):
            c = labels[r["q"]]
            srv = judge(*answer(r["raw_server"], "server"), c["server"], 0.9)
            tool = judge(*answer(r.get("raw_tool", {}), "tool"), c["tool"], 0.9)
            tot["server_any"] += srv["any"]
            tot["server_cw"] += srv["cw"]
            right = srv["win"] in c["server"]
            tot["e2e_any"] += right and srv["any"] and (tool["any"] or srv["win"] == "no_server")
        print(f"{Path(d).name} {f.stem}: {tot}")
