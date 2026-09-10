"""Did the charter-ambiguity score predict grader disagreement?

The instrument `housecast#7317` pre-registers. It reads the scores the director
seat committed before grading began and the disagreement report `housecast grade
disagreement` produced after, and applies the retirement rule to the join.

It does not compute disagreement itself. That definition belongs to
`housecast.grade.agreement`, which decides what a missing grade means, and a
second copy here would be a second answer to the same question.

Three decisions, in the order `power.py` ranked them:

* **trend** - Cochran-Armitage across 0, 1 and 2, one-sided. Primary, because it
  spends every scored case rather than the two end strata, and `power.csv` puts
  it at 0.603 against Fisher's 0.357 in the reference cell.
* **contrast** - one-sided Fisher exact on the 0-vs-2 table. Reported because
  the 0-vs-2 comparison is the gate's own wording.
* **direction** - whether the 2s simply disagreed more often. Reported and never
  decisive: under the null it fires 0.237 to 0.556 of the time depending only on
  how many 2s got assigned, so on its own it retires by coin flip.

Run `--shuffle` for the negative control. Scores permuted against the same
grades must not fire, and a rule that fires there is measuring the board rather
than the criterion.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import random
import sys

ALPHA = 0.05
Z_ONE_SIDED = 1.645  # normal critical value at ALPHA, matching power.py
SCORES = (0, 1, 2)


def fisher_one_sided(a: int, b: int, c: int, d: int) -> float:
    """P(as extreme or more) for [[a,b],[c,d]], testing a/(a+b) > c/(c+d)."""
    row1, row2 = a + b, c + d
    col1 = a + c
    total = row1 + row2
    if row1 == 0 or row2 == 0 or col1 == 0 or col1 == total:
        return 1.0
    hi = min(row1, col1)
    return sum(
        math.comb(row1, k) * math.comb(row2, col1 - k) / math.comb(total, col1)
        for k in range(a, hi + 1)
    )


def cochran_armitage(counts: list[tuple[int, int]]) -> float:
    """One-sided z for a linear trend in disagreement across 0, 1, 2."""
    total = sum(n for _, n in counts)
    events = sum(d for d, _ in counts)
    if total == 0 or events in (0, total):
        return 0.0
    p = events / total
    mean = sum(s * n for s, (_, n) in zip(SCORES, counts, strict=True)) / total
    num = sum(s * (d - n * p) for s, (d, n) in zip(SCORES, counts, strict=True))
    var = p * (1 - p) * sum(n * (s - mean) ** 2 for s, (_, n) in zip(SCORES, counts, strict=True))
    return num / math.sqrt(var) if var > 0 else 0.0


def normal_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2))


def read_scores(path: pathlib.Path) -> dict[str, int]:
    """Case id to 0/1/2. An unscored row is dropped and reported, never read as 0."""
    scored: dict[str, int] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            raw = (row.get("score") or "").strip()
            if raw == "":
                continue
            if raw not in {"0", "1", "2"}:
                raise ValueError(f"{row['case']}: score {raw!r} is not 0, 1 or 2")
            scored[row["case"]] = int(raw)
    return scored


def read_disagreement(path: pathlib.Path) -> dict[str, bool]:
    """Case id to disagreed, over the cases every grader reached."""
    report = json.loads(path.read_text())
    return {case["id"]: not case["agreed"] for case in report["per_case"] if "agreed" in case}


def tabulate(scores: dict[str, int], disagreed: dict[str, bool]) -> list[tuple[int, int]]:
    """(disagreed, total) per score level, over cases carrying both."""
    counts = {s: [0, 0] for s in SCORES}
    for case, score in scores.items():
        if case not in disagreed:
            continue
        counts[score][1] += 1
        counts[score][0] += int(disagreed[case])
    return [(counts[s][0], counts[s][1]) for s in SCORES]


def verdict(counts: list[tuple[int, int]]) -> dict[str, object]:
    (d0, n0), _, (d2, n2) = counts
    z = cochran_armitage(counts)
    trend_p = normal_sf(z)
    contrast_p = fisher_one_sided(d2, n2 - d2, d0, n0 - d0) if n0 and n2 else 1.0
    rate0 = d0 / n0 if n0 else float("nan")
    rate2 = d2 / n2 if n2 else float("nan")
    return {
        "z": z,
        "trend_p": trend_p,
        "contrast_p": contrast_p,
        "rate0": rate0,
        "rate2": rate2,
        "direction": bool(n0 and n2 and rate2 > rate0),
        "trend_fires": z >= Z_ONE_SIDED,
        "contrast_fires": contrast_p <= ALPHA,
        # Pre-registered rule: the criterion survives only when the primary test
        # clears alpha and the effect points the way the hypothesis said.
        "retained": bool(z >= Z_ONE_SIDED and n0 and n2 and rate2 > rate0),
    }


def render(counts: list[tuple[int, int]], result: dict[str, object]) -> str:
    lines = ["score  disagreed  compared  rate"]
    for score, (d, n) in zip(SCORES, counts, strict=True):
        rate = f"{d / n:.4f}" if n else "n/a"
        lines.append(f"{score:>5}  {d:>9}  {n:>8}  {rate:>6}")
    total = sum(n for _, n in counts)
    lines.append(f"total  {sum(d for d, _ in counts):>9}  {total:>8}")
    lines.append("")
    lines.append(f"trend     z = {result['z']:+.4f}  p = {result['trend_p']:.4f}  (primary)")
    lines.append(f"contrast  0 vs 2 fisher one-sided p = {result['contrast_p']:.4f}")
    lines.append(
        f"direction 2s {'above' if result['direction'] else 'not above'} 0s: "
        f"{result['rate2']:.4f} vs {result['rate0']:.4f}"
    )
    lines.append("")
    lines.append(
        "VERDICT: criterion RETAINED" if result["retained"] else "VERDICT: criterion RETIRED"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Charter-ambiguity score against disagreement.")
    parser.add_argument("--scores", type=pathlib.Path, required=True, help="filled scoring sheet")
    parser.add_argument(
        "--disagreement",
        type=pathlib.Path,
        required=True,
        help="`housecast grade disagreement --format json` output",
    )
    parser.add_argument(
        "--shuffle",
        type=int,
        metavar="N",
        help="negative control: permute scores N times and report how often the rule fires",
    )
    parser.add_argument("--seed", type=int, default=20260910)
    args = parser.parse_args(argv)

    scores = read_scores(args.scores)
    disagreed = read_disagreement(args.disagreement)
    joined = [case for case in scores if case in disagreed]
    if not joined:
        print(
            "no case carries both a score and a completed grade from every grader", file=sys.stderr
        )
        return 1

    counts = tabulate(scores, disagreed)
    result = verdict(counts)
    print(f"scored {len(scores)}, compared {len(disagreed)}, joined {len(joined)}\n")
    print(render(counts, result))

    if args.shuffle:
        rng = random.Random(args.seed)
        values = [scores[case] for case in joined]
        fired = 0
        for _ in range(args.shuffle):
            rng.shuffle(values)
            permuted = dict(zip(joined, values, strict=True))
            if verdict(tabulate(permuted, disagreed))["retained"]:
                fired += 1
        print(
            f"\nnegative control: {fired}/{args.shuffle} permutations retained "
            f"({fired / args.shuffle:.4f}), nominal {ALPHA}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
