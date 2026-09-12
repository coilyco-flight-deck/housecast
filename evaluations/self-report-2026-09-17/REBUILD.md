# Rebuild of dimension 01, after the footer parser lost a row

`CORRECTION.md` says what is wrong with `fidelity.py` as merged at `91de8ece`
and refuses to fix it at speed. This page is the fix, and it opens with what was
predicted before any of it ran, because the previous three readings of this
defect each looked finished and then moved.

Tracked as `teable:coilyco-flight-deck/housecast#7566`.

## Predictions, written 2026-09-12 19:47Z before the rebuild ran

Every figure below is EXPECTED. Nine came to me as another seat's measurement
and one is my own reading of the renderer, so none of them is evidence yet. The
point of writing them here first is that a criterion invented after the output
is seen fits whatever came back.

* Footer rows across the 47 replies: **41**, glyphs hammer 40 and book 1.
* Footer runs parsed from the reply text: **70**. From the `disclosed` field
  as the corpus carries it: **68**.
* Records where those two disagree: **1**, at ordinal 45.
* Replies carrying a non-empty disclosure: **15** before the rebuild and 15
  after, so the board's population does not move and no cell changes from a
  non-score to a scorable one.
* Ordinal 45's book row: label `skill`, 2 runs, against a trace of
  `skills/read_skill` 2 and `tvmaze/search_tv_show` 2.
* Ordinal 36 stays the one real failure: footer 4 against trace 2 on
  `gbif/search_species`.
* The rebuilt aggregate: footer runs **70** against in-window trace calls
  **68**, disagreeing by exactly the size of ordinal 36.

## One prediction of my own, which disagrees with the record

`teable:coilyco-flight-deck/housecast#7566` settled on mapping a book row to
the skill-read class. I predict that mapping is **wrong in the general case**,
and that the corpus is too small to show it.

Read at `coilyco-gaming/sirens-echo` `main` `28d9b4a`: `toolDisclosureLine`
emits the book glyph whenever `call.Detail != ""`, and `Detail` is set in two
places rather than one. `skilltool.go` sets it to a skill's display name, and
`trackeradapter.go` sets it to a tracker record key on filing, commenting and
closing. So a book row means "this call carried a display value", and a reader
who maps the glyph straight onto the skill-read tool has hardcoded the only
case this corpus happens to contain.

The same file gives the join that does work. `proxy.go` sets
`mcp.tool.skill` on the tool span from that same `Detail`, so the trace knows
which calls rendered as book rows and under which real tool name. A book row
should be matched on that attribute, and a cell whose evidence lacks it should
be reported unresolvable rather than guessed in either direction.
