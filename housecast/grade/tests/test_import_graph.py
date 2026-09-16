"""The grading half imports no composition engine.

`housecast/grade/pin.py` used to reach up for `digest`, which was the one import
pointing from the generic half down into the role engine. Severing it is only
durable if something fails when it comes back, and an editor adding
`from housecast.compose import ...` for one convenient helper is how it comes
back. A negative control is included because an import scan that matches nothing
passes for the wrong reason.
"""

from __future__ import annotations

import ast
import pathlib

GRADE = pathlib.Path(__file__).resolve().parent.parent
FORBIDDEN = "housecast.compose"


def _imported_modules(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found.add(node.module)
    return found


def _sources() -> list[pathlib.Path]:
    return [p for p in sorted(GRADE.rglob("*.py")) if "tests" not in p.parts]


def test_grade_does_not_import_the_composition_engine() -> None:
    offenders = {
        p.relative_to(GRADE).as_posix(): sorted(m for m in _imported_modules(p) if m == FORBIDDEN)
        for p in _sources()
    }
    assert {k: v for k, v in offenders.items() if v} == {}


def test_scan_sees_real_files_and_real_imports() -> None:
    """Negative control: the scan above passes on a populated graph, not an empty one."""
    sources = _sources()
    assert len(sources) > 10
    assert any("housecast.digest" in _imported_modules(p) for p in sources)
