# Evaluation

The board runner, `evalkit`. It derives a challenge board from the roster, runs
it through Inspect against Agent Proxy, and hands datasets to the annotator.
Four modules point here from their own docstrings, so this page is the one that
closes those references.

**This page is a stub.** The structure is settled and the prose is not.

## The board is derived, not maintained

`evalkit/matrix.py` builds the board from the roster through `derive()`.
Boundary allocations, role fit, personality, and voice each produce their own
challenge shapes. Adding a boundary or changing an adjacency changes the
output, which is the property that keeps the board honest: it cannot quietly
fall behind the roster it is meant to test.

A human writes the prompt into each derived challenge. `challenges.yaml` is
where those land.

## The runner

`evalkit/task.py` is the Inspect task. It replaces a hand-rolled fan-out with
`inspect eval`, and Inspect's epochs are what a repetition count used to be.

It runs **unscored**, because the scorer is a human. That seam is deliberate:
a board can be regraded without re-running it, and a run can be repeated without
regrading it. Grading is [`grading.md`](grading.md).

Transport goes through Agent Proxy, configured by `AGENTPROXY_BASE_URL`.
`agent_proxy_configured()` checks that before a run rather than failing partway
through one.

## The projections

`evalkit/roster.py` projects the person snapshot into the entity roster the
shared annotator renders. The shared layer prints an entity's charter and knows
nothing about how this deployment composes one, so `owns`, `defers`, `scoped`,
and traits are spelled out in the projection rather than in the shared schema.

`evalkit/profile.py` declares this board's own test types: `boundary`,
`role-fit`, `personality`, and `voice`. A deployment states its own types so the
shared schema does not grow a branch per consumer. Adding a test type is a
profile edit, never a schema edit.

## Still to write

* The workflow end to end, tying together the `scripts/eval-*.sh` verbs.
* What each of the four test types is actually looking for, with a real
  challenge as the example.
* How `evalkit/filter.py` selects, and what evidence a reader can open.
* Which committed runs under `evaluations/` are current and which are frozen
  records, because the directory does not say.
* The negative-control and ceiling-effect discipline this board is supposed to
  hold itself to.

## See also

* [`grading.md`](grading.md) - what happens to a run after it finishes.
* [`role-boundaries.md`](role-boundaries.md) - the allocations the board derives from.
* [`FEATURES.md`](FEATURES.md) - the shipped capability inventory.
