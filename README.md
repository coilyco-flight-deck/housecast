# housecast

Agent context, cast from one roster

Change what a role may do and the evaluation that checks it moves with it.
`agent-compose` owns the roster language now: it reads roster data authored as
YAML, validates it, resolves each role's personality meld and boundary
allocation, derives the identity primitives including each role's favorite
color, and composes the immutable bundle. housecast runs and boards the
behavior evaluations against exactly what `agent-compose catalog snapshot`
reports, which is what keeps the graded artifact and the shipped artifact
identical.

housecast shipped the composition engine itself for a stretch (moved in under
`agent-compose#337`, moved back out under `housecast#8041` once the Go engine
caught up), and only the eval half remains here.
[`docs/FEATURES.md`](docs/FEATURES.md) is the inventory. The name `housecast`
is held on PyPI as a 0.0.1 placeholder under `agent-compose#347`, now closed.
The release train that turns a `housecast-v*` tag into a real upload is wired,
and until the first tag runs it, consumers install from Forgejo.

## housecast and agent-compose

housecast is downstream of `agent-compose`, not its peer. `agent-compose` owns
the roster language, resolves every role's meld and boundary allocation, and
composes the bundle. housecast reads what `agent-compose catalog snapshot`
reports and grades behavior against it - it authors and vendors none of the
roster itself. Reading `agent-compose` as an accessory, plugin, adapter, or
helper to housecast inverts the relationship this repository now holds.

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
agent-compose catalog snapshot --out /tmp/person.json
```

Projecting the roster and composing a role's bundle are both agent-compose's
job now, not this repository's - housecast#8041.

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
extra when the consumer needs the board runner rather than the base package alone.
Once a `housecast-v*` tag has run the train in
[`docs/publishing.md`](docs/publishing.md), `pip install housecast` is the
shorter path.

## Layout

* `housecast/` - the eval and grading package: `digest.py`, `grade/`,
  `mcpeval/`, `mcp/`. No roster loading lives here anymore - that is
  `agent-compose catalog snapshot`'s job.
* `evalkit/` - the board runner, which reads `agent-compose catalog
  snapshot`'s JSON so the graded artifact and the shipped artifact stay
  identical.
* `challenges.yaml` and `evaluations/` - the board and its committed evidence.
* `scripts/` - the eval workflow, with no Go anywhere in it.

## License

MIT. Kai Ase Siren holds the copyright. See [`LICENSE`](LICENSE).

## See also

* [`AGENTS.md`](AGENTS.md) - agent-facing operating context for this repository.
* [`docs/FEATURES.md`](docs/FEATURES.md) - what ships today.
