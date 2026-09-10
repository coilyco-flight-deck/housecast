"""Grading order as a view beside a run, never folded into the run itself.

`dataset.yaml` records what a run produced, in derivation order. A pass that
reordered it in place would rewrite that record to suit one session, which is
the failure a committed dataset exists to prevent. `annotation-queue.csv` is
the other half: a ranking written beside the dataset, saying which cases to
reach first when a pass may not finish.

Found by convention rather than by flag, the way `io.pin_path` finds pin.yaml,
because both are facts about the run directory rather than choices a grader
makes at the prompt.

CSV rather than YAML because `dispersion.py` emits this table beside its other
two, and converting on the way in would put a second copy of the order in the
repository.
"""

from __future__ import annotations

import csv
from pathlib import Path

from housecast.grade.schema import DatasetEntry

QUEUE_NAME = "annotation-queue.csv"


class QueueMismatchError(Exception):
    """Raised where a queue and a dataset cannot be describing the same run."""


def queue_path(dataset_path: Path) -> Path:
    return dataset_path.parent / QUEUE_NAME


def load_queue(path: Path) -> list[str]:
    """Case ids in grading order, read from the `case` column."""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "case" not in rows[0]:
        raise QueueMismatchError(f"{path}: no `case` column, so it orders nothing")
    order = [row["case"].strip() for row in rows if (row.get("case") or "").strip()]
    # A repeated id would silently drop whichever case it displaced, so the
    # ranking is refused rather than deduplicated into a plausible order.
    duplicated = sorted({case for case in order if order.count(case) > 1})
    if duplicated:
        raise QueueMismatchError(f"{path}: ranks the same case twice: {', '.join(duplicated)}")
    return order


def order_by_queue(
    entries: list[DatasetEntry], order: list[str], known: list[DatasetEntry] | None = None
) -> tuple[list[DatasetEntry], int]:
    """Sort entries by the queue, trailing anything it does not rank.

    `known` is the whole dataset when `entries` is an `--entity` slice. A queue
    naming a case the whole dataset lacks means the two came from different
    runs, which is the straddle the pin refuses, so it raises here rather than
    ordering a subset and looking correct.
    """
    population = {entry.challenge.id for entry in (known if known is not None else entries)}
    absent = [case for case in order if case not in population]
    if absent:
        raise QueueMismatchError(
            f"ranks {len(absent)} case(s) the dataset does not carry, "
            f"so they are not the same run: {', '.join(absent[:3])}"
        )
    rank = {case: index for index, case in enumerate(order)}
    trailing = len(order)
    ordered = sorted(entries, key=lambda entry: rank.get(entry.challenge.id, trailing))
    unranked = sum(1 for entry in entries if entry.challenge.id not in rank)
    return ordered, unranked
