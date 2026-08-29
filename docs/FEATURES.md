# Features

Coarse inventory of the major capabilities housecast ships. Bugfixes,
refactors, and internal plumbing never earn an entry here.

## Shipped

* **The composition engine.** Reads a roster as YAML, validates it, resolves
  each role's personality meld and boundary allocation, derives the identity
  primitives including each role's favorite color, and emits an immutable
  bundle in either the native-skills or the compiled delivery mode.
* **The roster language.** `housecast/data/roster.yaml` carries roles,
  personalities, boundaries, and the invariant, with its field ancestry
  documented in the file.
* **A roster projection.** `housecast roster` emits the `person.json` shape
  downstream tools read, which is what removed Go from the eval path.
* **evalkit, the board runner.** Derives the challenge board from the roster,
  runs it through Inspect against Agent Proxy, and hands datasets to the
  `aos-eval` annotator. It travels with the engine so the graded artifact and
  the shipped artifact stay identical.

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
* **The room-facing half.** `housecast grade deck` joins authored rounds to
  graded cases into a `housecast.deck.v1` file, withholding every role and
  boundary slug by construction and refusing a round that names a missing case,
  an ungraded case, or no commitments. `housecast grade present` serves that
  deck to a room and takes anonymous votes on it, unlocking one thing per state
  so the reveal is absent from the wire until the presenter reaches it and an
  open round reports a count rather than a direction. It is a separate process
  from `serve` on purpose: nothing is authenticated for a viewer, so the divide
  between a private critique and an audience is which command is running rather
  than a flag inside one.
* **The grading page.** `housecast/grade/page/index.html` renders one committed
  run as a card per boundary pair, both halves side by side, with the evidence
  span highlighted in the response. One file and no build step, so a
  grader-private payload cannot be baked into a distributed artifact. Mount it
  with `serve --static housecast/grade/page`. See
  [`grading-page.md`](grading-page.md).

## See also

* [`../README.md`](../README.md) - what housecast is and how it pairs with acompose.
* [`../AGENTS.md`](../AGENTS.md) - agent-facing operating context for this repository.
* [`../.ward/ward.yaml`](../.ward/ward.yaml) - catalog metadata for the cross-repo graph.
