"""Measure how much room the derived role palette has left inside the legible band.

The derivation in internal/palette is global, so one personality hex moves every
role accent. That makes "can this colour change" a roster question rather than a
per-colour one, and the answer is a headroom margin rather than a yes.

Both inputs are read from their owning source rather than restated here: the
band constants from internal/color/color.go, the accents from the committed
snapshot. A probe that hardcoded either would report on a stale copy of the
thing it is measuring.
"""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path

COLOR_GO = Path("internal/color/color.go")
SNAPSHOT = Path("internal/palette/role-palette.txt")


@dataclass(frozen=True)
class Band:
    min_l: float
    max_l: float
    min_chroma: float


@dataclass(frozen=True)
class Accent:
    role: str
    hex: str
    lightness: float
    chroma: float

    def margin(self, band: Band) -> float:
        """Distance to whichever edge of the band is nearer."""
        return min(self.lightness - band.min_l, band.max_l - self.lightness)


def read_band(root: Path) -> Band:
    text = (root / COLOR_GO).read_text()
    values: dict[str, float] = {}
    for key in ("minL", "maxL", "minChroma"):
        found = re.search(rf"^\s*{key}\s*=\s*([\d.]+)", text, re.M)
        if not found:
            raise ValueError(f"{COLOR_GO} defines no {key}")
        values[key] = float(found.group(1))
    return Band(values["minL"], values["maxL"], values["minChroma"])


def _linearize(channel: int) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def to_oklab(hex_color: str) -> tuple[float, float, float]:
    r, g, b = (_linearize(int(hex_color[i : i + 2], 16)) for i in (1, 3, 5))
    long = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    med = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    short = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    lc, mc, sc = (math.copysign(abs(v) ** (1 / 3), v) for v in (long, med, short))
    return (
        0.2104542553 * lc + 0.7936177850 * mc - 0.0040720468 * sc,
        1.9779984951 * lc - 2.4285922050 * mc + 0.4505937099 * sc,
        0.0259040371 * lc + 0.7827717662 * mc - 0.8086757660 * sc,
    )


def read_accents(root: Path) -> list[Accent]:
    text = (root / SNAPSHOT).read_text()
    out: list[Accent] = []
    for match in re.finditer(r"^(\w+) // (#[0-9a-f]{6}) // #[0-9a-f]{6}", text, re.M):
        role, hex_color = match.group(1), match.group(2)
        lightness, a, b = to_oklab(hex_color)
        out.append(Accent(role, hex_color, lightness, math.hypot(a, b)))
    if not out:
        raise ValueError(f"{SNAPSHOT} lists no roles; run `agent-compose palette-snapshot`")
    return out


def report(root: Path) -> str:
    band = read_band(root)
    accents = read_accents(root)
    lines = [
        f"legible band L [{band.min_l}, {band.max_l}], chroma floor {band.min_chroma}",
        "",
        f"{'role':10} {'accent':9} {'lightness':>9} {'chroma':>7} {'margin':>8}",
        "-" * 48,
    ]
    for accent in sorted(accents, key=lambda a: a.margin(band)):
        lines.append(
            f"{accent.role:10} {accent.hex:9} {accent.lightness:9.4f} "
            f"{accent.chroma:7.3f} {accent.margin(band):8.4f}"
        )
    tightest = min(accents, key=lambda a: a.margin(band))
    lines += [
        "",
        f"tightest: {tightest.role} at {tightest.hex}, {tightest.margin(band):.4f} of headroom.",
        "A personality edit that moves the roster further than that lands outside the band,",
        "and the role it breaks need not be one that shares a personality with the edit.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    args = parser.parse_args(argv)
    print(report(args.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
