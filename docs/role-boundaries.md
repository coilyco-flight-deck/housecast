# Role boundaries

A boundary is a capability the roster allocates across roles. Every role either
owns it, defers it, or holds it within a stated scope, and no boundary is left
unallocated. `evalkit/matrix.py` points here, because the challenge board is
derived from these allocations rather than hand-maintained.

**This page is a stub.** The structure is settled and the prose is not.

## The three allocations

* **Owns** - the role is the one that acts. Exactly one role owns a boundary.
* **Defers** - the role hands the action to whoever owns it, and says so rather
  than acting.
* **Holds within a scope** - the role may act, but only inside a `Scoped` grant
  the roster spells out. The scope is prose in the roster and it is load-bearing.

`check_boundary_ownership` in `housecast/validate.py` is what keeps the
allocation total and the ownership single.

## Why the board is derived from them

`evalkit/matrix.py` turns allocations into unwritten challenges through
`boundary_challenges`, `scoped_grants`, and `owner_behaviour`. Adding a boundary
or changing an adjacency changes that output. A human then writes the prompt
into each one, so the board is a consequence of the roster and never drifts
away from it silently.

## Adjacency

`Adjacent` marks a boundary a role sits next to without holding. It is the
qualifier that makes a near-miss legible, and it feeds its own challenge shape.

## Still to write

* The boundary catalogue itself, one entry per boundary, with its owner and
  every scoped holder.
* What makes a scope statement good, drawn from the ones that survived grading.
* How a deferral is supposed to read in a transcript, since that is what the
  boundary challenges actually score.
* The relationship between a boundary and a personality meld, which the
  identity card renders together but the roster keeps separate.

## See also

* [`roster-language.md`](roster-language.md) - the YAML these are authored in.
* [`evaluation.md`](evaluation.md) - how allocations become a challenge board.
* [`FEATURES.md`](FEATURES.md) - the shipped capability inventory.
