"""Can the next board detect the charter-ambiguity effect at all?

`housecast#7317` pre-registers a criterion and a retirement rule: score every
case 0/1/2 for charter ambiguity before grading, then retire the criterion if
the 2s do not disagree more than the 0s. That rule is a direction check. This
asks what a direction check is worth on a board this size, and what a test with
a stated alpha would cost instead.

Nothing here reads the board. It is a simulation over stratum sizes and rates
that nobody has measured yet, so read it as the operating envelope the design
has to fit inside, not as a result about roles.
"""

from __future__ import annotations

import csv
import math
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).parent

BOARD = 105  # authored cases on the 2026-09-08 board; the reachable count
TRIALS = 20000
ALPHA = 0.05
SEED = 20260910

# Share of the board scoring 2, then 1. The rest score 0. The director seat
# scored 7 cases while forming the hypothesis and 2 of those were 2s, which is
# far too few to estimate a share from, so the grid spans plausible ones.
SHARE_2 = (0.05, 0.10, 0.20, 0.33)
SHARE_1 = 0.30
BASE = (0.05, 0.10, 0.20)  # disagreement rate among the 0s
LIFT = (1.0, 1.5, 2.0, 3.0, 4.0)  # multiplier applied to the 2s; 1.0 is the null


def fisher_one_sided(a: int, b: int, c: int, d: int) -> float:
    """P(as extreme or more) for the 2x2 [[a,b],[c,d]], testing a/(a+b) > c/(c+d).

    Hypergeometric tail, exactly as `scipy.stats.fisher_exact(alternative='greater')`
    computes it, written out because this directory carries no scipy.
    """
    row1, row2 = a + b, c + d
    col1 = a + c
    total = row1 + row2
    lo = max(0, col1 - row2)
    hi = min(row1, col1)

    def term(k: int) -> float:
        return math.comb(row1, k) * math.comb(row2, col1 - k) / math.comb(total, col1)

    return sum(term(k) for k in range(a, hi + 1)) if a >= lo else 1.0


def cochran_armitage(counts: list[tuple[int, int]], scores: tuple[float, ...]) -> float:
    """One-sided z for a linear trend in proportion across ordered levels.

    `counts` is (disagreed, total) per level in score order. Returns the z
    statistic; positive means disagreement rises with the score.
    """
    total = sum(n for _, n in counts)
    events = sum(d for d, _ in counts)
    if total == 0 or events in (0, total):
        return 0.0
    p = events / total
    mean_score = sum(s * n for s, (_, n) in zip(scores, counts, strict=True)) / total
    num = sum(s_ * (d - n * p) for s_, (d, n) in zip(scores, counts, strict=True))
    var = (
        p
        * (1 - p)
        * sum(n * (s_ - mean_score) ** 2 for s_, (_, n) in zip(scores, counts, strict=True))
    )
    return num / math.sqrt(var) if var > 0 else 0.0


def draw(n: int, p: float, rng: random.Random) -> int:
    return sum(1 for _ in range(n) if rng.random() < p)


def cell(n0: int, n1: int, n2: int, p0: float, p1: float, p2: float, rng: random.Random) -> dict:
    """One (stratum sizes, rates) cell, TRIALS times, three decision rules."""
    direction = fisher = trend = 0
    for _ in range(TRIALS):
        d0, d1, d2 = draw(n0, p0, rng), draw(n1, p1, rng), draw(n2, p2, rng)
        if d2 / n2 > d0 / n0:
            direction += 1
        if fisher_one_sided(d2, n2 - d2, d0, n0 - d0) <= ALPHA:
            fisher += 1
        # 1.645 is the one-sided normal critical value at alpha = 0.05.
        if cochran_armitage([(d0, n0), (d1, n1), (d2, n2)], (0.0, 1.0, 2.0)) >= 1.645:
            trend += 1
    return {
        "direction": direction / TRIALS,
        "fisher": fisher / TRIALS,
        "trend": trend / TRIALS,
    }


def main() -> int:
    rng = random.Random(SEED)
    rows = []
    for share2 in SHARE_2:
        n2 = round(BOARD * share2)
        n1 = round(BOARD * SHARE_1)
        n0 = BOARD - n1 - n2
        for p0 in BASE:
            for lift in LIFT:
                p2 = min(1.0, p0 * lift)
                p1 = (p0 + p2) / 2  # the 1s sit halfway, the trend test's own assumption
                out = cell(n0, n1, n2, p0, p1, p2, rng)
                rows.append(
                    {
                        "share_2": share2,
                        "n0": n0,
                        "n1": n1,
                        "n2": n2,
                        "p0": p0,
                        "p2": round(p2, 4),
                        "lift": lift,
                        "null": lift == 1.0,
                        "direction": round(out["direction"], 4),
                        "fisher": round(out["fisher"], 4),
                        "trend": round(out["trend"], 4),
                    }
                )

    out_path = HERE / "power.csv"
    with out_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"board {BOARD}, {TRIALS} trials per cell, alpha {ALPHA}, seed {SEED}")
    print(f"wrote {out_path.name}, {len(rows)} cells\n")

    nulls = [r for r in rows if r["null"]]
    print("under the null (lift 1.0), how often each rule fires:")
    print(f"{'n2':>4} {'p0':>6} {'direction':>10} {'fisher':>8} {'trend':>8}")
    for r in nulls:
        print(
            f"{r['n2']:>4} {r['p0']:>6} {r['direction']:>10.3f} "
            f"{r['fisher']:>8.3f} {r['trend']:>8.3f}"
        )

    print("\npower at p0 = 0.10, by share of 2s and lift:")
    print(f"{'n2':>4} {'lift':>5} {'p2':>6} {'direction':>10} {'fisher':>8} {'trend':>8}")
    for r in rows:
        if r["p0"] == 0.10 and not r["null"]:
            print(
                f"{r['n2']:>4} {r['lift']:>5} {r['p2']:>6} {r['direction']:>10.3f} "
                f"{r['fisher']:>8.3f} {r['trend']:>8.3f}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
