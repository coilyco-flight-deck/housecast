# Identity primitives

What the engine derives about a role beyond what the roster states: the identity
card, the instruction document, and the favorite color. `housecast/render.py`
and `housecast/color.py` own this between them.

**This page is a stub.** The structure is settled and the prose is not.

## The identity card

`identity_card()` renders the compact role identity a harness shows: purpose,
personality meld, voice, boundaries, seats, and the favorite color. Every
literal in the renderer is copied from the Go `RenderRoleIdentityCard` rather
than paraphrased, because byte-identity with the Go renderer is the acceptance
bar. `thousands()` exists only to reproduce Go's digit grouping.

## The instruction document

`instructions()` is the other half, joining the role skill and its ordered
personality skills into the document an agent actually reads.
`skill_body_sizes()` reports what each contributes, which is what lets a card
state its own doctrine byte count.

## The favorite color

`housecast/color.py` is a port of `internal/color/color.go`, and only the
compose path came across: `parse_hex()`, `to_oklab()`, `from_oklab()`,
`legible()`, and `favorites()`. Shimmer, nearest-match, ANSI, and background
tooling stay in Go, because no bundle depends on them.

The solve is joint rather than per-role. `favorites()` picks colors for the
whole roster at once so that no two roles land too close together, and
`legible()` holds the band that keeps every result readable against the
surfaces it gets rendered on.

## Still to write

* Why OKLab rather than a simpler space, which is a real decision with a real
  reason and is currently recorded nowhere.
* The legible band: its actual bounds and what they were tuned against.
* What happens to the solve when a role is added, and whether existing roles
  are allowed to move.
* A rendered example card, checked against the Go renderer.

## See also

* [`composition.md`](composition.md) - where these are derived in the pipeline.
* [`roster-language.md`](roster-language.md) - what the roster states directly.
* [`FEATURES.md`](FEATURES.md) - the shipped capability inventory.
