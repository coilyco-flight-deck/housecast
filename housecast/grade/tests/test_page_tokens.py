"""The grading page's token layers hold.

`just sync-kit-check` compares the vendored primitives against a real kit, but
it needs a website checkout and skips without one, so it cannot be the only
guard. These run anywhere and cover the part that is local: that layer 3 never
holds a literal colour, and that every role a rule reads is actually declared.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[1] / "page/index.html"
LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(\s*\d")
DECL = re.compile(r"(--[a-z0-9-]+)\s*:")
USE = re.compile(r"var\((--[a-z0-9-]+)")
BASE_MARK = "----- base */"


@pytest.fixture(scope="module")
def css() -> str:
    text = PAGE.read_text(encoding="utf-8")
    return text.split("<style>", 1)[1].split("</style>", 1)[0]


def test_only_the_vendored_block_holds_literal_colours(css: str) -> None:
    """Layer 3 reads roles, never raw values. The page had twenty that did."""
    body = css.split("/* -- layer 2", 1)[1]
    offenders = [
        line.strip() for line in body.splitlines() if LITERAL.search(line) and "--k-" not in line
    ]
    assert offenders == [], (
        "literal colour outside the vendored primitive block:\n  " + "\n  ".join(offenders)
    )


def test_every_role_a_rule_reads_is_declared(css: str) -> None:
    """A var() onto an undeclared name renders as nothing, silently."""
    declared = set(DECL.findall(css))
    used = set(USE.findall(css))
    assert used <= declared, f"undeclared tokens in use: {sorted(used - declared)}"


def test_the_frame_does_not_flip_with_the_theme(css: str) -> None:
    """Kit rule 3: nav and footer are the chrome and stay on ink on both
    themes, so the frame roles are declared once and never rebound."""
    light = css.split(':root[data-theme="light"]', 1)[1].split("\n}", 1)[0]
    assert "--frame" not in light, "the frame was rebound in the light theme"


def test_vendored_primitives_are_not_referenced_by_components(css: str) -> None:
    """Layer 3 may not reach past layer 2 into the raw ramps.

    Rebinding a role from a primitive is allowed and is what `.output`'s scoped
    paper ground does. Painting one straight into a CSS property is not.
    """
    body = css.split(BASE_MARK, 1)[1]
    reaching = []
    for line in body.splitlines():
        # strip role declarations, leaving only what the rule actually paints
        painted = re.sub(r"--[a-z0-9-]+\s*:[^;]*;", "", line)
        reaching += [m for m in USE.findall(painted) if m.startswith("--k-")]
    assert sorted(set(reaching)) == [], (
        f"components painting primitives directly: {sorted(set(reaching))}"
    )
