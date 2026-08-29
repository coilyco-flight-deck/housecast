# The grading page, payloads and delivery

How [`grading-page.md`](grading-page.md) gets data, and the test proving it needs no network.

## Two payloads, one renderer

It reads whichever it finds, and the renderer never learns which it got.

* `housecast.grading.v1` from `GET /api/session` - the private half, plus the
  profile's own keystrokes.
* `aos-eval.export.v1` embedded in the file, from `grade export` - the public
  half, unless built with `--include-private`.

An adapter normalises each into one view model, because a path exercised in one
delivery mode is untested in the others. The export drops empty fields, so
`critique`, `evidence`, `label`, `half`, and `pair_id` arrive as absent keys.
Its `pairs` holds only pairs with a graded half, so cards group from the cases
on the same key and an ungraded pair still gets a card.

## No build step, and a file path

The private half must never reach a distributed artifact. `serve` enforces that
by binding loopback, and the page by having nothing that could bake a payload
in. A bundler is where that mistake gets made, so there is none and the tracked
file holds `null` in its export slot.

`servedOverHttp()` gates the fetch on `location.protocol`, so from `file:` the
page makes no request at all. The acceptance test is the corrected one on
`coilysiren/inbox#472` `#issuecomment-79631`, run with a fresh profile and
`--host-resolver-rules="MAP * ~NOTFOUND"` so every hostname fails rather than
trusting a switched-off radio: 63 cards, 28 pairs, 91 map cells out of a public
export, zero critique blocks, and no critique text in the file.

## Sealing

`grade seal RUN --out board.html` writes the export into a **copy** of the page.
It refuses to write over the tracked file, which keeps holding `null`, and rides
`export`'s own refusal rather than adding a second gate. `--include-private`
seals the critique, and that artifact must never reach a projector.
