"""The grading half imports no composition engine and no consumer's runner.

`provider.py` declares an interface providers implement from above, so nothing in
`housecast/grade` imports down into either. A severed import stays severed only if
something fails when it returns. The negative control is here because a scan
matching nothing passes for the wrong reason.
"""

from __future__ import annotations

import ast
import pathlib

GRADE = pathlib.Path(__file__).resolve().parent.parent
FORBIDDEN = ("housecast.compose", "evalkit")


def _imported_modules(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found.add(node.module)
    return found


def _is_forbidden(module: str) -> bool:
    return any(module == f or module.startswith(f + ".") for f in FORBIDDEN)


def _sources() -> list[pathlib.Path]:
    return [p for p in sorted(GRADE.rglob("*.py")) if "tests" not in p.parts]


def test_grade_imports_neither_the_composition_engine_nor_a_provider() -> None:
    offenders = {
        p.relative_to(GRADE).as_posix(): sorted(m for m in _imported_modules(p) if _is_forbidden(m))
        for p in _sources()
    }
    assert {k: v for k, v in offenders.items() if v} == {}


def test_scan_sees_real_files_and_real_imports() -> None:
    """Negative control: the scan above passes on a populated graph, not an empty one."""
    sources = _sources()
    assert len(sources) > 10
    assert any("housecast.digest" in _imported_modules(p) for p in sources)
