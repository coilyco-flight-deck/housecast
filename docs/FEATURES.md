# Features

Coarse inventory of the major capabilities housecast ships.

## Shipped

* **The composition engine.** Reads a roster as YAML, resolves each role's meld and boundary
  allocation, derives the identity primitives, and emits an immutable bundle. See
  [`composition.md`](composition.md), [`identity.md`](identity.md).
* **The roster language.** `housecast/data/roster.yaml` carries roles, personalities, boundaries,
  acts, and the invariant. See [`roster-language.md`](roster-language.md),
  [`role-boundaries.md`](role-boundaries.md).
* **Attribute acts.** Every role, personality, and boundary side names three things a seat can
  actually run, rendered onto the identity card as `## Run`. A boundary's acts follow the side the
  seat holds rather than the owner's. See [`roster-language.md`](roster-language.md).
* **A roster projection.** `housecast roster` emits the `person.json` shape downstream tools read,
  which is what removed Go from the eval path.
* **evalkit, the board runner.** Derives the board from the roster and runs it through Inspect
  against Agent Proxy. See [`evaluation.md`](evaluation.md).
* **The grading half.** `housecast grade` under the `eval` extra: schema, pairing, annotation,
  taxonomy, one-way export, and `grade serve`, which holds one run open for a grader on loopback
  and refuses to bind past it. See [`grading.md`](grading.md),
  [`grading-surfaces.md`](grading-surfaces.md).
* **The grading page.** Renders a run as one card per boundary pair, both halves side by side,
  evidence highlighted. One file, no build step. See [`grading-page.md`](grading-page.md).
* **The room-facing half.** `housecast grade deck` builds a scanned, slug-free deck and `housecast
  grade present` serves it with anonymous voting, a separate process so the divide between a
  private critique and a room is which command runs. See [`presenting.md`](presenting.md),
  [`deck.md`](deck.md).

## Not shipped

No PyPI distribution, so consumers install from Forgejo with uv, and the name claim is
`agent-compose#347` waiting on Kai. The Go engine in agent-compose still composes and is deleted
under `agent-compose#339`, blocked separately.

## See also

* [`../README.md`](../README.md) - what housecast is and how it pairs with acompose.
* [`../AGENTS.md`](../AGENTS.md) - agent-facing operating context.
