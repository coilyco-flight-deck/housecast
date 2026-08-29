# The roster language

What YAML housecast reads, and what it refuses. The loader is
`housecast/roster.py`, the checks are `housecast/validate.py`, and the roster
the engine composes is `housecast/data/roster.yaml`, whose header documents its
own field ancestry.

**This page is a stub.** The structure is settled and the prose is not.

## Two loaders, one semantics

The language was ported from the Go engine's `internal/person`. Go parses KDL
and housecast parses YAML, so the loaders differ on purpose. What must not
differ is the semantics either one applies once the file is in memory, and
`agent-compose#339` keeps the differential test alive until the Go engine is
deleted.

## The types

`housecast/roster.py` defines the whole surface:

* **`Roster`** - the document. Roles, personalities, boundaries, the invariant.
* **`Role`** - a charter plus its ordered personality meld, boundary
  allocation, seats, and favorite color.
* **`Personality`** - a trait definition, carrying its own `Emblem` and `Voice`.
* **`Boundary`** - a capability that a role owns, defers, or holds within a
  scope. See [`role-boundaries.md`](role-boundaries.md).
* **`Seat`** - a harness a role can be launched into.
* **`Scoped`**, **`Adjacent`** - the two qualifiers on a boundary allocation.
* **`RosterError`** - every refusal, raised with the offending path.

## What it refuses

`validate()` runs before anything is resolved, so a bad roster fails at load
rather than at emission. The checks are named for what they hold:
`check_boundary_ownership`, `check_personality_bindings`,
`check_definition_set`, `check_personality_colors`, `check_skill_frontmatter`,
and `check_copy_contract`.

Their messages quote the Go tests closely enough that a reader can find the Go
check from a Python failure. That is deliberate and survives the Go deletion.

## Still to write

* A worked example of a minimal valid roster, field by field.
* The full field reference, generated from the dataclasses rather than typed
  out, so it cannot drift.
* What `check_copy_contract` actually enforces, which is the least obvious of
  the six.
* Word and paragraph counting, which reproduce `roleSkillBodyWordCount` and
  `briefingParagraphCount`, and why those caps exist.

## See also

* [`role-boundaries.md`](role-boundaries.md) - how a boundary is allocated.
* [`composition.md`](composition.md) - what the engine does with a loaded roster.
* [`FEATURES.md`](FEATURES.md) - the shipped capability inventory.
* [`../README.md`](../README.md) - what housecast is and how it pairs with acompose.
