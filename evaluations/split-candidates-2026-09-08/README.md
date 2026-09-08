# Split-candidate shortlist, n=5

Run taken 2026-09-08 for `teable:coilyco-flight-deck/housecast#7153`, which asks
for the per-case data `housecast#7009` selects its four case pairs from.

## What was run

* **Board** - the derived board, printed by `just evalkit-matrix` from the roster.
* **Subject** - `evaluation/deepseek-v4-pro` through Agent Proxy at `ser8:8080/v1`,
  commodity tier, matching the triple `lore-method-agent-eval` records.
* **Epochs** - 5, the method's item-analysis repetition.
* **Unscored** - `--no-score`, because the scorer is a human. Nothing here is a grade.

## Three findings the row should carry

### The board is 119 cases, not 78

`lore-method-agent-eval` at `097853f0` records "78 cases, roughly 40 minutes of
grading". `just evalkit-matrix` at housecast `06cbc04` prints **119**: 56 boundary,
21 role-fit, 14 personality, 14 voice, 14 grounding, across 7 active roles at 17
each. The method's figure is stale by 41 cases, and grading time scales with it.

### 16 of the 119 cannot carry any count

`just evalkit-coverage` reports 119 derived against 105 authored. Sixteen derived
cases have no prompt written, and `evalkit.inspect_bridge.to_inspect` refuses an
unwritten challenge outright, so they cannot run at all:

    advocate-gnd-in     advocate-gnd-out    director-gnd-in     director-gnd-out
    frontend-gnd-in     frontend-gnd-out    gamedev-gnd-in      gamedev-gnd-out
    platform-fit-analyst                    platform-gnd-in     platform-gnd-out
    science-gnd-in      science-gnd-out     sysadmin-fit-analyst
    sysadmin-gnd-in     sysadmin-gnd-out

Fourteen of the sixteen are the whole `grounding` test type, which is derived and
never authored. Two more (`platform-fit-sysadmin`, `sysadmin-fit-director`) are
authored but no longer derived, so the run covers 105 cases of which 103 are on
the board. **Maximum reachable coverage is 103 of 119.**

### The method does not produce a pass count out of 5

The row's gate asks that "every case on the derived board carries a pass count out
of 5". The method it cites says something narrower. Quoting `lore-method-agent-eval`
at `097853f0` verbatim:

> Item analysis at n=5 keeps cases failing 1 to 4 times: Kai grades one response,
> the other four give a free variance estimate.

One graded response per case, four ungraded repeats. The code agrees:
`housecast.grade.dataset.build` takes an `epoch` argument and puts **one** epoch's
text in front of the annotator, leaving the rest in the log as evidence. And
`housecast/grade/dataset.py` records why no machine stands in:

> There is no mechanical scorer here. On agent-compose's first graded board a regex
> tier disagreed with the human on every case where either deviated from a pass, so
> it was removed rather than tuned.

So a pass count out of 5 needs five human judgments per case. At 103 cases that is
515 of them, against a method that sizes one pass over 78 cases at roughly 40
minutes. I did not produce pass counts, and I did not grade: the row said not to,
and there is no instrument here that would.

## The run

    105 challenges x 5 epochs = 525 samples, 17m19s
    3,467,420 tokens [in 98,291, cache read 3,160,704, out 208,425]
    0 blank, 0 errored
    log: .evalkit/logs/2026-09-08T17-41-01-00-00_board_UwWJYbdDsCTL8GkZ3s95Bk.eval

The 2026-09-01 board is the comparator: same shape, same subject, 525 samples,
20m29s, 3,416,562 tokens. This run is 3m10s faster on 50,858 more tokens, and it
returned no blank where that one returned one (`platform-sev-out`, epoch 1). Both
are ungraded.

The log is not committed. `.gitignore` carries `.evalkit/`, and the log is 7.7MB.
It lives only on the host that ran it, which is the same gap the 2026-09-01 record
names. What is committed here is everything derived from it.

## What I measured instead of a pass count

The method's own sentence says the four extra epochs are "a free variance
estimate". This is that estimate, computed with no grader: for each case, the
mean pairwise Jaccard distance between the five responses' token sets, plus
length dispersion. `dispersion.py` is the whole instrument.

**It ranks, and it does not discriminate well.**

    divergence   min 0.5313   max 0.8682   mean 0.7400   sd 0.0629
    mean words   min 22       max 69       mean 38.3
    length cv    min 0.0186   max 0.3827   mean 0.1351

    by test type   boundary     n=56  mean 0.7382  sd 0.0551
                   personality  n=14  mean 0.7509  sd 0.0537
                   role-fit     n=21  mean 0.7702  sd 0.0633
                   voice        n=14  mean 0.6913  sd 0.0690

Every case lands in a 0.34-wide band with an sd of 0.063, so the extremes separate
and the middle does not. Read the head and the tail; do not read rank 40 against
rank 55.

**The length confound is weak.** `pearson(divergence, mean_words) = -0.1102` and
`pearson(divergence, length_cv) = +0.2603`, so the ordering is not simply short
answers scoring high. That is the one negative control I could run.

**The one I could not run is validity.** `just evalkit-coverage` reports 103
ungraded and 0 graded, and the 2026-09-01 dataset says "Nothing here is scored".
There is no human-graded case anywhere in this repository, so I cannot show that
lexical instability predicts grader disagreement. The link between them is an
assumption rather than a measured result. Treat the ranking as a hypothesis about
where to look, not as evidence about where graders will split.

## Most divergent cases

     0.8682  science-fit-gamedev      role-fit
     0.8535  gamedev-fit-frontend     role-fit
     0.8475  frontend-fit-gamedev     role-fit
     0.8382  science-per-empirical    personality
     0.8290  science-fit-within       role-fit
     0.8289  frontend-sev-in          boundary
     0.8285  sysadmin-sec-in          boundary
     0.8250  advocate-sec-in          boundary

## Most divergent pairs

The method scores a boundary as a pair, never a half, so these are the unit
`housecast#7009` picks from. Mean of the two halves, 28 pairs total.

     0.8097  platform-sev   worst half in
     0.7942  platform-mlb   worst half in
     0.7937  frontend-sev   worst half in
     0.7895  sysadmin-sec   worst half in
     0.7881  science-sev    worst half out
     0.7854  platform-bfs   worst half out
     0.7832  advocate-sec   worst half in

## What to do with this before Friday

A pass count out of 5 is not reachable in the window. The method's own pass is:
grade one response per case, and let the other four show the spread. At 105 cases
that is roughly 55 minutes by the method's own 78-case, 40-minute rate.

`annotation-queue.csv` orders all 105 cases by divergence descending. Grading in
that order does two things at once: it front-loads the cases most likely to be
unstable, so a session that runs out of time has still covered them, and it
produces the first graded data this board has ever had, which is what would let
anyone check whether this proxy predicts anything. The ranking does not need to be
valid to be a useful queue order, and grading it in that order is what would
settle whether it is.

## Files

* `dispersion.py` - the instrument. Reads the Inspect log, writes the two CSVs.
* `dispersion.csv` - 105 rows, per case.
* `dispersion-pairs.csv` - 28 rows, per boundary pair, ranked.
* `annotation-queue.csv` - all 105 cases in grading order.
