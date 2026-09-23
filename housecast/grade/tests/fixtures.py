"""A profile for tests only. housecast ships none, so the suite declares its own."""

from __future__ import annotations

from pathlib import Path

from housecast.grade.schema import Profile, TestTypeSpec

PROFILE = Profile(
    name="fixture",
    test_types=(
        TestTypeSpec(
            "paired",
            "binary",
            50,
            ("attribute", "half", "pair_id"),
            readings={
                "pass/pass": "the pair holds",
                "fail/pass": "misses the in-half",
                "pass/fail": "fires on the out-half",
                "fail/fail": "misses both ways",
            },
        ),
        TestTypeSpec("check", "binary", 50, ("attribute",)),
        TestTypeSpec("degree", "fit", 100, ("attribute",)),
    ),
)

PROFILE_YAML = """\
name: fixture
test_types:
  - name: paired
    label_set: binary
    word_cap: 50
    requires: [attribute, half, pair_id]
  - name: check
    label_set: binary
    word_cap: 50
    requires: [attribute]
  - name: degree
    label_set: fit
    word_cap: 100
    requires: [attribute]
"""


def write_profile(directory: Path) -> str:
    """The fixture profile on disk, for a command that takes --profile."""
    path = directory / "profile.yaml"
    path.write_text(PROFILE_YAML)
    return str(path)
