from typing import Any

import pytest
from pydantic import ValidationError

from housecast.grade.schema import (
    AGENT_COMPOSE,
    Annotation,
    Challenge,
    DatasetEntry,
    Fit,
    Half,
    Profile,
    TestTypeSpec,
    Verdict,
    annotation_order,
    pair_results,
)


def entry(
    challenge_id: str, entity: str = "engineer", test_type: str = "boundary", **fields: Any
) -> DatasetEntry:
    defaults = {
        "boundary": "modify-live-backend",
        "half": Half.IN,
        "pair_id": challenge_id.rsplit("-", 1)[0],
    }
    if test_type != "boundary":
        defaults = {}
    return DatasetEntry(
        challenge=Challenge(
            id=challenge_id,
            entity=entity,
            test_type=test_type,
            prompt="p",
            target="t",
            **{**defaults, **fields},
        ),
        output="o",
    )


def test_half_and_pair_id_travel_together() -> None:
    with pytest.raises(ValidationError):
        Challenge(id="a", entity="qa", test_type="boundary", prompt="p", target="t", half=Half.IN)


def test_profile_required_fields_are_reported_not_raised() -> None:
    challenge = Challenge(id="a", entity="qa", test_type="role-fit", prompt="p", target="t")
    assert challenge.check_against(AGENT_COMPOSE) == ["a: role-fit challenge needs attribute"]


def test_unknown_test_type_is_named() -> None:
    challenge = Challenge(id="a", entity="qa", test_type="invented", prompt="p", target="t")
    assert "invented" in challenge.check_against(AGENT_COMPOSE)[0]


def test_label_set_and_word_cap_come_from_the_profile() -> None:
    challenge = Challenge(
        id="a", entity="qa", test_type="personality", prompt="p", target="t", attribute="warm"
    )
    assert challenge.label_set(AGENT_COMPOSE) == "fit"
    assert challenge.word_cap(AGENT_COMPOSE) == 100


def test_a_second_deployment_declares_its_own_taxonomy() -> None:
    echo = Profile(
        name="sirens-echo",
        test_types=(TestTypeSpec("content-class", "binary", 40, ("attribute",)),),
        entity_order=("echo", "deep"),
    )
    challenge = Challenge(
        id="nsfw-in",
        entity="echo",
        test_type="content-class",
        prompt="p",
        target="t",
        attribute="content-nsfw",
        half=Half.IN,
        pair_id="content-nsfw",
    )
    assert challenge.check_against(echo) == []
    assert challenge.word_cap(echo) == 40


def test_a_pair_passes_only_when_both_halves_pass() -> None:
    dataset = [
        entry("modify-live-in", half="in", pair_id="modify-live"),
        entry("modify-live-out", half="out", pair_id="modify-live"),
    ]
    annotations = {
        "modify-live-in": Annotation(id="modify-live-in", label=Verdict.PASS),
        "modify-live-out": Annotation(id="modify-live-out", label=Verdict.FAIL),
    }
    [pair] = pair_results(dataset, annotations)
    assert pair.complete
    assert not pair.passed


def test_a_half_graded_pair_is_incomplete_rather_than_passing() -> None:
    dataset = [
        entry("b-in", half="in", pair_id="b"),
        entry("b-out", half="out", pair_id="b"),
    ]
    annotations = {"b-in": Annotation(id="b-in", label=Verdict.PASS)}
    [pair] = pair_results(dataset, annotations)
    assert not pair.complete
    assert not pair.passed


def test_a_fit_label_never_scores_a_pair() -> None:
    dataset = [entry("c-in", half="in", pair_id="c")]
    annotations = {"c-in": Annotation(id="c-in", label=Fit.FIT)}
    assert pair_results(dataset, annotations) == []


def test_annotation_order_is_entity_major_then_profile_order() -> None:
    dataset = [
        entry("z-personality", entity="qa", test_type="personality", attribute="candid"),
        entry("a-boundary", entity="qa", half="in", pair_id="a"),
        entry("m-boundary", entity="engineer", half="in", pair_id="m"),
    ]
    ordered = [e.id for e in annotation_order(dataset, AGENT_COMPOSE, ["engineer", "qa"])]
    assert ordered == ["m-boundary", "a-boundary", "z-personality"]


def test_a_deduction_is_the_thing_that_needs_a_critique() -> None:
    assert Annotation(id="a", label=Verdict.FAIL).is_deduction
    assert Annotation(id="a", label=Fit.UNDECIDED).is_deduction
    assert not Annotation(id="a", label=Verdict.PASS).is_deduction


def test_a_derived_challenge_is_unwritten_until_it_has_both_halves_of_the_question() -> None:
    derived = Challenge(id="c1", entity="platform", test_type="boundary")
    assert not derived.written
    assert not derived.model_copy(update={"prompt": "ask"}).written
    assert derived.model_copy(update={"prompt": "ask", "target": "pass"}).written


def test_an_unwritten_challenge_cannot_be_annotated() -> None:
    unwritten = Challenge(id="c1", entity="platform", test_type="boundary", target="pass")
    with pytest.raises(ValidationError):
        DatasetEntry(challenge=unwritten, output="whatever the subject said")
