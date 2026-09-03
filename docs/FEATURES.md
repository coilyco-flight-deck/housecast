# Features

Coarse inventory of the major capabilities housecast ships.

## Shipped

* **The composition engine.** Reads a roster as YAML, resolves each role's meld and boundary
  allocation, derives the identity primitives, and emits an immutable bundle. See
  [`composition.md`](composition.md), [`identity.md`](identity.md).
* **The roster language.** `housecast/data/roster.yaml` carries roles, personalities, boundaries,
  acts, and the invariant. See [`roster-language.md`](roster-language.md),
  [`role-boundaries.md`](role-boundaries.md).
* **Attribute acts, and the overlay that extends them.** Every role, personality, and boundary side
  names three runnable things, rendered as `## Run`, following the side the seat holds. A private
  overlay appends estate-only acts without redefining anything. See [`overlay.md`](overlay.md).
* **A roster projection.** `housecast roster` emits the `person.json` shape downstream tools read,
  which is what removed Go from the eval path.
* **evalkit, the board runner.** Derives the board from the roster across five test types (boundary, role-fit, personality, voice, and [grounding](grading-grounding.md), which pairs a fact inside the role's lane against one its evidence cannot settle), runs it through Inspect against
  Agent Proxy, and reports the coverage gap. See [`evaluation.md`](evaluation.md), [`evaluation-workflow.md`](evaluation-workflow.md).
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
* **The PyPI release train.** A pushed `housecast-v*` tag gates, builds, and uploads with a token from SSM. See [`publishing.md`](publishing.md).

## Not shipped

No release is on PyPI yet, only the 0.0.1 name claim from `agent-compose#347`, so the next tag is
the first real upload. agent-compose's Go engine still composes, deleted under `agent-compose#339`. Attested bundles, a signed statement binding a graded run to the digest it graded, are designed and not built. See [`composition.md`](composition.md).

## See also

* [`../README.md`](../README.md) - what housecast is and how it pairs with acompose.
* [`../AGENTS.md`](../AGENTS.md) - agent-facing operating context.
