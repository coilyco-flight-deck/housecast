"""Apply the tiered rule to committed no-server-pick raw answers (same request, new rule)."""

import json
import sys
from pathlib import Path

from housecast.jevroute.echorouter import score_tiered

run_dir, *general = sys.argv[1:]
for f in sorted(Path(run_dir).glob("*.run*.jsonl")):
    rows = [json.loads(line) for line in f.read_text().splitlines()]
    out = [score_tiered({**r, "server": "eco-game"}, r["raw"], set(general)) for r in rows]
    n = len(out)
    print(f"{f.stem}: right_route {sum(r['right_route'] for r in out)}/{n}"
          f"  direct_right {sum(r['direct_right'] for r in out)}"
          f"  direct_wrong {sum(r['direct_wrong'] for r in out)}"
          f"  contested {sum(r['contested'] for r in out)}")
