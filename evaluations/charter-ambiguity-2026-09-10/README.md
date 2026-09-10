# Charter ambiguity as a split-test selection criterion: the pre-registration

Written 2026-09-10 for `teable:coilyco-flight-deck/housecast#7317`, at housecast
`7b9f8cc`. Nothing here is a result about the criterion. The board it applies to
has not been scored and cannot be graded yet, and that ordering is the whole
point of the row.

## Why a pre-registration and not a run

Divergence went into production unfalsified. It ranked 105 cases, `housecast#7009`
selected its split-test pairs from that ranking, and only afterwards did anyone
ask whether it predicted anything. It did not: AUC 0.4608, permutation p = 0.85,
and 6 of 12 worst-half hits against a coin flip of 6.0. The replacement criterion
gets its falsification test written down first, with the numbers that decide it
fixed before any of them exist.

## The criterion

Set by the director seat. A case is a split-test candidate when the behaviour it
demands is not settled by a single unambiguous sentence in the governing charter.

* **0** - one verbatim sentence decides it
* **1** - a general rule decides it but has to be applied
* **2** - two sources bear on it and disagree, or no sentence reaches it

The hypothesis is that disagreement between graders rises with the score.

## The order of operations, which is the substance

1. The director seat fills `scoring-sheet.csv`, reading the charter, before any
   response has been graded and before any grader has been recruited.
2. The filled sheet is committed. That commit is the pre-registration.
3. The board runs and two graders grade it, writing `annotations.<grader>.yaml`.
4. `housecast grade disagreement --format json` produces the disagreement report.
5. `validity.py` joins the two and prints a verdict it cannot influence.

A score assigned once the grades are visible is not a prediction, and that is
exactly the mistake that produced the row this one replaces.

## The retirement rule, which is not the gate's literal wording

The gate says the criterion is retired if the 2s do not disagree more than the
0s. Taken literally that is a bare direction check, and `power.py` measures what
a direction check is worth on a board this size. Under the null it fires between
0.237 and 0.556 of the time, depending on nothing but how many 2s the scoring
happened to produce:

    n2     p0   direction   fisher    trend
     5   0.05       0.237    0.013    0.060
    10   0.10       0.474    0.024    0.061
    21   0.10       0.454    0.021    0.053
    35   0.05       0.556    0.015    0.050

So a criterion that predicts nothing survives its own falsification test about
half the time, and the survival rate is a property of the scoring rather than of
the world. That is not a falsification test.

The rule `validity.py` applies instead, fixed here before any data:

* **Primary** - a one-sided Cochran-Armitage trend test across 0, 1 and 2 at
  alpha 0.05, `z >= 1.645`. It spends every scored case rather than the two end
  strata.
* **And** the direction has to hold, so a significant downward trend cannot be
  read as support.
* **Reported, never decisive** - the one-sided Fisher exact on the 0-vs-2 table,
  because that contrast is the gate's own wording, and the bare direction check,
  because a reader will want it.

Trend beats Fisher everywhere in `power.csv` and is correctly sized where Fisher
is not. Under the null, trend fires 0.049 to 0.065 against a nominal 0.05, while
Fisher's discreteness holds it to 0.010 to 0.029 and it pays for that in power.

## What this board can and cannot detect

At a 10% share of 2s and a base disagreement rate of 0.10, from `power.csv`:

    lift    p2   direction   fisher    trend
     1.5  0.15       0.650    0.070    0.154
     2.0  0.20       0.770    0.143    0.287
     3.0  0.30       0.913    0.357    0.603
     4.0  0.40       0.975    0.591    0.836

**This design detects a large effect and nothing smaller.** At a doubling of the
disagreement rate the primary test finds it 29% of the time. A null result at a
2x lift is therefore uninformative and must not be reported as the criterion
failing. Only a 3x lift or better puts power past a half, and even there a miss
happens 40% of the time.

Raising the share of 2s helps less than it looks. Going from 10 of 105 to 35 of
105 moves power at 3x from 0.603 to 0.706, because the 0 stratum shrinks as the
2 stratum grows. The board size is the binding constraint, not the split.

## The instrument is checked, and it is calibrated

`test_validity.py` asserts every statistic against a value computed off the
machine: Fisher against the tea-tasting table's 17/70, the trend z against a
hand-computed 10 / sqrt(40/9), the retirement rule against counts constructed to
fire and not to fire. 16 tests, all passing, run before the instrument saw a real
score. It is not in `testpaths`, which stops at the two packages, so run it with
`just test evaluations/charter-ambiguity-2026-09-10/test_validity.py`.

The first `--shuffle` negative control came back at 0.0730 against a nominal
0.05, which is 4 binomial SE high and looked like the normal approximation going
anti-conservative at eight cases in the top stratum. It is not. `calibration.py`
measured both candidates and `calibration.txt` carries the run:

    unconditional, 20000 independent draws, no true effect
      retained (trend AND direction)  0.0542
      trend alone                     0.0544
      direction alone                 0.4524

    conditional, 200 realizations x 500 permutations
      mean 0.0560   median 0.0540   5th 0.0300   95th 0.0860

The rule is correctly sized. A single `--shuffle` run conditions on one
realization's disagreement vector, and those land anywhere from 0.020 to 0.108,
with 15.5% of them at or above the 0.0730 that raised the question. Read a
`--shuffle` number against that 0.030-to-0.086 band and not against 0.05.

The `direction alone` line is the same finding as the power table, arriving by a
second route: 0.4524 under a null with no effect in it.

## Where I was wrong

`PREDICTION.md` was written before `power.py` ran and it missed twice. Fisher
power at the reference cell came in at 0.357 against a predicted ceiling of
0.35, and the trend test at 0.603 against a predicted 0.40 to 0.55. The
direction check's false-keep rate landed inside the predicted 0.35 to 0.50 at
the reference cell and outside it at the edges, which the prediction did not
anticipate varying at all.

A third miss came later. I predicted the 0.0730 negative control meant an
anti-conservative approximation, at 0.06 to 0.09. The measurement says 0.0542.

## What is blocked, and what this row does not need

Disagreement needs two graders and this board has one, so no verdict can be
produced here. `housecast#7160` holds the recruitment behind Kai naming a
community, and `housecast#7158` is blocked at the same gate.

None of that blocks the scoring. Steps 1 and 2 need a charter and a reader, and
running them now is what makes the eventual measurement a prediction rather than
a description. **The scoring is the unblocked half and it belongs to the director
seat.**

## Files

* `PREDICTION.md` - written before `power.py` ran, kept so the numbers cannot be
  read back as the ones I expected.
* `power.py` - simulates the three decision rules over stratum sizes and rates.
  Writes `power.csv`, 60 cells, 20000 trials each.
* `power.txt` - the run, verbatim stdout.
* `power.csv` - the operating envelope this design has to fit inside.
* `scoring_sheet.py` - derives the sheet through `evalkit.matrix`, so a roster
  change moves it. Regenerate against the roster the next run actually uses.
* `scoring-sheet.csv` - 119 derived cases, 105 authored, `score` and `why` empty.
* `validity.py` - the analysis instrument and the retirement rule. Reads the
  filled sheet and the disagreement report, and computes no disagreement of its
  own, because `housecast.grade.agreement` owns that definition.
* `test_validity.py` - 16 known-answer checks on it.
* `calibration.py` and `calibration.txt` - what the rule does when nothing is
  there to find.
