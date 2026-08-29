# The deck

`housecast grade deck ROUNDS --run RUN_DIR --out DECK` builds the artifact a
room meets.

## Built, not live-read

`present` takes a deck file rather than a run directory, which is what removes
any request path from a live grading session to a projector. A deck is built
deliberately, scanned, and looked at before an audience sees it.

It joins two sources: the case, from committed evidence, and a commitments
block, which is authored prose belonging to the exercise content rather than to
this repository.

## Three refusals at build time

The alternative is discovering them in a room.

* a round naming a case the run does not hold
* a round on an ungraded case, so there is nothing to reveal
* a round with no commitments, so there is nothing to grade against

## Every slug is withheld by construction

`entity`, `test_type`, `attribute`, `pair_id`, `half`, `seed`, and
`required_tool` never enter a deck, so a retired slug cannot reach a recorded
stream. Suppressing them in a page is a rule. Leaving them out of the payload is
a guarantee.

## The reveal is scanned because it is public on purpose

A deck carries the critique a public export withholds, because showing it is the
round's whole point. So the exporter's secret scan runs at build **and again at
load**: a file can be hand-edited between the two.

## See also

* [`presenting.md`](presenting.md) - the server that reads it.
* [`grading-evidence.md`](grading-evidence.md) - the public and private halves.
