"""The seam a board's source sits behind.

A board needs three things from wherever its cases come from: the profile naming
the test types, the entities a grader reads a charter for, and the challenges
themselves. One provider exists today, which is why the interface is written
now. Waiting for the second one means deriving the shape from two examples that already disagree.

The core declares the protocol and implements none of it. A provider imports
this module; this module imports no provider, which `test_import_graph.py`
holds to.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from housecast.grade.schema import Challenge, Profile


@runtime_checkable
class Provider(Protocol):
    """One source of entities and the challenges they imply.

    A provider is constructed around its own source, because what a source
    needs differs per kind: the role provider takes a rendered person, and an
    MCP provider takes a live connection. Nothing below takes arguments the
    caller has to know the shape of.
    """

    @property
    def name(self) -> str:
        """Stable slug, recorded on a trial so a comparison can refuse across kinds."""
        ...

    def profile(self) -> Profile:
        """The test-type taxonomy this provider's challenges are drawn from."""
        ...

    def entities(self) -> dict[str, Any]:
        """`{"entity_order": [...], "entities": {...}}`, the shape grading surfaces take."""
        ...

    def challenges(self, group: str = "tier") -> list[Challenge]:
        """Every challenge the source implies, ordered by `group`."""
        ...
