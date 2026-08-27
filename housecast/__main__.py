"""The housecast CLI: compose a bundle, or project the roster.

    python -m housecast compose --role tpm --out DIR
    python -m housecast roster --out DIR

`roster` writes the person.json shape evalkit reads, which is what took the Go
engine out of the eval path. See housecast/snapshot.py.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from housecast import compose as compose_module
from housecast import roster as roster_module
from housecast import snapshot as snapshot_module


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


def main(argv: list[str] | None = None) -> int:
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

    args = parser.parse_args(argv)
    handler: object = args.handler
    assert callable(handler)
    return int(handler(args))


if __name__ == "__main__":
    sys.exit(main())
