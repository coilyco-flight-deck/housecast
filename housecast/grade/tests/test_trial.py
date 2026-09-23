"""The refusals: D-5, K-3, K-4 and K-5.

Each test names the thing that moved, because a refusal that says only "these
are not comparable" sends a reader back to diff two records by hand.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from housecast.grade.trial import (
    Provenance,
    ProvenanceError,
    Trial,
    require_comparable,
    require_one_variant,
    require_poolable,
)

BASE = Provenance(
    board="sha256:board",
    fixture="sha256:fixture",
    tools="sha256:tools",
    subject_version="1.4.0",
    model="local/qwen3-coder",
    temperature=0.0,
    harness_mode="in-memory",
    seed=7,
)


def trial(challenge_id: str = "c1", variant: str = "v1", **moved: Any) -> Trial:
    return Trial(
        challenge_id=challenge_id,
        variant=variant,
        epoch=1,
        provenance=replace(BASE, **moved) if moved else BASE,
        response="ok",
    )


def test_identical_provenance_pools() -> None:
    """Negative control: the refusals below must be about the difference, not about pooling."""
    require_poolable([trial("c1"), trial("c2")])


def test_a_changed_model_refuses_and_names_it() -> None:
    """D-5."""
    with pytest.raises(ProvenanceError, match="model moved"):
        require_poolable([trial("c1"), trial("c2", model="local/other")])


def test_a_changed_temperature_refuses_and_names_it() -> None:
    """D-5."""
    with pytest.raises(ProvenanceError, match="temperature moved"):
        require_poolable([trial("c1"), trial("c2", temperature=0.7)])


def test_a_changed_tool_set_refuses_and_names_it() -> None:
    """D-5. Selection depends on what else was on offer, so this is not a detail."""
    with pytest.raises(ProvenanceError, match="tools moved"):
        require_poolable([trial("c1"), trial("c2", tools="sha256:other")])


def test_a_changed_subject_version_refuses() -> None:
    """The addition the second cut made: subject version is an input like any other."""
    with pytest.raises(ProvenanceError, match="subject_version moved"):
        require_poolable([trial("c1"), trial("c2", subject_version="1.5.0")])


def test_two_things_moving_names_both() -> None:
    with pytest.raises(ProvenanceError, match="model, temperature moved"):
        require_poolable([trial("c1"), trial("c2", model="local/other", temperature=0.7)])


def test_a_denominator_cannot_span_two_variants() -> None:
    """K-4."""
    with pytest.raises(ProvenanceError, match="cannot span 2 variants"):
        require_one_variant([trial("c1", variant="v1"), trial("c2", variant="v2")])


def test_one_variant_returns_its_own_name() -> None:
    assert require_one_variant([trial("c1"), trial("c2")]) == "v1"


def test_comparing_variants_whose_prompt_also_moved_refuses() -> None:
    """K-3: differing prose is the measurement, so nothing else may move with it."""
    with pytest.raises(ProvenanceError, match="model moved as well as the prose"):
        require_comparable(
            [trial("c1", variant="v1")],
            [trial("c1", variant="v2", model="local/other")],
        )


def test_comparing_two_variants_with_identical_inputs_is_allowed() -> None:
    require_comparable([trial("c1", variant="v1")], [trial("c1", variant="v2")])


def test_comparing_a_variant_with_itself_refuses() -> None:
    with pytest.raises(ProvenanceError, match="nothing to compare"):
        require_comparable([trial("c1", variant="v1")], [trial("c2", variant="v1")])


def test_rebasing_returns_a_copy_and_leaves_the_original_alone() -> None:
    """K-5: committed evidence is never rewritten to match a later variant."""
    original = trial("c1")
    rebased = original.rebased(replace(BASE, model="local/other"))
    assert rebased is not original
    assert original.provenance.model == "local/qwen3-coder"
    assert rebased.provenance.model == "local/other"
