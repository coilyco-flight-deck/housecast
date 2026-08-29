# Composition

The engine path: a roster on disk becomes an immutable bundle. `housecast
compose` drives it, `housecast/compose.py` emits it, and everything the bundle
carries is derived rather than authored.

**This page is a stub.** The structure is settled and the prose is not.

## The pipeline

1. **Load** - `housecast/roster.py` parses the YAML into the roster types.
2. **Validate** - `housecast/validate.py` refuses a bad roster before any work
   is done on it. See [`roster-language.md`](roster-language.md).
3. **Resolve** - each role's personality meld is ordered and its boundary
   allocation is settled. See [`role-boundaries.md`](role-boundaries.md).
4. **Derive** - the identity primitives, including the favorite-color solve.
   See [`identity.md`](identity.md).
5. **Emit** - `compose()` writes the bundle, its `manifest()`, and its
   `trace()`.

## Two delivery modes

The bundle emits as **native skills** or as a **compiled** document.
`compiled_document()` is the second one. Which mode a consumer wants is a
property of the harness it is feeding, not of the roster.

## Byte-identity is the acceptance bar

The Go engine in agent-compose still composes, and the two must agree byte for
byte until `agent-compose#339` deletes it. That constraint reaches further into
this code than it looks.

`go_json()` exists because Go's encoder escapes `<`, `>`, and `&` even inside
strings and Python's does not. Without re-adding exactly those three, two
identical documents differ on any summary containing an ampersand. `digest()`
is taken over the result, so the escaping difference would otherwise surface as
a content hash mismatch on documents that are in fact the same.

## Still to write

* The bundle layout: what files land, and what each one is for.
* What `manifest()` and `trace()` each carry, and which one a consumer reads.
* The digest: what it covers, and what a consumer may assume from a match.
* How `source_segment()` decides provenance.
* A worked `compose` run against the shipped roster, with the output tree.

## See also

* [`roster-language.md`](roster-language.md) - the input.
* [`identity.md`](identity.md) - the primitives derived during composition.
* [`FEATURES.md`](FEATURES.md) - the shipped capability inventory.
* [`../README.md`](../README.md) - what housecast is and how it pairs with acompose.
