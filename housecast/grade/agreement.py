"""Two or more graders over one board, and the rate at which they disagree.

The pairing half asks whether a boundary held. This asks whether the humans
reading it saw the same thing, which is a different question and the one a
split test is run to answer.

A case counts toward the rate only when every grader has labelled it. A missing
grade is reported as incomplete rather than folded in, because a denominator
that quietly absorbs the cases nobody reached reports agreement that was never
measured.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from housecast.grade.schema import Annotation, DatasetEntry


@dataclass(frozen=True)
class CaseAgreement:
    """One case, as each grader labelled it."""

    case_id: str
    labels: dict[str, str]
    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing

    @property
    def agreed(self) -> bool:
        """Undefined on an incomplete case, so read it with `complete`."""
        return self.complete and len(set(self.labels.values())) == 1

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"id": self.case_id, "labels": dict(sorted(self.labels.items()))}
        if self.missing:
            payload["missing"] = list(self.missing)
        else:
            payload["agreed"] = self.agreed
        return payload


@dataclass(frozen=True)
class AgreementReport:
    graders: tuple[str, ...]
    cases: tuple[CaseAgreement, ...]

    @property
    def complete(self) -> tuple[CaseAgreement, ...]:
        return tuple(case for case in self.cases if case.complete)

    @property
    def compared(self) -> int:
        return len(self.complete)

    @property
    def disagreed(self) -> int:
        return sum(1 for case in self.complete if not case.agreed)

    @property
    def rate(self) -> float | None:
        """None rather than zero when nothing was compared, which is not agreement."""
        if not self.compared:
            return None
        return self.disagreed / self.compared

    def to_dict(self) -> dict[str, Any]:
        return {
            "graders": list(self.graders),
            "cases": len(self.cases),
            "compared": self.compared,
            "disagreed": self.disagreed,
            "rate": None if self.rate is None else round(self.rate, 4),
            "per_case": [case.to_dict() for case in self.cases],
        }


def compare(
    dataset: list[DatasetEntry], graders: Mapping[str, dict[str, Annotation]]
) -> AgreementReport:
    """Join every grader's annotations onto the dataset, in dataset order."""
    names = tuple(sorted(graders))
    cases = tuple(
        CaseAgreement(
            case_id=entry.id,
            labels={
                name: graders[name][entry.id].label.value
                for name in names
                if entry.id in graders[name]
            },
            missing=tuple(name for name in names if entry.id not in graders[name]),
        )
        for entry in dataset
    )
    return AgreementReport(graders=names, cases=cases)


def render(report: AgreementReport) -> str:
    """One line per case, then the rate, matching how `pairs` prints."""
    lines = []
    for case in report.cases:
        if not case.complete:
            state = "incomplete, missing " + ", ".join(case.missing)
        else:
            state = "agreed" if case.agreed else "DISAGREED"
        seen = "  ".join(
            f"{name}={case.labels[name]}" for name in report.graders if name in case.labels
        )
        lines.append(f"{case.case_id}  {seen}  {state}")

    if report.rate is None:
        everyone = ", ".join(report.graders)
        lines.append(f"0 of {len(report.cases)} cases graded by all of: {everyone}")
    else:
        lines.append(
            f"{report.disagreed}/{report.compared} compared cases disagreed "
            f"({report.rate:.0%}), {len(report.cases) - report.compared} incomplete"
        )
    return "\n".join(lines)
