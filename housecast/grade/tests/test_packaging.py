"""The package's own shipping contract, which a consumer discovers too late."""

from __future__ import annotations

import tomllib
from pathlib import Path

import housecast.grade

ROOT = Path(__file__).resolve().parents[3]


def test_the_typing_marker_ships() -> None:
    """Without it a strict-mypy consumer reads every import here as untyped."""
    installed = Path(str(housecast.grade.__file__)).parent
    assert (installed / "py.typed").is_file()


def test_the_marker_is_declared_as_package_data() -> None:
    """Present in the tree is not the same as present in the built wheel."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    included = config["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert "housecast" in included


def test_no_runner_reaches_the_dependency_set() -> None:
    """The engine core stays installable without a runner. See docs/grading.md."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    names = " ".join(config["project"]["dependencies"]).lower()
    for runner in ("inspect-ai", "openai", "anthropic", "litellm"):
        assert runner not in names
