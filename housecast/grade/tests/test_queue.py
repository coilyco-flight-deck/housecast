import pathlib
from typing import Any

import pytest

from housecast.grade.queue import (
    QueueMismatchError,
    load_queue,
    order_by_queue,
    queue_path,
)
from housecast.grade.schema import Challenge, DatasetEntry


def entry(challenge_id: str, entity: str = "qa") -> DatasetEntry:
    spec: dict[str, Any] = {
        "id": challenge_id,
        "entity": entity,
        "test_type": "personality",
        "attribute": "candid",
        "prompt": "p",
        "target": "t",
    }
    return DatasetEntry(challenge=Challenge(**spec), output="answer")


def write_queue(tmp_path: pathlib.Path, *cases: str) -> pathlib.Path:
    path = tmp_path / "annotation-queue.csv"
    rows = "\n".join(f"{index + 1},{case},qa,personality,,0.5" for index, case in enumerate(cases))
    path.write_text(f"rank,case,entity,test_type,pair_id,divergence\n{rows}\n")
    return path


def test_queue_sits_beside_the_dataset() -> None:
    assert queue_path(pathlib.Path("runs/board/dataset.yaml")).name == "annotation-queue.csv"
    assert queue_path(pathlib.Path("runs/board/dataset.yaml")).parent.name == "board"


def test_order_follows_the_queue_not_the_dataset(tmp_path: pathlib.Path) -> None:
    order = load_queue(write_queue(tmp_path, "c", "a", "b"))
    ordered, unranked = order_by_queue([entry("a"), entry("b"), entry("c")], order)
    assert [item.challenge.id for item in ordered] == ["c", "a", "b"]
    assert unranked == 0


def test_a_case_the_queue_does_not_rank_goes_last_in_dataset_order(
    tmp_path: pathlib.Path,
) -> None:
    order = load_queue(write_queue(tmp_path, "c"))
    entries = [entry("a"), entry("b"), entry("c")]
    ordered, unranked = order_by_queue(entries, order)
    assert [item.challenge.id for item in ordered] == ["c", "a", "b"]
    assert unranked == 2


def test_an_entity_slice_orders_against_the_whole_dataset(tmp_path: pathlib.Path) -> None:
    order = load_queue(write_queue(tmp_path, "c", "a", "b"))
    whole = [entry("a", "qa"), entry("b", "ops"), entry("c", "qa")]
    slice_ = [item for item in whole if item.challenge.entity == "qa"]
    ordered, unranked = order_by_queue(slice_, order, whole)
    assert [item.challenge.id for item in ordered] == ["c", "a"]
    assert unranked == 0


def test_a_queue_naming_an_absent_case_refuses(tmp_path: pathlib.Path) -> None:
    order = load_queue(write_queue(tmp_path, "a", "gone"))
    with pytest.raises(QueueMismatchError, match="not the same run"):
        order_by_queue([entry("a")], order)


def test_a_repeated_rank_refuses_rather_than_dropping_a_case(tmp_path: pathlib.Path) -> None:
    with pytest.raises(QueueMismatchError, match="same case twice"):
        load_queue(write_queue(tmp_path, "a", "b", "a"))


def test_a_csv_without_a_case_column_refuses(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "annotation-queue.csv"
    path.write_text("rank,id\n1,a\n")
    with pytest.raises(QueueMismatchError, match="orders nothing"):
        load_queue(path)
