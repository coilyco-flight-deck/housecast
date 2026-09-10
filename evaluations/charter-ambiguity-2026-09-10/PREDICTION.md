# Written before `power.py` ran

Stamped `2026-09-10T07:00:01Z`, `date -u`, at housecast `7b9f8cc`. This file
exists so the power numbers below cannot be read back as the ones I expected.

The gate on `teable:coilyco-flight-deck/housecast#7317` says the criterion is
"retired if the 2s do not disagree more than the 0s". That is a direction check,
not a significance test. Three numbers decide whether it is worth running.

1. **False-keep rate of the bare direction check under the null.** With no real
   effect, `p2_hat > p0_hat` is close to a coin flip, so I expect the criterion
   to survive its own falsification test between **0.35 and 0.50** of the time.
   Ties at small n push it below 0.5 rather than above.
2. **Power of a one-sided Fisher exact 0-vs-2 contrast**, at n=105, a 10% share
   of 2s (n2 about 10), base disagreement 0.10, and a 3x lift to 0.30. I expect
   **under 0.35**.
3. **Power of a Cochran-Armitage trend test** across all three levels at the same
   cell, which spends every case rather than two strata. I expect it higher than
   the Fisher contrast, **0.40 to 0.55**.

If 1 lands where I expect, the gate as written retires or keeps by coin flip and
needs replacing before the board is scored, not after.
