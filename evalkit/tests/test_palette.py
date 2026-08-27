"""The OKLab conversion has to agree with internal/color, or the margin is fiction.

These lightness values are agent-compose's own, taken verbatim from the errors it
raised when each colour was tried in the record. They are observations of the Go
implementation rather than a second copy of it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evalkit import palette

REPORTED_LIGHTNESS = {
    "#d1cb26": 0.82,
    "#5f8f47": 0.60,
    "#478f47": 0.59,
    "#478f5f": 0.59,
    "#f8ab5d": 0.80,
    "#3a9278": 0.60,
}


@pytest.mark.parametrize(("hex_color", "reported"), sorted(REPORTED_LIGHTNESS.items()))
def test_lightness_matches_agent_compose(hex_color: str, reported: float) -> None:
    lightness, _, _ = palette.to_oklab(hex_color)
    assert round(lightness, 2) == pytest.approx(reported)


def test_band_is_read_from_color_go(tmp_path: Path) -> None:
    source = tmp_path / palette.COLOR_GO
    source.parent.mkdir(parents=True)
    source.write_text("const (\n\tminL = 0.11\n\tmaxL = 0.99\n\tminChroma = 0.02\n)\n")
    band = palette.read_band(tmp_path)
    assert (band.min_l, band.max_l, band.min_chroma) == (0.11, 0.99, 0.02)


def test_margin_is_distance_to_the_nearer_edge() -> None:
    band = palette.Band(min_l=0.60, max_l=0.80, min_chroma=0.05)
    near_ceiling = palette.Accent("devrel", "#f7ab5d", lightness=0.7996, chroma=0.130)
    near_floor = palette.Accent("sysadmin", "#009895", lightness=0.6143, chroma=0.105)
    assert near_ceiling.margin(band) == pytest.approx(0.0004)
    assert near_floor.margin(band) == pytest.approx(0.0143)


def test_accents_come_from_the_committed_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / palette.SNAPSHOT
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("preamble\n\nplatform // #9c8b31 // #1f2000 // tenacious, grounded\n")
    accents = palette.read_accents(tmp_path)
    assert [a.role for a in accents] == ["platform"]
    assert accents[0].hex == "#9c8b31"


def test_empty_snapshot_is_an_error_rather_than_an_empty_report(tmp_path: Path) -> None:
    snapshot = tmp_path / palette.SNAPSHOT
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("preamble only, no roles\n")
    with pytest.raises(ValueError, match="palette-snapshot"):
        palette.read_accents(tmp_path)
