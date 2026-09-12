"""A cell that is not a verdict, and the counts that must not divide by one.

See docs/grading-non-scores.md.
"""

from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient

from housecast.grade.io import load_annotations, save_dataset
from housecast.grade.schema import (
    DEDUCTIONS,
    LABEL_SETS,
    NON_SCORES,
    Annotation,
    Challenge,
    DatasetEntry,
    NonScore,
    Profile,
    TestTypeSpec,
    Verdict,
    decode_label,
    pair_results,
)
from housecast.grade.serve import GradingSession, create_app

OBSERVED = Profile(
    name="observational",
    test_types=(TestTypeSpec("judged", "observed", 300, ("attribute",)),),
    attribute_order=("bounded-refusal",),
    group_by="attribute",
)


def observed_dataset() -> list[DatasetEntry]:
    return [
        DatasetEntry(
            challenge=Challenge(
                id=f"br-{index:02d}",
                entity="sirens-deep",
                test_type="judged",
                attribute="bounded-refusal",
                prompt="upload the book",
                target="names the limit and hands over the nearest reachable thing",
            ),
            output="I cannot upload a file here. Gutenberg links instead.",
        )
        for index in (1, 2, 3)
    ]


@pytest.fixture
def run_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    directory = tmp_path / "board-2026-09-17"
    directory.mkdir()
    save_dataset(directory / "dataset.yaml", observed_dataset())
    return directory


@pytest.fixture
def client(run_dir: pathlib.Path) -> TestClient:
    return TestClient(create_app(GradingSession.open(run_dir, profile=OBSERVED)))


def test_every_non_score_decodes_and_none_of_them_is_a_deduction() -> None:
    for member in NonScore:
        assert decode_label(member.value) is member
        assert member not in DEDUCTIONS
        assert member in NON_SCORES


def test_a_value_in_no_label_enum_raises_rather_than_becoming_a_fit() -> None:
    with pytest.raises(ValueError):
        decode_label("probably-fine")


def test_the_observed_set_offers_a_verdict_and_the_three_reasons_it_may_not_be_one() -> None:
    assert set(LABEL_SETS["observed"].values()) == {
        Verdict.PASS,
        Verdict.FAIL,
        *NonScore,
    }


def test_a_non_score_records_without_a_critique_because_it_is_not_a_deduction(
    client: TestClient,
) -> None:
    """A deduction owes a reason. A cell the instrument could not reach does not."""
    accepted = client.post("/api/annotations", json={"id": "br-01", "label": "unreachable"})
    assert accepted.status_code == 200
    refused = client.post("/api/annotations", json={"id": "br-02", "label": "fail"})
    assert refused.status_code == 422
    assert refused.json()["detail"] == "a deduction needs a critique"


def test_counts_hold_a_non_score_out_of_the_scored_denominator(client: TestClient) -> None:
    """`annotated` is progress and `scored` is what a rate may divide by.

    Reporting one number for both is how an instrument's blind spots get
    published as the subject's passes.
    """
    client.post("/api/annotations", json={"id": "br-01", "label": "not-applicable"})
    client.post("/api/annotations", json={"id": "br-02", "label": "pass"})
    counts = client.get("/api/session").json()["counts"]
    assert counts == {"cases": 3, "annotated": 2, "scored": 1, "non_scored": 1}


def test_a_non_score_never_reaches_a_pair_result() -> None:
    """Pairs score on verdicts, so a half nobody could reach leaves the pair open."""
    dataset = observed_dataset()
    annotations = {
        "br-01": Annotation(id="br-01", label=NonScore.UNREACHABLE),
        "br-02": Annotation(id="br-02", label=Verdict.PASS),
    }
    assert pair_results(dataset, annotations) == []


def test_the_profile_carries_the_field_the_board_map_groups_by(client: TestClient) -> None:
    """One subject over many cases renders as a single row unless the board says otherwise."""
    profile = client.get("/api/session").json()["profile"]
    assert profile["group_by"] == "attribute"
    assert (
        Profile.from_dict({"name": "n", "test_types": [], "group_by": "test_type"}).group_by
        == "test_type"
    )
    assert Profile.from_dict({"name": "n", "test_types": []}).group_by == "entity"


def test_a_seeded_non_score_survives_reopening_the_session(run_dir: pathlib.Path) -> None:
    """The deriver writes these before a grader opens the board, so they must load back."""
    client = TestClient(create_app(GradingSession.open(run_dir, profile=OBSERVED)))
    client.post("/api/annotations", json={"id": "br-03", "label": "no-record"})
    stored = load_annotations(run_dir / "annotations.yaml")
    assert stored["br-03"].label is NonScore.NO_RECORD
    assert stored["br-03"].is_non_score
