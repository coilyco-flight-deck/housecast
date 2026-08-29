# Features

Coarse inventory of the major capabilities housecast ships. Bugfixes, refactors,
and internal plumbing never earn an entry here.

## Shipped

* **The composition engine.** Reads a roster as YAML, validates it, resolves each
  role's meld and boundary allocation, derives the identity primitives including
  each role's favorite color, and emits an immutable bundle in either delivery
  mode. See [`composition.md`](composition.md) and [`identity.md`](identity.md).
* **The roster language.** `housecast/data/roster.yaml` carries roles,
  personalities, boundaries, and the invariant. See
  [`roster-language.md`](roster-language.md) and
  [`role-boundaries.md`](role-boundaries.md).
* **A roster projection.** `housecast roster` emits the `person.json` shape
  downstream tools read, which is what removed Go from the eval path.
* **evalkit, the board runner.** Derives the challenge board from the roster,
  runs it through Inspect against Agent Proxy, and hands datasets to the
  annotator. See [`evaluation.md`](evaluation.md).
* **The grading half.** `housecast grade` under the `eval` extra: schema, pairing,
  annotation, failure taxonomy, one-way export. See [`grading.md`](grading.md).
* **A browser grading surface.** `housecast grade serve` holds one run open for a
  grader on loopback under the rules the terminal loop enforces, and refuses to
  bind past loopback. See [`grading-surfaces.md`](grading-surfaces.md).
* **The room-facing half.** `housecast grade deck` builds a scanned, slug-free
  deck and `housecast grade present` serves it with anonymous voting, a separate
  process so the divide between a private critique and a room is which command
  runs. See [`presenting.md`](presenting.md) and [`deck.md`](deck.md).

## Not shipped

No PyPI distribution. Consumers install from Forgejo with uv. The name claim is
`agent-compose#347` and waits on Kai. The Go engine in agent-compose still
composes, and is deleted under `agent-compose#339`, blocked separately.

## See also

* [`../README.md`](../README.md) - what housecast is and how it pairs with acompose.
* [`../AGENTS.md`](../AGENTS.md) - agent-facing operating context.
