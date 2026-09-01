"""The housecast CLI: compose a bundle, or project the roster.

    python -m housecast compose --role director --out DIR
    python -m housecast roster --out DIR
    python -m housecast fields
    python -m housecast grade annotate --dataset D --out O

`roster` writes the person.json shape evalkit reads, which is what took the Go
engine out of the eval path. See housecast/snapshot.py.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from housecast import compose as compose_module
from housecast import reference as reference_module
from housecast import roster as roster_module
from housecast import snapshot as snapshot_module


def _grade(argv: list[str]) -> int:
    """Forward to the click group. It keeps its own parser, so argparse stops here."""
    try:
        from housecast.grade.cli import main as grade_main
    except ImportError as missing:  # the grading half rides the eval extra
        raise SystemExit(
            f"housecast grade needs the eval extra: pip install 'housecast[eval]' ({missing})"
        ) from missing
    return grade_main(args=argv, standalone_mode=False) or 0


def _compose(args: argparse.Namespace) -> int:
    loaded = roster_module.load(args.roster)
    if args.role not in loaded.roles:
        raise SystemExit(f"roster defines no role {args.role!r}")
    out = compose_module.compose(
        loaded, args.role, args.model_tier, pathlib.Path(args.out), args.delivery
    )
    print(f"composed {args.role} at {args.model_tier} into {out}")
    return 0


def _roster(args: argparse.Namespace) -> int:
    loaded = roster_module.load(args.roster)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "person.json").write_text(snapshot_module.dumps(loaded))
    print(f"roster projected into {out / 'person.json'}")
    return 0


def _fields(args: argparse.Namespace) -> int:
    """Rendered rather than committed, so there is no second copy to go stale."""
    del args
    print(reference_module.render(), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    # `grade` owns its own parser, so it is split off before argparse sees it.
    raw = sys.argv[1:] if argv is None else argv
    if raw and raw[0] == "grade":
        return _grade(raw[1:])

    parser = argparse.ArgumentParser(prog="housecast")
    parser.add_argument("--roster", default=str(roster_module.DATA))
    sub = parser.add_subparsers(dest="command", required=True)

    compose_parser = sub.add_parser("compose", help="compose one role bundle")
    compose_parser.add_argument("--role", required=True)
    compose_parser.add_argument("--model-tier", default="frontier")
    compose_parser.add_argument(
        "--delivery", default="native-skills", choices=("native-skills", "compiled")
    )
    compose_parser.add_argument("--out", required=True)
    compose_parser.set_defaults(handler=_compose)

    roster_parser = sub.add_parser("roster", help="project the roster as person.json")
    roster_parser.add_argument("--out", required=True)
    roster_parser.set_defaults(handler=_roster)

    fields_parser = sub.add_parser("fields", help="print the roster field reference")
    fields_parser.set_defaults(handler=_fields)

    sub.add_parser("grade", help="grade a board dataset (needs the eval extra)")

    args = parser.parse_args(argv)
    handler: object = args.handler
    assert callable(handler)
    return int(handler(args))


if __name__ == "__main__":
    sys.exit(main())
