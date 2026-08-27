"""Scaffold guard: the distribution imports and declares its version.

This is the whole suite on purpose. It exists so `just test` is a real gate
from the first commit rather than a recipe that passes by having nothing to run.
"""

from __future__ import annotations

import housecast


def test_version_is_declared() -> None:
    assert housecast.__version__ == "0.0.0"
