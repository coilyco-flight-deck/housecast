"""Variants of the prose under test, and the chain that counts the search.

The pin refuses a grade straddling a change to its inputs, and the prose shown
beside a case is one of them. PR-4 edits that prose on purpose, so the pin stops
being only a refusal and gains an axis: within one variant it refuses exactly as
before, and across variants differing prose is the measurement.

A variant is identified by its prose and nothing else. That is what makes an
edit-and-revert collide with its origin instead of arriving as a third variant
whose numbers a reader would compare against the first two.

The parent chain is here because the count of variants tried has to be
reported beside any result (O-5), and traversing a chain the store already
keeps is cheaper than a second ledger that can disagree with it.

Rules K-3 to K-5 and O-5 in `teable:coilyco-flight-deck/housecast#7802`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from housecast.digest import digest


class VariantError(ValueError):
    """Raised when a lineage is impossible or an author is unattributable."""


def prose_digest(prose: Mapping[str, str]) -> str:
    """Over prose alone. Sorted so a reordered mapping is the same variant."""
    canonical = json.dumps(dict(sorted(prose.items())), ensure_ascii=False, sort_keys=True)
    return digest(canonical)


@dataclass(frozen=True)
class Variant:
    """One state of the prose under test."""

    digest: str
    prose: Mapping[str, str]
    parent: str | None
    authored_by: str

    @property
    def is_baseline(self) -> bool:
        return self.parent is None

    def short(self) -> str:
        return self.digest.removeprefix("sha256:")[:12]


@dataclass
class VariantStore:
    """Every variant minted against one board, keyed by prose.

    Not persistent. The durable form arrives with the trial record, which is
    where a variant has to outlive the process that minted it.
    """

    _variants: dict[str, Variant] = field(default_factory=dict)
    _baseline: str | None = None

    def baseline(self, prose: Mapping[str, str], authored_by: str) -> Variant:
        if self._baseline is not None:
            raise VariantError("a store has one baseline, and this one already has it")
        variant = self._record(prose, parent=None, authored_by=authored_by)
        self._baseline = variant.digest
        return variant

    def mint(self, prose: Mapping[str, str], parent: Variant, authored_by: str) -> Variant:
        """A-5: new prose mints a new digest, and prose already seen returns what was seen.

        The parent recorded is the first one, so a revert reports the lineage
        that actually produced the prose rather than the path that rediscovered it.
        """
        if parent.digest not in self._variants:
            raise VariantError(f"parent {parent.short()} was not minted by this store")
        return self._record(prose, parent=parent.digest, authored_by=authored_by)

    def _record(self, prose: Mapping[str, str], parent: str | None, authored_by: str) -> Variant:
        if not authored_by.startswith(("human:", "model:")):
            raise VariantError(
                f"authored_by must be 'human:<name>' or 'model:<id>', got {authored_by!r}. "
                "A loop where subject, editor and grader are all models is the failure "
                "this field exists to make visible."
            )
        key = prose_digest(prose)
        existing = self._variants.get(key)
        if existing is not None:
            return existing
        variant = Variant(digest=key, prose=dict(prose), parent=parent, authored_by=authored_by)
        self._variants[key] = variant
        return variant

    def get(self, key: str) -> Variant:
        if key not in self._variants:
            raise VariantError(f"no variant {key}")
        return self._variants[key]

    def lineage(self, variant: Variant) -> list[Variant]:
        """Baseline first, `variant` last."""
        chain: list[Variant] = []
        seen: set[str] = set()
        current: Variant | None = variant
        while current is not None:
            if current.digest in seen:
                raise VariantError(f"lineage of {variant.short()} cycles")
            seen.add(current.digest)
            chain.append(current)
            current = self._variants[current.parent] if current.parent else None
        return list(reversed(chain))

    @property
    def tried(self) -> int:
        """O-5: how many variants have been minted against this board since the baseline.

        Distinct prose, so a revert does not inflate the count any more than it
        mints a variant. This is the number that goes in the sentence carrying
        the delta, because the best of N beats a baseline by chance at a rate
        the reader cannot infer without it.
        """
        return max(len(self._variants) - 1, 0)

    def render_search(self, reported: Variant) -> str:
        """O-5 in the sentence rather than in a log."""
        return (
            f"variant {reported.short()}, best of {self.tried} tried since baseline, "
            f"authored by {reported.authored_by}"
        )
