# housecast

Agent context, cast from one roster

Change what a role may do and the evaluation that checks it moves with it, in
the same commit. housecast reads roster data authored
as YAML (roles, personalities, boundaries, and the invariant), validates it,
resolves each role's personality meld and boundary allocation, derives the
identity primitives including each role's favorite color, and emits an
immutable bundle. It also runs and boards the behavior evaluations against what
it composed, which is what keeps the graded artifact and the shipped artifact
identical.

The engine and the eval runner both live here now, moved out of agent-compose
under `agent-compose#337`. [`docs/FEATURES.md`](docs/FEATURES.md) is the
inventory. The name `housecast` is held on PyPI as a 0.0.1 placeholder under
`agent-compose#347`, now closed. The release train that turns a `housecast-v*`
tag into a real upload is wired, and until the first tag runs it, consumers
install from Forgejo.

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

Two other readings of the string are live, and neither one is this project.

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
just sync
just compose --role director --out /tmp/bundle
```

`just` with no arguments lists every verb. `just check` is the offline gate:
lint, format check, types, and tests in one recipe.

## Installing it elsewhere

No release is on PyPI yet, only the reserved name. Depend on it from Forgejo
with uv:

```toml
[project]
dependencies = ["housecast"]

[tool.uv.sources]
housecast = { git = "https://forgejo.coilysiren.me/coilyco-flight-deck/housecast.git", tag = "housecast-v0.1.0" }
```

That is the same shape the estate already uses for `aos-eval`. Add the `eval`
extra when the consumer needs the board runner rather than the engine alone.
Once a `housecast-v*` tag has run the train in
[`docs/publishing.md`](docs/publishing.md), `pip install housecast` is the
shorter path.

## Layout

* `housecast/` - the engine. Roster loading, validation, meld and boundary
  resolution, the OKLab favorite-color solve, and bundle emission.
* `housecast/data/roster.yaml` - the roster the engine composes.
* `evalkit/` - the board runner, which travels with the engine so the graded
  artifact and the shipped artifact stay identical.
* `challenges.yaml` and `evaluations/` - the board and its committed evidence.
* `scripts/` - the eval workflow, with no Go anywhere in it.

## License

MIT. Kai Ase Siren holds the copyright. See [`LICENSE`](LICENSE).

## See also

* [`AGENTS.md`](AGENTS.md) - agent-facing operating context for this repository.
* [`docs/FEATURES.md`](docs/FEATURES.md) - what ships today.
