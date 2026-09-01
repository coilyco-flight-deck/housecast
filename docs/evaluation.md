# Evaluation

The board runner, `evalkit`. It derives a challenge board from the roster, runs
it through Inspect against Agent Proxy, and hands datasets to the annotator.

**Stub.** The structure is settled and the prose is not.

## The board is derived, not maintained

`evalkit/matrix.py` builds it through `derive()`. Boundary allocations, role fit,
personality, and voice each produce their own challenge shapes. Adding a boundary
or changing an adjacency changes the output, which is what stops the board
falling behind the roster it tests. A human writes the prompt into each derived
challenge, and `challenges.yaml` is where those land.

## Coverage

`just evalkit-coverage` reports what the two sides do not share: cases derived with no
prompt, prompts no longer derived, authored cases with no annotation, and graded records
whose case is gone. It exits zero, because the grader is a human and blocking would put
every roster edit behind an annotation session. `[tool.evalkit.coverage]` in
`pyproject.toml` carries `blocking` and `retired_runs`: configuration, not a patch.

## The runner

`evalkit/task.py` is the Inspect task. Its epochs are what a repetition count was,
and it runs **unscored** because the scorer is a human: a board is regradable
without re-running and repeatable without regrading. Grading is [`grading.md`](grading.md).
Transport goes through Agent Proxy, checked by `agent_proxy_configured()` up front.

## The projections

`evalkit/roster.py` projects the person snapshot into the entity roster the shared
annotator renders, spelling out `owns`, `defers`, `scoped`, and traits there rather
than in the schema. `evalkit/profile.py` declares the test types: a profile edit.

## See also

* [`evaluation-workflow.md`](evaluation-workflow.md) - the verb order, and what each type decides.
* [`role-boundaries.md`](role-boundaries.md) - the allocations the board derives from.
