"""Both 0.9 metrics per round from committed raw answers: strict (winner confidence) and any."""

import json
import sys
from pathlib import Path

ROUNDS = Path(__file__).parent / "rounds"
SPLITS = ("dev", "holdout", "sealed")


def rescore(row: dict) -> tuple[bool, bool, bool]:
    tool = row["raw"].get("answers", {}).get("tool", {})
    probs, conf = tool.get("probabilities") or {}, tool.get("confidence") or 0
    if not probs:
        return False, False, False
    win = max(probs, key=probs.get)
    mass = sum(v for k, v in probs.items() if k in row["ok"])
    return win in row["ok"] and conf >= 0.9, mass >= 0.9, win not in row["ok"] and conf >= 0.9


for name in sys.argv[1:]:
    cells, tot = [], [0, 0, 0, 0]
    for split in SPLITS:
        files = sorted((ROUNDS / name).glob(f"{split}.run*.jsonl"))
        if not files:
            cells.append(f"{split} -")
            continue
        rows = [json.loads(line) for f in files for line in f.read_text().splitlines()]
        s, a, w = (sum(rescore(r)[i] for r in rows) for i in range(3))
        cells.append(f"{split} {s / len(rows):.0%} / {a / len(rows):.0%} cw{w}")
        tot = [tot[0] + s, tot[1] + a, tot[2] + w, tot[3] + len(rows)]
    all_ = f"ALL {tot[0] / tot[3]:.1%} / {tot[1] / tot[3]:.1%} cw{tot[2]} n={tot[3]}"
    print(f"{name:34} " + "  ".join(cells) + "  " + all_)
