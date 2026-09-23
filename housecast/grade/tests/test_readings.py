"""A pair reads back in the profile's words, not the page's.

The page once carried one test type's four sentences inline, which made every
board that type no matter what its profile declared. These hold that the
wording lives in a profile, where each board supplies its own.
"""

from __future__ import annotations

import re
from pathlib import Path

from housecast.grade.tests.fixtures import PROFILE
from housecast.mcp.profile import MCP_TOOLS

PAGE = Path(__file__).resolve().parents[1] / "page/index.html"
OUTCOMES = ("pass/pass", "fail/pass", "pass/fail", "fail/fail")


def paired() -> dict[str, str]:
    return dict(PROFILE.test_types[0].readings)


def test_the_page_holds_no_profile_wording() -> None:
    """If a profile's sentence is inline, the profile is decoration."""
    page = PAGE.read_text(encoding="utf-8")
    for spec in (*PROFILE.test_types, *MCP_TOOLS.test_types):
        for sentence in spec.readings.values():
            assert sentence not in page, f"{sentence!r} is hardcoded in the page"


def test_the_page_reads_the_profile_for_its_wording() -> None:
    page = PAGE.read_text(encoding="utf-8")
    assert "function readingFor(" in page
    assert "readings" in page


def test_every_mcp_pair_type_supplies_all_four_outcomes() -> None:
    """A missing outcome falls back to `pass in, fail out`, which reads as a bug."""
    for spec in MCP_TOOLS.test_types:
        assert set(spec.readings) == set(OUTCOMES), spec.name


def test_the_mcp_board_does_not_borrow_another_profiles_wording() -> None:
    """Negative control: a profile that copied another's sentences would pass the test above."""
    borrowed = set(paired().values())
    for spec in MCP_TOOLS.test_types:
        assert not (set(spec.readings.values()) & borrowed - {"misses both ways"}), spec.name


def test_selectable_names_the_failure_the_pairing_exists_to_catch() -> None:
    """A description that wins selection everywhere passes in and fails out."""
    readings = dict(MCP_TOOLS.test_types[0].readings)
    assert readings["pass/fail"] == "fires on its neighbour's task"
    assert readings["pass/pass"] == "reachable for its own task, and no other"


def test_selectable_and_description_grounded_are_adjacent() -> None:
    """O-4 pairs them, so an annotator meets them together rather than pages apart."""
    names = [spec.name for spec in MCP_TOOLS.test_types]
    assert names.index("description-grounded") == names.index("selectable") + 1


def test_readings_ship_in_the_profile_payload() -> None:
    """A reading the page cannot see is a reading that does not exist."""
    serve = Path(__file__).resolve().parents[1] / "serve.py"
    assert '"readings": dict(spec.readings)' in serve.read_text(encoding="utf-8")


def test_the_page_still_parses_as_one_file_with_no_build_step() -> None:
    """The absent build step is this page's safety property."""
    page = PAGE.read_text(encoding="utf-8")
    assert page.count("<script") == len(re.findall(r"<script(?![^>]*\bsrc=)", page))
    assert not re.search(r"<link[^>]+rel=[\"']stylesheet", page)
