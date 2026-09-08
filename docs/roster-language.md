# The roster language

What YAML housecast reads and what it refuses. The loader is `housecast/roster.py`, the checks are
`housecast/validate.py`, and `housecast/data/roster.yaml`'s header documents its field ancestry.

## Two loaders, one semantics

Ported from the Go engine's `internal/person`. Go parses KDL and housecast parses YAML, so the
loaders differ on purpose. The semantics must not, and `agent-compose#339` keeps the differential test alive.

## The types

* **`Roster`** - roles, personalities, boundaries, the invariant.
* **`Role`** - a charter, its meld, its boundary allocation, its seats, its favorite color, and
  whether it is archived.
* **`Personality`** - a trait definition carrying its own `Emblem` and `Voice`.
* **`Boundary`** - see [`role-boundaries.md`](role-boundaries.md).
* **`Scoped`**, **`Adjacent`** - the two qualifiers on an allocation.
* **`Act`** - one thing an attribute requires a seat to run, carried by roles, personalities, and
  boundaries. `tool` is separate from `text` so a coverage check reads the tool without parsing
  English, and the tool must appear in the text so the two cannot drift apart.

## Archived roles

`archived: true` retires a seat from selection and keeps it whole, and absent means live. It still
validates, holds its boundary allocation, carries its identity and art, and answers adjacency edges other
roles declare onto it, so archiving does not disturb the in-degree the graph balances. What stops is the derived
board: `evalkit.matrix.active_roles` filters role order, the boundary-owner slot guards itself because `owner`
arrives unfiltered, and the seat is the subject of no challenge. Deleting loses the charter and the art.

## What it refuses

`validate()` runs before anything resolves, so a bad roster fails at load rather than at emission:
`check_boundary_ownership`, `check_personality_bindings`, `check_definition_set`, `check_personality_colors`,
`check_skill_frontmatter`, `check_copy_contract`. Their messages quote the Go tests closely enough to find it.

## See also

* `just fields`, and [`minimal-roster.yaml`](../housecast/data/minimal-roster.yaml) - every field, and the smallest roster that loads.
* [`composition.md`](composition.md) - what the engine does with a loaded roster.
