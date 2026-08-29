# Features

Coarse inventory of the major capabilities housecast ships. Bugfixes,
refactors, and internal plumbing never earn an entry here.

## Shipped

* **The composition engine.** Reads a roster as YAML, validates it, resolves
  each role's personality meld and boundary allocation, derives the identity
  primitives including each role's favorite color, and emits an immutable
  bundle in either the native-skills or the compiled delivery mode. See
  [`composition.md`](composition.md) and [`identity.md`](identity.md).
* **The roster language.** `housecast/data/roster.yaml` carries roles,
  personalities, boundaries, and the invariant, with its field ancestry
  documented in the file. See [`roster-language.md`](roster-language.md) and
  [`role-boundaries.md`](role-boundaries.md).
* **A roster projection.** `housecast roster` emits the `person.json` shape
  downstream tools read, which is what removed Go from the eval path.
* **evalkit, the board runner.** Derives the challenge board from the roster,
  runs it through Inspect against Agent Proxy, and hands datasets to the
  `aos-eval` annotator. It travels with the engine so the graded artifact and
  the shipped artifact stay identical. See [`evaluation.md`](evaluation.md).

## Not shipped

No PyPI distribution. Consumers install from Forgejo with uv, described in the
README. The name claim is `agent-compose#347` and waits on Kai.

The Go engine in agent-compose still exists and still composes. It is deleted
under `agent-compose#339`, which is blocked separately.

## Grading

`housecast.grade` is the grading half: schema, boundary pairing, human
annotation, failure taxonomy, and the one-way display export. It ships as
`housecast grade` under the `eval` extra, alongside the `evalkit` runner. Ported
from `agentic-os/aos-eval`, which is deleted once sirens-echo moves. See
[`grading.md`](grading.md).

* **A browser grading surface.** `housecast grade serve` holds one committed run
  open for a grader on loopback and writes every decision back to
  `annotations.yaml`, enforcing the same label, critique, and verbatim-span
  rules the terminal loop does. It hands the page `housecast.grading.v1`,
  carrying the profile's own keystrokes so one-key grading survives the move.
  The evidence span is selected rather than retyped. It refuses to bind past
  loopback without `--expose`, because that payload carries the grader's private
  critique, and a built display artifact embeds the public export instead and
  can neither read one nor write a label.

## See also

* [`../README.md`](../README.md) - what housecast is and how it pairs with acompose.
* [`../AGENTS.md`](../AGENTS.md) - agent-facing operating context for this repository.
* [`../.ward/ward.yaml`](../.ward/ward.yaml) - catalog metadata for the cross-repo graph.
