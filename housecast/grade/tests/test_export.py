import pathlib

import pytest

from housecast.grade.export import (
    EXPORT_FORMAT,
    ExportRefusedError,
    build_run,
    export_run_dir,
    scan_for_secrets,
)
from housecast.grade.io import save_annotations, save_dataset
from housecast.grade.schema import Annotation, Challenge, DatasetEntry, Half, Provenance, Verdict


def pair_dataset(output: str = "a plain answer") -> list[DatasetEntry]:
    return [
        DatasetEntry(
            challenge=Challenge(
                id=f"live-{half.value}",
                entity="ops",
                test_type="boundary",
                prompt="p",
                target="t",
                attribute="modify-live-backend",
                half=half,
                pair_id="live",
            ),
            output=output,
        )
        for half in (Half.IN, Half.OUT)
    ]


GRADED = {
    "live-in": Annotation(id="live-in", label=Verdict.PASS, critique="", evidence=""),
    "live-out": Annotation(
        id="live-out", label=Verdict.FAIL, critique="dropped the handoff", evidence="a plain"
    ),
}


def test_the_pair_travels_as_its_own_structure() -> None:
    run = build_run("run1", pair_dataset(), GRADED)
    assert run.to_dict()["format"] == EXPORT_FORMAT
    assert run.pairs[0]["halves"] == {"in": "pass", "out": "fail"}
    assert run.pairs[0]["complete"]
    assert not run.pairs[0]["passed"]
    assert run.counts() == {"cases": 2, "annotated": 2, "pairs": 1, "pairs_passed": 0}


def test_grader_notes_stay_out_unless_asked_for() -> None:
    withheld = build_run("run1", pair_dataset(), GRADED)
    assert all("critique" not in case.to_dict() for case in withheld.cases)

    included = build_run("run1", pair_dataset(), GRADED, include_private=True)
    assert any(case.to_dict().get("critique") for case in included.cases)


@pytest.mark.parametrize(
    "text",
    [
        "contact AKIAIOSFODNN7EXAMPLE now",
        "token ghp_abcdefghijklmnopqrstuvwxyz012345",
        "-----BEGIN RSA PRIVATE KEY-----",
        "reach someone@example.com",
        "host somebox.ts.net",
        "id 123456789012345678",
    ],
)
def test_the_exporter_refuses_rather_than_scrubs(text: str) -> None:
    assert scan_for_secrets(text)
    with pytest.raises(ExportRefusedError):
        build_run("run1", pair_dataset(output=text), GRADED)


def test_a_refusal_names_every_reason_in_one_pass() -> None:
    text = "AKIAIOSFODNN7EXAMPLE and someone@example.com"
    with pytest.raises(ExportRefusedError) as refusal:
        build_run("run1", pair_dataset(output=text), GRADED)
    assert "an AWS key id" in str(refusal.value)
    assert "an email address" in str(refusal.value)


def test_a_grader_note_is_only_scanned_when_it_is_exported() -> None:
    leaky = {
        "live-in": Annotation(id="live-in", label=Verdict.PASS),
        "live-out": Annotation(
            id="live-out", label=Verdict.FAIL, critique="saw AKIAIOSFODNN7EXAMPLE"
        ),
    }
    build_run("run1", pair_dataset(), leaky)
    with pytest.raises(ExportRefusedError):
        build_run("run1", pair_dataset(), leaky, include_private=True)


def test_provenance_rides_along_when_the_run_recorded_it() -> None:
    run = build_run("run1", pair_dataset(), GRADED, provenance=Provenance(model="a-model"))
    assert run.to_dict()["provenance"]["model"] == "a-model"


def test_a_run_directory_round_trips(tmp_path: pathlib.Path) -> None:
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    save_dataset(run_dir / "dataset.yaml", pair_dataset())
    save_annotations(run_dir / "annotations.yaml", GRADED)

    run = export_run_dir(run_dir)
    assert run.name == "run1"
    assert run.counts()["cases"] == 2


def test_a_named_grader_s_annotations_are_found_only_when_asked_for(
    tmp_path: pathlib.Path,
) -> None:
    """`grade serve --grader kai` writes `annotations.kai.yaml`, and a seal of
    that directory used to read `annotations.yaml`, find nothing, and say
    nothing. `load_annotations` returns an empty mapping for a path that does
    not exist, so the page rendered every case unannotated and the export
    reported success. Observed on the 2026-09-17 fallback page, which lost all
    58 of its seeded non-scores that way.
    """
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    save_dataset(run_dir / "dataset.yaml", pair_dataset())
    save_annotations(run_dir / "annotations.kai.yaml", GRADED, "kai")

    assert export_run_dir(run_dir).counts()["annotated"] == 0
    assert export_run_dir(run_dir, grader="kai").counts()["annotated"] == len(GRADED)


def test_a_directory_with_no_dataset_is_refused(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ExportRefusedError, match="nothing to display"):
        export_run_dir(tmp_path)
