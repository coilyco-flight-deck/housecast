# Features

Coarse inventory of the major capabilities housecast ships.

## Shipped

* **Attribute acts, and the overlay extending them.** Every role, personality and boundary side names
  three runnable things; a private overlay appends estate-only acts. See [`overlay.md`](overlay.md).
* **evalkit, the board runner.** Derives the board across seven test types, runs it through Inspect,
  and reports the coverage gap. [`evaluation.md`](evaluation.md), [`grading-grounding.md`](grading-grounding.md).
* **The grading half.** `housecast grade` under the `eval` extra: schema, pairing, annotation,
  taxonomy, export, `grade serve`, and `grade pin`. See [`grading.md`](grading.md).
* **The grading page.** One card per boundary pair, both halves side by side, evidence highlighted.
  One file, no build step. See [`grading-page.md`](grading-page.md).
* **Observational boards.** From replies a subject already gave, so a cell can be decided and not a verdict. [`grading-non-scores.md`](grading-non-scores.md).
* **The room-facing half.** `grade deck` builds a scanned, slug-free deck and `grade present` serves
  it with anonymous voting. [`presenting.md`](presenting.md), [`deck.md`](deck.md).
* **The variant search.** Reads every variant against a measured noise floor and labels overfitting
  and overselling rather than netting them. `teable:coilyco-flight-deck/housecast#7802`.
* **The MCP tool-description loop.** `housecast mcpeval`, under `eval` and `mcp`: an HTTP MCP subject
  with flawed prose, a runner making real model calls and routing the returned calls back to it,
  deterministic grading, a concurrent run, a paired sign test, and the visual flow driving it.
  Record: `evaluations/mcp-tool-loop-2026-09-16/`.
* **The PyPI release train.** A pushed `housecast-v*` tag gates, builds and uploads. [`publishing.md`](publishing.md).

## Not shipped

No release is on PyPI yet, only the 0.0.1 name claim from `agent-compose#347`. Attested bundles are designed, not built.
The variant search has no `Measurer`. The MCP loop runs on one task and one subject: a second task,
an LLM judge, HTTP fault injection and a holdout split are absent, and it has no `docs/` page
because the band is full at 20.

## See also

* [`../README.md`](../README.md) - what housecast is, and [`../AGENTS.md`](../AGENTS.md) for agents.
