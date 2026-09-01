# The evaluation workflow

The order the verbs run in, and what a grader is deciding in each test type.
[`evaluation.md`](evaluation.md) is what each piece is. This is what to run.

## The sequence

Nine verbs, and the seams between them are where work stops and resumes.

1. `just evalkit-matrix` - print the board the roster implies. Read it.
2. `just evalkit-coverage` - the gap against `challenges.yaml`. Write the
   missing prompts before running anything, or the run measures a partial board.
3. `just evalkit-prompts` - compose one compiled bundle per role into
   `.evalkit/prompts/<role>.md`. Frontier tier, because it is the only one every
   role supports and the tier does not change selected context.
4. `just evalkit-smoke` - one live request, so a broken transport surfaces here
   rather than eleven minutes into a board.
5. `just evalkit-run` - the board through Inspect, **unscored**. `EVAL_EPOCHS`
   defaults to 5, and the other four are a failure-spread estimate at no
   grading cost.
6. `just evalkit-filter` - the Inspect log becomes the dataset to grade.
7. `just evalkit-annotate` - or `just grade-serve RUN` for the browser. A human
   decides. This is the only irreplaceable step.
8. `just evalkit-taxonomy` - cluster the critiques into ranked failures.
9. `just evalkit-export`, then `just grade-seal` or `just grade-deck` - the
   one-way display payload, and the artifact that carries it.

A run repeats without regrading, and a board regrades without re-running. Step 5
and step 7 are separate commands because that seam is the point.

## What each test type decides

* **boundary** - binary, 50 words, paired. The in-half acts, the out-half hands
  over. The pair is the scoring unit, never the half. See [`grading.md`](grading.md).
* **role-fit** - binary, 50 words. Does the seat claim work it owns, and route
  work it does not, against the named adjacent.
* **personality** - fit, 100 words. Did the trait fire, composed alongside the
  rest of the meld rather than alone.
* **voice** - fit, 100 words. Reaches for its own register and refuses the
  borrowed one, and performs every tell the meld carries.
