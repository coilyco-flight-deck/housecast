# Presenting

The room-facing half. `housecast grade deck` builds the artifact and
`housecast grade present` serves it to an audience.

## Two servers, because a flag is not a boundary

`serve` is the grader's and `present` is the room's, as **separate processes**,
so the only thing dividing a private critique from an audience is which one is
running.

The tempting shape is one server with a mode. It is wrong here: nothing is
authenticated for a viewer, so a mode boolean would be the single thing between
`/api/session` and a room, and a boolean cannot fail closed. Two commands can.

`present` binds openly by default and has no route that returns a grading
session, because it never loads one.

## A deck is built, not live-read

`present` takes a **deck file** rather than a run directory, which is what
removes any request path from a live grading session to a projector.

`housecast grade deck ROUNDS --run RUN_DIR --out DECK` joins the case, from
committed evidence, to a commitments block, which is authored prose belonging to
the exercise content rather than to this repository.

It refuses three rounds at build time, because the alternative is discovering
them in a room: one naming a case the run does not hold, one on an ungraded case
(nothing to reveal), and one with no commitments (nothing to grade against).

**Every slug is withheld by construction.** `entity`, `test_type`, `attribute`,
`pair_id`, `half`, `seed`, and `required_tool` never enter a deck, so a retired
slug cannot reach a recorded stream. Suppressing them in a page is a rule.
Leaving them out of the payload is a guarantee.

**The reveal is included on purpose and therefore scanned.** A deck carries the
critique that a public export withholds, because showing it is the round's whole
point, so the exporter's secret scan runs at build **and again at load**: a file
can be hand-edited between the two.

## What the room may know, and when

A round unlocks one thing per state and **withholds** the rest rather than
sending everything and hiding it. A viewer reading the response body early gets
nothing, and seeing a verdict before voting would both spoil the round and
corrupt the split it produces.

* `commitments` - the commitments
* `case` - adds the prompt and the response
* `open` - adds a **count of votes cast**, never a direction
* `split` - adds the tally
* `reveal` - adds the label, critique, and evidence span

The count-not-direction rule lives in the API rather than in the page's
discipline. A running split anchors every later voter to the early ones, so the
reading stops being of the room and becomes a reading of whoever went first.

## What is authenticated, which is almost nothing

No viewer authenticates and no viewer identity is created. A vote carries a
device token the browser minted for itself so re-voting replaces rather than
accumulates, and votes live in memory and are discarded when the process exits.

**The presenter's control is the one gated thing.** `advance` and `back` need a
token `present` prints on startup, because a room that can close a vote is a
live failure with an audience watching.

That thinness bounds what the number means. A phone and a laptop count twice, so
the split is a reading of a room rather than a statistic, and presenting it as
data would be the failure this body of work exists to describe.

## See also

* [`grading.md`](grading.md) - what the grading half is.
* [`grading-evidence.md`](grading-evidence.md) - the public and private halves.
* [`grading-surfaces.md`](grading-surfaces.md) - the terminal and browser loops.
