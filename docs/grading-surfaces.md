# Grading surfaces

Two surfaces, one set of rules. `annotate` grades in a terminal and `serve` grades in a browser.

## One set of rules

The same loop against the same committed YAML, each rule in one place per surface:

* a label must belong to the case's label set
* a deduction needs a critique
* an evidence span must appear verbatim in the output
* the file is rewritten after **every** decision, so an interrupted session keeps its work

## What the browser changes

One thing that matters. `annotate` asks the grader to retype the span and loops until it matches, because a
retyped quote gets edited by the hand retyping it. A page anchors the span by selection, so that failure
cannot occur and the verbatim check stops being a typo guard. It stays in place as the guard against a page
sending a span from the wrong case. `serve` hands the page `housecast.grading.v1`, carrying the profile's
own keystrokes so one-key grading survives the move.

## Two graders on one board

`--grader kai` writes `annotations.kai.yaml` rather than the shared `annotations.yaml`, so two testers stop
overwriting each other. The name is validated as lowercase letters, digits and hyphens because it becomes a
filename, and it is written into the file under a `grader` key because a filename is the first thing a copy
or an export changes. `grade disagreement` takes `--annotations` once per grader, reads that key ahead of
the filename, and rates only the cases every grader reached: one nobody finished is incomplete rather than
folded in, and nothing compared reports no rate rather than agreement. Required `--tester` declares the
study's roster, so a glob catching a calibrated grader refuses rather than counting. Counted files are named.

## annotate is not deleted

It keeps working until the page has carried one real board end to end.

## See also

* [`grading.md`](grading.md) - what the grading half is.
* [`grading-evidence.md`](grading-evidence.md) - why `serve` binds loopback.
* [`presenting.md`](presenting.md) - the room-facing deck and its server.
