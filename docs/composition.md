# Composition

The engine path: a roster on disk becomes an immutable bundle. `housecast
compose` drives it and `housecast/compose.py` emits it. Everything the bundle
carries is derived rather than authored.

**Stub.** The structure is settled and the prose is not.

## The pipeline

1. **Load and validate** - a bad roster is refused before any work is done. See [`roster-language.md`](roster-language.md).
2. **Resolve** - the meld is ordered, the boundary allocation settled. See [`role-boundaries.md`](role-boundaries.md).
3. **Derive** - the identity primitives. See [`identity.md`](identity.md).
4. **Emit** - `compose()` writes the bundle, `manifest()` and `trace()`, as **native skills** or a **compiled** document per the harness being fed.

## Byte-identity is the acceptance bar

The Go engine still composes, and the two must agree byte for byte until
`agent-compose#339` deletes it. `go_json()` re-adds Go's escaping of `<`, `>`
and `&` because `digest()` is taken over the result, and without it two
identical documents differ on any summary holding an ampersand.

## What a digest match lets a consumer assume

`manifest()` digests every content part, so a match says the bytes composed are
the bytes shipped. It does not say they were graded. `eval-prompts.sh` deletes
the manifest on exit, so no artifact links a run to the bundle it graded, and
the README's identity claim is true by construction and evidenced by nothing.
**Attestation closes that gap, designed and not built.** One whole-bundle
digest becomes the subject of an in-toto `test-result/v0.1` statement whose
`configuration` names the roster, the board, the Inspect log and the model
under test by digest, in DSSE, signed with cosign against a KMS key.
`housecast verify` refuses a missing, unsigned or mismatched bundle and emits a
SLSA verification summary. The regulatory hook is Annex IV 2(g), test reports
dated and signed by the responsible persons, not Article 12.

## Still to write

* The bundle layout, what `trace()` carries, a worked `compose` run, the whole-bundle digest input, the extension fields, and the policy file.
