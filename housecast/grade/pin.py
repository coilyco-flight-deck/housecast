"""Pin the inputs a grade depends on, so a straddling pass refuses rather than averages.

A grade is a decision about five things: the case prompt, the stored response,
the target, the label set with its word cap, and the charter the annotator is
shown beside the case. Four of those live in the dataset. The fifth is composed
at render time from the roster, which is why `housecast#7166` exists: two
graders either side of a roster edit see different charters, every recorded
field matches, and the disagreement rate absorbs the difference and reports it
as disagreement between the people.

The gate this replaces asked a person to hold in their head which open tickets
reach which grade. This asks the bytes instead. A pin is taken when a run is
composed, and every grading surface checks it before showing a case.

Digests are per case and per entity rather than one roll-up, because a single
whole-run digest says a pass is invalid without saying what moved. Same reason
`evaluations/reflow-v3/board-2026-09-01/README.md` gives for attesting a board
per role rather than per bundle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from housecast.compose import digest
from housecast.grade.schema import AGENT_COMPOSE, LABEL_SETS, Challenge, DatasetEntry, Profile

# The five inputs, in the order the rule names them. `labels` covers the label
# set and the word cap together because one test type decides both.
CASE_INPUTS = ("prompt", "response", "target", "labels")
CHARTER_INPUT = "charter"


class PinMismatchError(Exception):
    """Raised where a surface must refuse rather than grade a changed input."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def charter_parts(roster: dict[str, Any] | None, entity: str) -> tuple[str, str, list[str]]:
    """The charter as its three pieces, for a surface that styles them differently."""
    spec = (roster or {}).get("entities", {}).get(entity)
    if not spec:
        return "", "", []
    notes = [str(note) for note in spec.get("notes", [])]
    return str(spec.get("display_name", entity)), str(spec.get("purpose", "")), notes


def charter_lines(roster: dict[str, Any] | None, entity: str) -> list[str]:
    """Exactly what `annotate.entity_header` puts in front of the grader, unstyled.

    Shared with the renderer rather than reimplemented, because a pin over a
    projection the renderer does not use is a pin over nothing. That is the
    class `agent-compose#7170` names: structure is checked against structure
    and the prose projection is not checked at all.
    """
    display, purpose, notes = charter_parts(roster, entity)
    if not display and not purpose and not notes:
        return []
    return [f"{display}  {purpose}", *notes]


def case_digests(entry: DatasetEntry, profile: Profile = AGENT_COMPOSE) -> dict[str, str]:
    challenge = entry.challenge
    asked: Any = challenge.prompt
    if challenge.turns:
        asked = [{"role": turn.role, "content": turn.content} for turn in challenge.turns]
    return {
        "prompt": digest(_canonical(asked)),
        "response": digest(entry.output),
        "target": digest(challenge.target or ""),
        "labels": digest(_canonical(_label_contract(challenge, profile))),
    }


def _label_contract(challenge: Challenge, profile: Profile) -> dict[str, Any]:
    """The label set and the word cap together, since one test type decides both.

    A test type the profile does not declare is recorded rather than raised.
    `housecast grade validate` is where that is reported, and a pin that threw
    here would replace a named problem with a traceback. Recording it also
    means the digest moves if the profile later declares the type, which is a
    change to the label set and belongs in the drift.
    """
    try:
        label_set = challenge.label_set(profile)
    except KeyError:
        return {"label_set": None, "undeclared_test_type": challenge.test_type}
    return {
        "label_set": label_set,
        "labels": {key: str(value) for key, value in sorted(LABEL_SETS[label_set].items())},
        "word_cap": challenge.word_cap(profile),
    }


def take(
    dataset: list[DatasetEntry],
    profile: Profile = AGENT_COMPOSE,
    roster: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The pin as it goes to disk. Sorted, so two takes of one run are byte-equal."""
    cases = {entry.id: case_digests(entry, profile) for entry in dataset}
    entities = sorted({entry.challenge.entity for entry in dataset})
    charters = {
        entity: digest(_canonical(charter_lines(roster, entity)))
        for entity in entities
        if charter_lines(roster, entity)
    }
    return {
        "profile": profile.name,
        "cases": {key: cases[key] for key in sorted(cases)},
        "charters": charters,
    }


@dataclass(frozen=True)
class Drift:
    """One input that moved. Named per case, because "the run is stale" is not actionable."""

    scope: str
    subject: str
    input: str

    def __str__(self) -> str:
        return f"{self.scope} {self.subject}: {self.input} changed since the pin was taken"


def verify(
    pinned: dict[str, Any],
    dataset: list[DatasetEntry],
    profile: Profile = AGENT_COMPOSE,
    roster: dict[str, Any] | None = None,
) -> list[Drift]:
    """Every input that no longer matches, rather than the first one found.

    A case dropped from the dataset is not drift. A case the pin never covered
    is, because grading it would produce a decision no pin describes.
    """
    current = take(dataset, profile, roster)
    drifts: list[Drift] = []

    if pinned.get("profile") != current["profile"]:
        drifts.append(Drift("profile", str(pinned.get("profile", "")), "name"))

    pinned_cases = pinned.get("cases", {})
    for case_id, digests in current["cases"].items():
        before = pinned_cases.get(case_id)
        if before is None:
            drifts.append(Drift("case", case_id, "not covered by the pin"))
            continue
        drifts.extend(
            Drift("case", case_id, name)
            for name in CASE_INPUTS
            if before.get(name) != digests[name]
        )

    pinned_charters = pinned.get("charters", {})
    for entity, value in current["charters"].items():
        before = pinned_charters.get(entity)
        if before is None:
            drifts.append(Drift("entity", entity, "not covered by the pin"))
        elif before != value:
            drifts.append(Drift("entity", entity, CHARTER_INPUT))

    # A charter the pin covered and the roster no longer renders is the same
    # hazard read from the other side: the grader now sees less than the pin says.
    drifts.extend(
        Drift("entity", entity, "no longer rendered")
        for entity in sorted(pinned_charters)
        if entity not in current["charters"]
    )
    return drifts


def check(
    pinned: dict[str, Any],
    dataset: list[DatasetEntry],
    profile: Profile = AGENT_COMPOSE,
    roster: dict[str, Any] | None = None,
) -> None:
    """Refuse, naming every input that moved and how to accept the change on purpose."""
    drifts = verify(pinned, dataset, profile, roster)
    if not drifts:
        return
    shown = "\n  ".join(str(drift) for drift in drifts[:20])
    more = f"\n  and {len(drifts) - 20} more" if len(drifts) > 20 else ""
    counted = "1 grade input" if len(drifts) == 1 else f"{len(drifts)} grade inputs"
    raise PinMismatchError(
        f"{counted} moved since this run was pinned:\n  {shown}{more}\n"
        "Grading across that change reports it as grader disagreement. "
        "Re-pin with `housecast grade pin --force` to accept it deliberately."
    )
