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


def test_the_sdist_is_an_allowlist_so_a_new_directory_is_out_by_default() -> None:
    """An exclude list ships whatever nobody remembered to name.

    The wheel was scoped from the start and the sdist was not, so the sdist took
    every tracked file. PyPI accepts a version once, so anything that reaches it
    is there permanently.
    """
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    sdist = config["tool"]["hatch"]["build"]["targets"]["sdist"]
    assert "include" in sdist, "an exclude list would ship the next directory by default"
    assert set(sdist["include"]) >= {"/housecast", "/evalkit"}


def test_every_sdist_pattern_is_rooted_because_a_bare_name_matches_at_any_depth() -> None:
    """The failure this catches actually happened, on the commit that added the
    allowlist above.

    Hatchling's patterns are gitignore-style. A bare `README.md` matched nine of
    them, one per evaluation directory, so the first scoped sdist still carried
    the content the scoping was written to keep out. The config looked right and
    the artifact was wrong, which is why this asserts the shape of every entry
    rather than the presence of the ones that were remembered.
    """
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    included = config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
    unrooted = [entry for entry in included if not entry.startswith("/")]
    assert not unrooted, f"these match at any depth rather than at the root: {unrooted}"


def test_committed_run_evidence_stays_out_of_the_sdist() -> None:
    """`evaluations/` quotes subject output verbatim and is a record rather than
    package material. It was 101 files and 55% of the sdist's bytes before the
    target was scoped, and the built artifact carries none of it now."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    included = config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
    assert not any("evaluations" in entry for entry in included)


def test_no_runner_reaches_the_dependency_set() -> None:
    """The engine core stays installable without a runner. See docs/grading.md."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    names = " ".join(config["project"]["dependencies"]).lower()
    for runner in ("inspect-ai", "openai", "anthropic", "litellm"):
        assert runner not in names
