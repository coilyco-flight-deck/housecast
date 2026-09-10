"""The page's identity table matches the roster it was copied from.

The board names each entity's agent and shows an element glyph. That table is
mirrored into the page because the page carries no build step and cannot read
YAML at render. Mirrored data drifts, which is the whole reason the palette
needed re-vendoring, so this fails the moment the roster moves underneath it.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

PAGE = Path(__file__).resolve().parents[1] / "page/index.html"
ROSTER = Path(__file__).resolve().parents[2] / "data/roster.yaml"
ENTRY = re.compile(
    r'(\w+):\s*\{\s*who:\s*"([^"]+)",\s*element:\s*"([^"]+)",\s*glyph:\s*"([^"]*)"\s*\}'
)


@pytest.fixture(scope="module")
def table() -> dict[str, tuple[str, str]]:
    block = PAGE.read_text(encoding="utf-8").split("var ROSTER = {", 1)[1].split("};", 1)[0]
    return {m.group(1): (m.group(2), m.group(3)) for m in ENTRY.finditer(block)}


@pytest.fixture(scope="module")
def roles() -> dict[str, dict[str, Any]]:
    loaded = yaml.safe_load(ROSTER.read_text(encoding="utf-8"))["roles"]
    return dict(loaded)


def test_the_page_names_every_role(
    table: dict[str, tuple[str, str]], roles: dict[str, dict[str, Any]]
) -> None:
    assert set(table) == set(roles), (
        f"page-only: {sorted(set(table) - set(roles))}, "
        f"roster-only: {sorted(set(roles) - set(table))}"
    )


def test_names_and_elements_match_the_roster(
    table: dict[str, tuple[str, str]], roles: dict[str, dict[str, Any]]
) -> None:
    drift: dict[str, dict[str, tuple[str, str]]] = {
        slug: {"page": table[slug], "roster": (r["identity"]["name"], r["element"])}
        for slug, r in roles.items()
        if slug in table and table[slug] != (r["identity"]["name"], r["element"])
    }
    assert drift == {}, f"identity drifted from the roster: {drift}"


def test_one_glyph_per_element(table: dict[str, tuple[str, str]]) -> None:
    """The glyph carries the element because the kit has no hue to spare, so
    two roles sharing an element must not read as two different things."""
    block = PAGE.read_text(encoding="utf-8").split("var ROSTER = {", 1)[1].split("};", 1)[0]
    by_element: dict[str, set[str]] = {}
    for m in ENTRY.finditer(block):
        by_element.setdefault(m.group(3), set()).add(m.group(4))
    split = {e: g for e, g in by_element.items() if len(g) > 1}
    assert split == {}, f"one element drawn with more than one glyph: {split}"
