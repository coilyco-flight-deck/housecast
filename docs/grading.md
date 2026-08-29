# Grading

The grading half, `housecast.grade`, and the `housecast grade` command that
drives it. Ported here from `agentic-os/aos-eval`, which is deleted once its
last consumer moves.

## What it is

Committed YAML in, human decisions and one-way display payloads out. It holds no
runner and no model client. The runner is `evalkit`, which reaches Inspect and
Agent Proxy, and the seam between them is deliberate: a board can be regraded
without re-running it, and a run can be repeated without regrading it.

    housecast grade help

is the long form. Every verb ends with the next one to run.

## Why it lives in the eval extra

The engine core installs with a YAML parser and nothing else, because a consumer
composing a bundle should not pay for a grading stack. `housecast.grade` and
`evalkit` both ride `housecast[eval]`, and `housecast grade` says so rather than
failing on an import error when the extra is absent.

`test_no_runner_reaches_the_dependency_set` pins the half of that which matters:
no runner reaches the **core** dependency set, whatever the extra carries.

## Schema ids are a wire format

`aos-eval.board.v1`, `aos-eval.attributes.v1`, and `aos-eval.export.v1` keep
their names after the port. They identify a file format that committed evidence
already carries, not the package that reads it. Renaming them would make the
loader reject boards it wrote itself, so they move only in a format migration
with a version bump behind it.

## The profile is the deployment's

`Profile` exists so a deployment declares its own test types without this schema
growing a branch per consumer. `evalkit/profile.py` is agent-compose's, carrying
`boundary`, `role-fit`, `personality`, and `voice`. sirens-echo declares its own.
Adding a test type is a profile edit, never a schema edit.

## See also

* [`FEATURES.md`](FEATURES.md) - the shipped capability inventory.
* [`../README.md`](../README.md) - what housecast is and how it pairs with acompose.
