#!/usr/bin/env python3
"""Refuse a publish whose git tag disagrees with the packaged version.

PyPI accepts a version once. An upload built from `housecast-v0.4.0` while
`housecast/__init__.py` still says 0.3.0 lands as 0.3.0 and can never be
replaced, so this runs before the build rather than after it. The repository has
already been bitten by the softer form of this: `housecast-v0.1.3` reports
version 0.1.1, and nothing failed because a git dependency does not check.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PREFIX = "housecast-v"
ROOT = Path(__file__).resolve().parent.parent
VERSION_SOURCE = ROOT / "housecast" / "__init__.py"
VERSION_PATTERN = re.compile(r'^__version__ = "([^"]+)"$', re.MULTILINE)


def packaged_version(source: Path = VERSION_SOURCE) -> str:
    """Read `__version__` textually, so no import and no install is needed."""
    match = VERSION_PATTERN.search(source.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"no __version__ assignment in {source}")
    return match.group(1)


def version_from_tag(tag: str) -> str:
    """Return the version a release tag names, rejecting any other shape."""
    tag = tag.removeprefix("refs/tags/")
    if not tag.startswith(PREFIX):
        raise ValueError(f"release tag {tag!r} does not start with {PREFIX!r}")
    version = tag[len(PREFIX) :]
    if not version:
        raise ValueError(f"release tag {tag!r} names no version")
    return version


def check(tag: str, version: str) -> None:
    """Raise unless the tag names exactly the version the package will build."""
    tagged = version_from_tag(tag)
    if tagged != version:
        raise ValueError(
            f"tag {tag!r} names version {tagged!r} but "
            f"{VERSION_SOURCE.name} says {version!r}; "
            "move the tag or bump the package, then retry"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="the housecast-v* tag being published")
    args = parser.parse_args(argv)
    version = packaged_version()
    try:
        check(args.tag, version)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{args.tag} agrees with packaged version {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
