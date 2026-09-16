"""Exact two-tailed sign-test power for a held-out split.

Answers the question the holdout design depends on: at a given holdout size, what
can a result report at all? A unanimous split clears 0.05 from six upward, but the
first size where anything short of unanimity clears is nine. Between those, the
only reportable outcome is "every held-out case moved", so a holdout carved from
a ten-to-twenty-five case board is not a weak control, it is an inert one.
"""

from __future__ import annotations

from math import comb


def sign_p(k: int, n: int) -> float:
    """Two-tailed exact sign test: probability of k or more of n under p=0.5."""
    return min(1.0, 2 * sum(comb(n, i) for i in range(k, n + 1)) / 2**n)


def best_split(n: int) -> tuple[float, float]:
    """Unanimous p at size n, and the best p available without unanimity."""
    partial = [sign_p(k, n) for k in range(n // 2 + 1, n)]
    return sign_p(n, n), min(partial) if partial else 1.0


def main() -> None:
    print(f"{'n':>4}  {'unanimous':>9}  {'non-unan.':>9}  verdict")
    for n in range(3, 13):
        unanimous, partial = best_split(n)
        if unanimous >= 0.05:
            verdict = "inert, cannot reach 0.05 on any outcome"
        elif partial >= 0.05:
            verdict = "unanimous only"
        else:
            verdict = "discriminates"
        print(f"{n:>4}  {unanimous:>9.4f}  {partial:>9.4f}  {verdict}")


if __name__ == "__main__":
    main()
