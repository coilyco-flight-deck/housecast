"""Build the sheet the director seat scores, before any grading exists.

`housecast#7317` splits the work: the 0/1/2 charter-ambiguity read is a charter
reading and belongs to the director seat, while the design and the measurement
are science's. This is the handoff artifact between the two halves.

It derives the board through `evalkit.matrix` rather than parsing printed
output, so a roster change moves the sheet on its own. Regenerate it against the
roster the next run actually uses. A sheet scored against a board that then
changed is a set of scores pointing at cases nobody ran.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from evalkit.coverage import authored_ids
from evalkit.matrix import derive

HERE = pathlib.Path(__file__).parent
COLUMNS = ("case", "entity", "test_type", "attribute", "half", "pair_id", "authored", "target")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", type=pathlib.Path, required=True, help="person.json")
    parser.add_argument("--challenges", type=pathlib.Path, required=True, help="challenges.yaml")
    parser.add_argument("--out", type=pathlib.Path, default=HERE / "scoring-sheet.csv")
    args = parser.parse_args(argv)

    written = authored_ids(args.challenges)
    board = derive(json.loads(args.roster.read_text()))

    with args.out.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        # `score` and `why` stay empty on purpose. A generated sheet that
        # arrives pre-filled is a sheet nobody reads the charter for.
        writer.writerow([*COLUMNS, "score", "why"])
        for case in board:
            writer.writerow(
                [
                    case.id,
                    case.entity,
                    case.test_type,
                    case.attribute or "",
                    case.half.value if case.half else "",
                    case.pair_id or "",
                    "yes" if case.id in written else "no",
                    (case.target or "").replace("\n", " "),
                    "",
                    "",
                ]
            )

    reachable = sum(1 for case in board if case.id in written)
    print(f"wrote {args.out.name}: {len(board)} derived, {reachable} authored and reachable")
    print("score column empty. The director seat fills 0, 1 or 2 per row, reading the charter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
