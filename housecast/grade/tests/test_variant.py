"""A-5 and the search count around it.

The one-character edit is literal rather than illustrative: the point of the
criterion is that a digest over prose alone cannot be fooled by a round trip,
and a test that changed a whole description would pass without showing that.
"""

from __future__ import annotations

import pytest

from housecast.grade.variant import Variant, VariantError, VariantStore, prose_digest

ORIGINAL = {
    "write_file": "Write text to a path, creating parent directories.",
    "read_file": "Read a file as text.",
}
EDITED = ORIGINAL | {"write_file": "Write text to a path, creating parent directories!"}


def store_with_baseline() -> tuple[VariantStore, Variant]:
    store = VariantStore()
    return store, store.baseline(ORIGINAL, authored_by="human:kai")


def test_editing_one_character_mints_a_new_digest() -> None:
    """A-5, first half."""
    store, base = store_with_baseline()
    edited = store.mint(EDITED, parent=base, authored_by="model:claude-opus-5")
    assert edited.digest != base.digest


def test_reverting_that_character_returns_the_original_digest() -> None:
    """A-5, second half. Not a third variant."""
    store, base = store_with_baseline()
    edited = store.mint(EDITED, parent=base, authored_by="model:claude-opus-5")
    reverted = store.mint(ORIGINAL, parent=edited, authored_by="model:claude-opus-5")
    assert reverted.digest == base.digest
    assert reverted is base
    assert store.tried == 1, "the revert collided, so the search is one variant wide"


def test_the_two_prose_maps_differ_by_exactly_one_character() -> None:
    """Negative control: A-5 is about a one-character edit, so prove it is one."""
    before = ORIGINAL["write_file"]
    after = EDITED["write_file"]
    assert len(before) == len(after)
    assert sum(a != b for a, b in zip(before, after, strict=True)) == 1


def test_reordering_the_mapping_is_the_same_variant() -> None:
    reordered = dict(reversed(list(ORIGINAL.items())))
    assert prose_digest(reordered) == prose_digest(ORIGINAL)


def test_the_count_of_variants_tried_is_the_chain_traversal() -> None:
    """O-5. The number that goes in the sentence carrying the delta."""
    store, base = store_with_baseline()
    parent = base
    for index in range(6):
        parent = store.mint(
            ORIGINAL | {"read_file": f"Read a file as text, revision {index}."},
            parent=parent,
            authored_by="model:claude-opus-5",
        )
    assert store.tried == 6
    assert "best of 6 tried since baseline" in store.render_search(parent)


def test_lineage_runs_baseline_first() -> None:
    store, base = store_with_baseline()
    edited = store.mint(EDITED, parent=base, authored_by="human:kai")
    assert [v.digest for v in store.lineage(edited)] == [base.digest, edited.digest]


def test_an_unattributed_variant_refuses() -> None:
    """Three-way circularity: subject, editor and grader must not all be anonymous models."""
    store, base = store_with_baseline()
    with pytest.raises(VariantError, match="human:<name>"):
        store.mint(EDITED, parent=base, authored_by="claude")


def test_both_attribution_forms_are_accepted() -> None:
    """Negative control for the refusal above."""
    store, base = store_with_baseline()
    assert store.mint(EDITED, parent=base, authored_by="model:x").authored_by == "model:x"


def test_minting_against_a_foreign_parent_refuses() -> None:
    store, base = store_with_baseline()
    other = VariantStore()
    stranger = other.baseline({"write_file": "elsewhere"}, authored_by="human:kai")
    with pytest.raises(VariantError, match="was not minted by this store"):
        store.mint(EDITED, parent=stranger, authored_by="human:kai")
    assert base.digest in {v.digest for v in store.lineage(base)}


def test_a_store_has_one_baseline() -> None:
    store, _ = store_with_baseline()
    with pytest.raises(VariantError, match="already has it"):
        store.baseline({"write_file": "second"}, authored_by="human:kai")


def test_a_fresh_store_has_tried_nothing() -> None:
    assert VariantStore().tried == 0
