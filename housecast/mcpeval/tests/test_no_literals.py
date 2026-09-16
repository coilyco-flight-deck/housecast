"""The token discipline, enforced rather than asserted in a comment.

`tokens.css` claims every visual value lives in it. A claim in a docstring is
not a control, so this reads the other two files and fails on a raw colour,
length, font stack or shadow outside the token file.
"""

from __future__ import annotations

import pathlib
import re

PAGE = pathlib.Path(__file__).parent.parent / "page"

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
LENGTH = re.compile(r"(?<![\w-])\d*\.?\d+(px|rem|em|ch)\b")
FONT_VALUE = re.compile(r"font-family\s*:\s*([^;}]+)", re.I)
RGB = re.compile(r"\brgba?\(", re.I)

# `100%` and `0` are layout rather than brand. Everything else needs a token.
ALLOWED_LENGTHS = {"0px", "0rem"}

# A media query cannot read a custom property, so a breakpoint is the one length
# written where it is used. Inside the block everything is checked as normal.
MEDIA = re.compile(r"^\s*@media\b")

# `inherit` takes the family from an ancestor that already read a token, so it
# introduces no stack of its own.
FONT_OK = ("var(", "inherit")


def _lines(path: pathlib.Path) -> list[tuple[int, str]]:
    return [
        (n, line)
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if not line.strip().startswith(("/*", "*", "//"))
    ]


def test_app_css_holds_no_literal_values() -> None:
    offences: list[str] = []
    for number, line in _lines(PAGE / "app.css"):
        for pattern, label in ((HEX, "hex colour"), (RGB, "rgb colour")):
            if pattern.search(line):
                offences.append(f"app.css:{number} {label}: {line.strip()}")
        for match in FONT_VALUE.finditer(line):
            if not match.group(1).strip().startswith(FONT_OK):
                offences.append(f"app.css:{number} font stack: {line.strip()}")
        if MEDIA.match(line):
            continue
        for match in LENGTH.finditer(line):
            if match.group(0) not in ALLOWED_LENGTHS:
                offences.append(f"app.css:{number} length {match.group(0)}: {line.strip()}")
    assert not offences, "app.css must take every visual value from tokens.css:\n" + "\n".join(
        offences
    )


def test_app_js_decides_no_visual_value() -> None:
    offences: list[str] = []
    for number, line in _lines(PAGE / "app.js"):
        for pattern, label in ((HEX, "hex colour"), (RGB, "rgb colour")):
            if pattern.search(line):
                offences.append(f"app.js:{number} {label}: {line.strip()}")
    assert not offences, "app.js must set classes, never values:\n" + "\n".join(offences)


def test_tokens_define_both_schemes() -> None:
    text = (PAGE / "tokens.css").read_text()
    assert ":root {" in text
    assert "prefers-color-scheme: dark" in text


def test_the_customer_product_shares_no_palette_with_the_annotator() -> None:
    """A customer product that looks like the internal annotator is the wrong artifact."""
    annotator = pathlib.Path(__file__).parents[3] / "housecast" / "grade" / "page" / "index.html"
    if not annotator.is_file():
        return
    theirs = set(HEX.findall(annotator.read_text()))
    ours = set(HEX.findall((PAGE / "tokens.css").read_text()))
    assert not (theirs & ours), f"shared palette values: {sorted(theirs & ours)}"
