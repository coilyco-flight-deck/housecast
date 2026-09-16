# Features

Coarse inventory of the major capabilities housecast ships.

## Shipped

* **The composition engine.** Reads a roster as YAML, resolves each role's meld and boundary
  allocation, derives the identity primitives, and emits an immutable bundle. See
  [`composition.md`](composition.md), [`identity.md`](identity.md).
* **The roster language.** `housecast/data/roster.yaml` carries roles, personalities, boundaries,
  acts, and the invariant. See [`roster-language.md`](roster-language.md), [`role-boundaries.md`](role-boundaries.md).
* **Attribute acts, and the overlay extending them.** Every role, personality and boundary side
  names three runnable things, and a private overlay appends estate-only acts. See [`overlay.md`](overlay.md).
* **A roster projection.** `housecast roster` emits the `person.json` shape downstream tools read.
* **evalkit, the board runner.** Derives the board across seven test types, runs it through Inspect
  against Agent Proxy, and reports the coverage gap. See [`evaluation.md`](evaluation.md), [`grading-grounding.md`](grading-grounding.md).
* **The grading half.** `housecast grade` under the `eval` extra: schema, pairing, annotation,
  taxonomy, export, `grade serve`, and `grade pin`, which digests a grade's five inputs so a pass
  straddling a change refuses instead of reading as disagreement. See [`grading.md`](grading.md).
* **The grading page.** Renders a run as one card per boundary pair, both halves side by side,
  evidence highlighted. One file, no build step. See [`grading-page.md`](grading-page.md).
* **Observational boards.** Derived from replies a subject already gave, so a cell can be decided
  and not a verdict, held out of every denominator. See [`grading-non-scores.md`](grading-non-scores.md).
* **The room-facing half.** `housecast grade deck` builds a scanned, slug-free deck and `grade
  present` serves it with anonymous voting, a separate process. See [`presenting.md`](presenting.md), [`deck.md`](deck.md).
* **The iteration loop.** Under the `mcp` extra: hosts an MCP subject in-process, drives a model
  at it, rewrites its tool descriptions, and reads every variant against a measured noise floor.
  Labels overfitting and overselling instead of netting them. `teable:coilyco-flight-deck/housecast#7802`.
* **The PyPI release train.** A pushed `housecast-v*` tag gates, builds and uploads with a token from
  SSM. See [`publishing.md`](publishing.md).

## Not shipped

No release is on PyPI yet, only the 0.0.1 name claim from `agent-compose#347`. agent-compose's Go
engine still composes, deleted under `agent-compose#339`. Attested bundles are designed, not built.
The iteration loop has no `Measurer`, so it is wired and tested but cannot yet run a real board.

## See also

* [`../README.md`](../README.md) - what housecast is, and [`../AGENTS.md`](../AGENTS.md) for agents.
