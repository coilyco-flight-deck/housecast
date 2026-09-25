"""Replay sirens-echo 6f413d5 matchVocab against eco questions and score argument fills.

Mirrors argextract.go: lowercase whole words, a message word may carry a trailing s or
es, the longest matching form wins, a tie between entries at that length declines.
"""

import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).parent
TOOL_ARG = {"find_trade": ("item", "name"), "get_market": ("item", "id"),
            "price_recipe": ("product", "id"), "get_currency": ("currency", "name")}


def words(text):
    return [w for w in re.split(r"[^\w]|_", text.lower()) if w]


def same(got, want):
    return got in (want, want + "s", want + "es")


def contains(ws, form):
    return any(all(same(ws[s + i], f) for i, f in enumerate(form))
               for s in range(len(ws) - len(form) + 1))


def match(message, entries):
    ws, best, best_len, tied = words(message), None, 0, False
    for e in entries:
        length = 0
        for form in [e["name"], e["id"], *e["aliases"]]:
            fw = words(form)
            if len(fw) > length and contains(ws, fw):
                length = len(fw)
        if length == 0:
            continue
        if length > best_len:
            best, best_len, tied = e, length, False
        elif length == best_len and e["id"] != best["id"]:
            tied = True
    return None if best_len == 0 or tied else best


def main(route_dir):
    items = json.loads((HERE / "items-vocab-736e8be.json").read_text())["entries"]
    expected = {c["q"]: c for c in yaml.safe_load((HERE / "expected-args.yaml").read_text())["cases"]}
    for split in ("dev", "holdout"):
        for n in (1, 2):
            rows = [json.loads(x) for x in (Path(route_dir) / f"{split}.run{n}.jsonl").read_text().splitlines()]
            tally = {"direct_right_arg_tools": 0, "filled_right": 0, "declined": 0,
                     "declined_correctly": 0, "filled_wrong": 0}
            wrong = []
            for r in rows:
                if not r["direct_right"] or r["tool"] not in TOOL_ARG:
                    continue
                tally["direct_right_arg_tools"] += 1
                exp = expected.get(r["q"], {})
                if TOOL_ARG[r["tool"]][0] == "currency":
                    got = None  # the offline currency vocabulary is empty
                    want = exp.get("currency")
                    want_ok = want is None
                else:
                    e = match(r["q"], items)
                    got, want = (e["name"] if e else None), exp.get("item")
                    want_ok = got == want
                if got is None:
                    tally["declined"] += 1
                    tally["declined_correctly"] += want is None
                elif want_ok:
                    tally["filled_right"] += 1
                else:
                    tally["filled_wrong"] += 1
                    wrong.append((r["q"], got, want))
            print(f"{split} run{n}: {tally} wrong={wrong}")


if __name__ == "__main__":
    main(sys.argv[1])
