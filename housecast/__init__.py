"""Composition engine for agent rosters.

Reads a roster as YAML, resolves each role's personality meld and boundary
allocation, derives identity primitives including each role's favorite color,
and emits an immutable bundle. Moves to coilyco-flight-deck/housecast under
agent-compose#337, which is why it sits here as its own package rather than
inside evalkit.

Discharged from the #332 tracer's cheat list:

* favorite_color is derived, not read. color.favorites ports the OKLab joint
  solve including the 400-round spread, and all seven roles match Go exactly.
* Both delivery modes are emitted. native-skills and compiled are each
  byte-identical to the Go engine for all seven roles.
* Validation exists: boundary ownership, personality bindings, the definition
  set, the legible colour band, skill frontmatter, and the copy contract.
* Content digests match Go byte for byte, including the identity digest, which
  covers an anonymous struct carrying no json tags rather than the manifest's
  own identity block.
* Decision reasons are the Go strings, not paraphrases. The traces are
  byte-identical.
* The model-tier matrix is enforced. An unsupported tier is refused with the
  Go engine's wording.
* Role methods and seat channels survive the loader, and the identity card
  emits the Role methods line between the role skill and the boundaries, as Go
  does. No shipped role carries either, so a fixture injects them and a
  negative control asserts the shipped roster still renders no methods line.

Carried forward, with reasons, tracked in agent-compose#373:

* Local library merge and conflict detection is not ported. #333 lists it as a
  semantic step and this engine reads exactly one person package, so a roster
  admitting a second source is out of scope until the merge lands.
* Overlay, cascade, skill selectors, and knowledge-provider catalogues stay in
  Go. No bundle in the shipped roster selects from them, so parity does not
  cover them and porting blind would be guesswork.
* The copy contract is not ported at all, model or digest. Go's CopyContract is
  a scope plus forbid/prefer rules, hashed over a canonical marshal.
  check_copy_contract here validates role body word counts, which is a name
  collision rather than the same check. No shipped role declares one and
  roster.yaml has no field for it. agent-compose#373
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.7"
