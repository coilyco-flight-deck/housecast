# Presenting

`housecast grade present` serves a built deck to a room, taking anonymous votes.
## Two servers, because a flag is not a boundary

`serve` is the grader's and `present` is the room's, as separate processes, so
the only thing dividing a private critique from an audience is which one runs.
The tempting shape is one server with a mode. Nothing is authenticated for a
viewer, so a boolean would be the single thing between `/api/session` and a
room, and it cannot fail closed. Two commands can. `present` binds openly and
has no route returning a grading session, because it loads none.

## What the room may know, and when

A round unlocks one thing per state and **withholds** the rest rather than
sending everything and hiding it. Seeing a verdict before voting would spoil
the round and corrupt the split it produces.

* `commitments` - the commitments
* `case` - adds the prompt and the response
* `open` - adds a **count of votes cast**, never a direction
* `split` - adds the tally
* `reveal` - adds the label, critique, and evidence span

The count-not-direction rule lives in the API rather than a page's discipline.
A running split anchors later voters to the early ones, so the reading stops
being of the room and becomes one of whoever went first.

## What is authenticated, which is almost nothing

No viewer authenticates and none is identified. A vote carries a device token
the browser minted itself so re-voting replaces, and votes are discarded on
exit. `advance` and `back` need a token `present` prints on startup, because a
room that can close a vote is a live failure with an audience watching. That
thinness bounds the number: a phone and a laptop count twice, so the split
reads a room rather than being a statistic.

## See also

* [`deck.md`](deck.md) - the artifact it serves, and what it refuses to build.
