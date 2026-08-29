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

## Two grading surfaces, one set of rules

`annotate` grades in a terminal. `serve` grades in a browser. They are the same
loop against the same committed YAML, and every rule lives in one place per
surface rather than being restated: a label must belong to the case's label set,
a deduction needs a critique, an evidence span must appear verbatim in the
output, and the file is rewritten after **every** decision so an interrupted
session keeps its work.

The browser changes one thing that matters. `annotate` asks the grader to retype
the span and loops until it matches, because a retyped quote gets edited by the
hand retyping it. A page anchors the span by selection, so that failure cannot
occur and the verbatim check stops being a typo guard. It stays in place as the
guard against a page sending a span from the wrong case.

`annotate` is not deleted. It keeps working until the page has carried one real
board end to end.

## The public and private halves of one run

`export` projects a run one way onto a display surface. `serve` is the other
direction, and the split between them is a safety property rather than a
layering preference.

* A **built artifact** embeds the public export. It has no critique, no
  evidence, and no way to write a label, so a file opened on a projector cannot
  leak one. That is enforced by absence rather than by a flag.
* **`serve`** holds the private payload in memory for as long as the process
  runs, and writes decisions back to `annotations.yaml`.

`serve` binds loopback and refuses anything else unless `--expose` says
otherwise, because the payload it hands the page carries the words the grader
wrote for herself. It refuses rather than warns, matching how the exporter
treats a public target.

`serve` deliberately does **not** run the exporter's secret scan. That scan
guards a public projection. Refusing to show a grader her own board because a
response quotes an email address would be the wrong instrument pointed at the
wrong target.

## Schema ids are a wire format

`aos-eval.board.v1`, `aos-eval.attributes.v1`, and `aos-eval.export.v1` keep
their names after the port. They identify a file format that committed evidence
already carries, not the package that reads it. Renaming them would make the
loader reject boards it wrote itself, so they move only in a format migration
with a version bump behind it.

**A new format takes this package's name.** `housecast.grading.v1`, which
`serve` hands the page, is the first. The rule above is a reason not to rename
an id that committed evidence carries, and it is not a reason to mint more
`aos-eval.*` ids for a package called housecast.

## Committed evidence ages out of the loader

`evaluations/pilot/ops-board-2026-08-12` and its regraded sibling predate the
current `Challenge`. They carry `role`, `trait`, and `boundary` where the schema
now wants `entity` and `attribute`, so neither `export` nor `serve` can load
them and both fail the same way.

**That is correct and they are left alone.** A committed dataset is the record
of what was true when the run executed, and rewriting it to match today is the
exact failure a committed dataset exists to prevent. Anything pointing a new
tool at real evidence should use `evaluations/reflow-v3/board-2026-08-26`, which
is 91 cases on the current vocabulary.

## The profile is the deployment's

`Profile` exists so a deployment declares its own test types without this schema
growing a branch per consumer. `evalkit/profile.py` is agent-compose's, carrying
`boundary`, `role-fit`, `personality`, and `voice`. sirens-echo declares its own.
Adding a test type is a profile edit, never a schema edit.

## See also

* [`FEATURES.md`](FEATURES.md) - the shipped capability inventory.
* [`../README.md`](../README.md) - what housecast is and how it pairs with acompose.
