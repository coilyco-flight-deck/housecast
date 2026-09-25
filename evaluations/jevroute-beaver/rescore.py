"""Rescore committed round rows against the current case labels, from the raw answers."""

import json
import sys
from pathlib import Path

import yaml

from housecast.jevroute.bench import score, summarize

cases_path, *round_dirs = sys.argv[1:]
split = Path(cases_path).stem.removeprefix("cases-")
labels = {c["q"]: c for c in yaml.safe_load(Path(cases_path).read_text())["cases"]}
for d in round_dirs:
    for f in sorted(Path(d).glob(f"{split}.run*.jsonl")):
        rows = [json.loads(line) for line in f.read_text().splitlines()]
        s = summarize([score(labels[r["q"]], r["raw"], 0.9) for r in rows])
        print(f"{Path(d).name} {f.stem}: pass {s['pass']} pass_any {s['pass_any']} cw {s['confident_wrong']}")
