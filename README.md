# housecast

The roster framework for agent context. It reads roster data authored
as YAML (roles, personalities, boundaries, and the invariant), validates it,
resolves each role's personality meld and boundary allocation, derives the
identity primitives including each role's favorite color, and emits an
immutable bundle. It also runs and boards the behavior evaluations against what
it composed, which is what keeps the graded artifact and the shipped artifact
identical.

**Nothing ships yet.** This repository holds the catalog scaffold and no
product code. [`docs/FEATURES.md`](docs/FEATURES.md) is the inventory, and
`agent-compose#337` is the slice that moves the engine in.

## housecast and acompose

`acompose` is downstream of housecast, not its peer.

housecast owns the roster language and the engine. `acompose` renders the
bundle housecast emits into harness surfaces and launches them. Reading
housecast as an accessory, plugin, adapter, or helper to `acompose` inverts the
relationship the whole program exists to establish. The position housecast
holds relative to `acompose` is the position umbra holds relative to its own
downstream consumers.

## The name

A house cast is the resident standing company of a theatre: a fixed troupe held
by one house under one set of conventions, able to mount any role in its book.
`house` is the authority noun. `cast` carries both casting a play and casting
metal, and that second sense is the immutable bundle.

Two other readings of the string are live. Neither one is this project, and
both are named here rather than left to be discovered.

* **house plus forecast** - `housecast` also parses that way, and three of the
  four existing GitHub repositories under the string are dead housing-price
  forecasters. This engine forecasts nothing.
* **type casting** - `cast` is a live Python concept, so a Python reader lands
  on coercion for a beat before they land on the theatre. This engine does no
  type casting worth the name.

The name is locked in `agent-compose#330`, which carries the full search
record.

`housecast` unhyphenated is the repository, the import name, and the primary
distribution. `house-cast` is held defensively and never shipped.

## Quick start

```
git clone https://forgejo.coilysiren.me/coilyco-flight-deck/housecast.git
cd housecast
just pre-commit-install
just
```

`just` with no arguments lists every verb. `just test`, `just lint`,
`just format-check`, and `just typecheck` are the offline gates, and
`just pre-commit` runs the catalog validator suite over every tracked file.

## Layout

* `housecast/` - the package. A version and a docstring today.
* `tests/` - pytest suites mirroring the package.
* `docs/` - the inventory, and the design pages the compositor will bring.
* `.forgejo/workflows/` - the CI gate, running the same recipes as above.

## License

MIT. Kai Siren holds the copyright. See [`LICENSE`](LICENSE).

## See also

* [`AGENTS.md`](AGENTS.md) - agent-facing operating context for this repository.
* [`docs/FEATURES.md`](docs/FEATURES.md) - what ships today, which is nothing.
* [`.ward/ward.yaml`](.ward/ward.yaml) - catalog metadata for the cross-repo graph.
