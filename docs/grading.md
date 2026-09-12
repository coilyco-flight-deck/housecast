# Grading

The grading half, `housecast.grade`, and the `housecast grade` command that drives it. Ported from
`agentic-os/aos-eval`, which is deleted once its last consumer moves.

## What it is

Committed YAML in, human decisions and one-way display payloads out. It holds no runner and no model
client. The runner is `evalkit`, which reaches Inspect and Agent Proxy, and the seam between them is
deliberate: a board can be regraded without re-running it, and a run repeated without regrading it.
`housecast grade help` is the long form, and each verb ends with the next.

It rides the `eval` extra with `evalkit`, because a consumer composing a bundle should not pay for a
grading stack, and `housecast grade` says so rather than failing on an import error when the extra is
absent. `test_no_runner_reaches_the_dependency_set` pins the half that matters: no runner reaches the
**core** dependency set whatever the extra carries.

## The profile is the deployment's

`Profile` exists so a deployment declares its own test types without this schema growing a branch per
consumer. `evalkit/profile.py` is agent-compose's, carrying `boundary`, `role-fit`, `personality`,
`voice`, and [`grounding`](grading-grounding.md). sirens-echo declares its own. Adding one is a
profile edit plus a deriver, never a schema edit: `evalkit/matrix.py` unpacks the test types by
arity, so a new one fails loudly rather than deriving nothing. A profile also names the field the
board map groups by, because one subject over many cases is otherwise a single row.

## Schema ids are a wire format

`aos-eval.board.v1`, `aos-eval.attributes.v1`, and `aos-eval.export.v1` keep their names after the
port. They identify a file format committed evidence already carries, not the package that reads it,
and renaming them would make the loader reject boards it wrote itself, so they move only in a format
migration with a version bump behind it. That is a reason not to rename an id, never a reason to mint
more `aos-eval.*` ids for a package called housecast: a new format takes this package's name, and
`housecast.grading.v1`, which `serve` hands the page, is the first.

## See also

* [`grading-surfaces.md`](grading-surfaces.md) - the two loops and the evidence halves.
* [`grading-non-scores.md`](grading-non-scores.md) - a cell that is not a verdict.
* [`grading-page.md`](grading-page.md) - the page `--static` mounts, and its delivery.
