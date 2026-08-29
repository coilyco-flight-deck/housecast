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

## Two servers, because a flag is not a boundary

`serve` is the grader's. `present` is the room's. They are **separate
processes**, so the only thing dividing a private critique from an audience is
which one is running.

The tempting shape is one server with a mode. It is wrong here: nothing is
authenticated for a viewer, so a mode boolean would be the single thing between
`/api/session` and a room, and a boolean cannot fail closed. Two commands can.

* **`serve RUN_DIR`** - loopback, refuses to bind further without `--expose`,
  serves the private payload, writes annotations.
* **`present DECK`** - binds openly by default, serves a built deck, takes
  anonymous votes. It has no route that returns a grading session, because it
  never loads one.

## A deck is built, not live-read

`present` takes a **deck file** rather than a run directory. That is the point.
A deck is built deliberately, scanned, and looked at before a room sees it, so
no request path reaches a live grading session.

`housecast grade deck ROUNDS --run RUN_DIR --out DECK` joins two sources:

* **The case** comes from committed evidence: the prompt, the response, and the
  reveal, which is Kai's label, her critique, and her evidence span.
* **The commitments block** is authored prose. It belongs to the exercise
  content rather than to this repository, and the builder only requires that it
  is present.

Three refusals at build time, because the failure is discovered in a room
otherwise: a round naming a case the run does not hold, a round on an ungraded
case (there is nothing to reveal), and a round with no commitments (there is
nothing to grade against).

**Every slug is withheld by construction.** `entity`, `test_type`, `attribute`,
`pair_id`, `half`, `seed`, and `required_tool` never enter a deck, so a retired
slug cannot reach a recorded stream. Suppressing them in a page would be a rule.
Leaving them out of the payload is a guarantee.

**The reveal is included on purpose and therefore scanned.** A public export
withholds critique and evidence, and a deck carries them because showing them is
the round's whole point. So the exporter's secret scan runs over the deck at
build **and again at load**, since a file can be hand-edited between the two.

## What the room may know, and when

`present` unlocks one thing per state and **withholds** the rest rather than
sending everything and hiding it. A viewer reading the response body early gets
nothing, which matters because seeing the verdict before voting both spoils the
round and corrupts the split it produces.

* `commitments` - the commitments.
* `case` - adds the prompt and the response.
* `open` - adds a **count of votes cast**, never a direction.
* `split` - adds the tally.
* `reveal` - adds Kai's label, critique, and evidence span.

The count-not-direction rule lives here rather than in the page's discipline. A
running split anchors every later voter to the early ones, so the reading stops
being of the room and becomes a reading of whoever went first.

## What is authenticated, which is almost nothing

No viewer authenticates and no viewer identity is created. A vote carries a
device token the browser minted for itself, which exists so re-voting replaces
rather than accumulates. Votes live in memory and are discarded when the process
exits.

**The presenter's control is the one gated thing.** `advance` and `back` need a
token that `present` prints to stderr on startup, because a room that can skip
rounds or close a vote is a live failure with an audience watching.

That thinness is deliberate and it bounds what the number means. A phone and a
laptop count twice, so the split is a reading of a room rather than a statistic.
Presenting it as data would be the same failure this whole body of work
describes.

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
