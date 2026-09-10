"""The drift check actually fires, proven rather than described.

`sync_kit.py` was negative-controlled by hand when it was written, which is not
the same as being covered. A guard whose failing path nobody runs is a guard
that reports green for whatever reason it likes. Each case here drives the
script as a subprocess so the exit code is the real one.

The fake kit is synthesised from the page's OWN vendored block, so these run
with no website checkout anywhere and still exercise both directions.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts/sync_kit.py"
PAGE = REPO / "housecast/grade/page/index.html"
DECL = re.compile(r"(--k-[a-z0-9-]+)\s*:\s*([^;]+);")


def vendored() -> dict[str, str]:
    block = PAGE.read_text(encoding="utf-8").split("-- layer 1: kit primitives", 1)[1]
    block = block.split("/* -- layer 2", 1)[0]
    return {m.group(1): m.group(2).strip() for m in DECL.finditer(block)}


def fake_site(root: Path, tokens: dict[str, str]) -> Path:
    kit = root / "src/sass"
    kit.mkdir(parents=True)
    body = "\n".join(f"  {name}: {value};" for name, value in tokens.items())
    (kit / "_kit.scss").write_text(":root {\n" + body + "\n}\n", encoding="utf-8")
    return root


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def test_a_matching_kit_reports_in_sync(tmp_path: Path) -> None:
    site = fake_site(tmp_path / "website", vendored())
    result = run(str(site), "--check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "match the kit" in result.stdout


def test_a_moved_primitive_fails_and_names_itself(tmp_path: Path) -> None:
    """#8670ff is a real superseded value for this slot, so this is the drift
    that actually happened rather than a synthetic one."""
    tokens = vendored()
    assert tokens["--k-b-400"] == "#9083f9"
    tokens["--k-b-400"] = "#8670ff"
    site = fake_site(tmp_path / "website", tokens)

    result = run(str(site), "--check")
    assert result.returncode == 1, "drift reported success"
    assert "--k-b-400" in result.stdout
    assert "#8670ff" in result.stdout and "#9083f9" in result.stdout


def test_a_primitive_the_kit_dropped_is_reported(tmp_path: Path) -> None:
    tokens = vendored()
    del tokens["--k-b-400"]
    site = fake_site(tmp_path / "website", tokens)

    result = run(str(site), "--check")
    assert result.returncode == 1
    assert "no longer declares" in result.stdout
    assert "--k-b-400" in result.stdout


@pytest.mark.parametrize("args", [("--check",), ("--check", "/nonexistent/website")])
def test_no_checkout_skips_rather_than_passing_quietly(args: tuple[str, ...]) -> None:
    """The skip is deliberate - housecast builds without a website - but it is
    the check's weakest moment, so it says so in words rather than exiting 0
    silently. The fleet validator that replaces this must fail loudly instead:
    teable:coilyco-flight-deck/agentic-os#7259.
    """
    result = run(*args)
    assert result.returncode == 0
    assert "skipped" in result.stdout


def test_a_write_run_refuses_without_a_checkout() -> None:
    """Without --check there is nothing to re-vendor from, so it must not
    silently leave the page as it found it."""
    result = run()
    assert result.returncode != 0
    assert "need a website checkout" in (result.stdout + result.stderr)
