"""The guard standing between a mistyped tag and a permanent PyPI version."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

import housecast

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "release_tag.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("release_tag", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_script_reads_the_version_the_package_reports() -> None:
    """Textual read and imported value must not be two different numbers."""
    assert _load().packaged_version() == housecast.__version__


def test_a_refs_tags_ref_is_accepted_as_written() -> None:
    """Forgejo hands the workflow a full ref on some triggers and a bare tag on others."""
    module = _load()
    assert module.version_from_tag("refs/tags/housecast-v0.4.1") == "0.4.1"
    assert module.version_from_tag("housecast-v0.4.1") == "0.4.1"


@pytest.mark.parametrize("tag", ["v0.4.0", "housecast-0.4.0", "housecast-v", "0.4.0"])
def test_a_tag_of_the_wrong_shape_is_refused(tag: str) -> None:
    with pytest.raises(ValueError):
        _load().version_from_tag(tag)


def test_agreement_passes_and_disagreement_raises() -> None:
    module = _load()
    module.check("housecast-v9.9.9", "9.9.9")
    with pytest.raises(ValueError, match="but"):
        module.check("housecast-v9.9.9", "0.3.0")


def test_the_cli_exits_nonzero_on_disagreement(capsys: pytest.CaptureFixture[str]) -> None:
    """The workflow reads the exit code, so a wrong tag must not exit 0."""
    module = _load()
    assert module.main(["housecast-v0.0.0-not-the-version"]) == 1
    assert "error:" in capsys.readouterr().err


def test_the_cli_accepts_the_current_version() -> None:
    assert _load().main([f"housecast-v{housecast.__version__}"]) == 0
