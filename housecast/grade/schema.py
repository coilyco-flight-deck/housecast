"""The shared contract between an science runner and the humans who grade it.

Vocabulary follows the references where they have a word for something. Challenge,
dataset, and target are Inspect's. Test type is CheckList's. Annotation, label,
and critique are Phoenix's and Hamel's.

Nothing here imports a runner or a model client. Two repos run evals very
differently (a two-input composed-prompt call, and a live harness turn against
a real tool roster) and both emit this shape. A `Profile` carries the part that
is genuinely per-deployment, so the taxonomy is config rather than code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class Half(StrEnum):
    IN = "in"
    OUT = "out"


class Verdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class Fit(StrEnum):
    FIT = "fit"
    UNDECIDED = "undecided"
    NO_FIT = "does-not-fit"


# Phoenix configures its annotation rubric as data rather than hardcoding it.
# Each entry binds a keystroke to a categorical label.
LABEL_SETS: dict[str, dict[str, Verdict | Fit]] = {
    "binary": {"p": Verdict.PASS, "x": Verdict.FAIL},
    "fit": {"f": Fit.FIT, "u": Fit.UNDECIDED, "n": Fit.NO_FIT},
}

DEDUCTIONS: frozenset[Verdict | Fit] = frozenset({Verdict.FAIL, Fit.NO_FIT, Fit.UNDECIDED})

DEFAULT_WORD_CAP = 100


@dataclass(frozen=True)
class TestTypeSpec:
    """One column of the CheckList grid, as the deployment defines it."""

    name: str
    label_set: str = "binary"
    word_cap: int = DEFAULT_WORD_CAP
    # Challenge fields a case of this type cannot omit. A missing field here is a
    # case that looks graded and is not.
    requires: tuple[str, ...] = ()

    # CheckList's noun, not pytest's. Keeps collection off the class.
    __test__ = False


@dataclass(frozen=True)
class Profile:
    """Everything about the taxonomy that is a deployment's business.

    `test_types` is ordered, and that order is the annotation order inside one
    group. Declaring a profile is how a second repo adopts this schema without
    the schema growing a branch for it.
    """

    name: str
    test_types: tuple[TestTypeSpec, ...]
    entity_order: tuple[str, ...] = ()
    attribute_order: tuple[str, ...] = ()

    def spec(self, test_type: str) -> TestTypeSpec:
        for candidate in self.test_types:
            if candidate.name == test_type:
                return candidate
        raise KeyError(f"{self.name} declares no test type {test_type!r}")

    def rank(self, test_type: str) -> int:
        names = [spec.name for spec in self.test_types]
        return names.index(test_type) if test_type in names else len(names)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Profile:
        return cls(
            name=str(raw["name"]),
            test_types=tuple(
                TestTypeSpec(
                    name=str(entry["name"]),
                    label_set=str(entry.get("label_set", "binary")),
                    word_cap=int(entry.get("word_cap", DEFAULT_WORD_CAP)),
                    requires=tuple(str(f) for f in entry.get("requires", ())),
                )
                for entry in raw.get("test_types", [])
            ),
            entity_order=tuple(str(e) for e in raw.get("entity_order", ())),
            attribute_order=tuple(str(a) for a in raw.get("attribute_order", ())),
        )


# Below 50 words the suggest-external-comms out-half drops the factual handoff,
# which the boundary requires. Measured against written example responses.
AGENT_COMPOSE = Profile(
    name="agent-compose",
    test_types=(
        TestTypeSpec("boundary", "binary", 50, ("attribute", "half", "pair_id")),
        TestTypeSpec("role-fit", "binary", 50, ("attribute",)),
        TestTypeSpec("personality", "fit", 100, ("attribute",)),
    ),
    attribute_order=(
        "build-foundational-software",
        "modify-live-backend",
        "suggest-external-comms",
        "seek-external-validation",
    ),
)


class Turn(BaseModel):
    """One message in a challenge's transcript. `role` is speaker, not entity."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    role: str
    content: str


class Challenge(BaseModel):
    """One question put to the subject, and a target saying what passing means.

    A roster derives it unwritten, carrying only what the roster knows, and a
    human writes the prompt into it. Both states are one type, so `written` is
    the gate rather than a second model. See docs/grading.md.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    # What is under test. A composed role in one deployment, a deployed agent
    # in another, so the shared layer names the abstraction rather than either.
    entity: str
    # Which kind of attribute this challenge tests.
    test_type: str
    # What is being tested about the entity. The deployment's own word for it
    # belongs in its profile rather than in this schema. See docs/grading.md.
    attribute: str | None = None
    # The question, as one string or as a transcript ending on the turn under
    # test. A deployment whose subject is conversational needs the second.
    prompt: str | None = None
    turns: tuple[Turn, ...] = ()
    target: str | None = None
    half: Half | None = None
    pair_id: str | None = None
    # An expectation on the answer's shape rather than its prose, checked by
    # the runner and carried as a note. See docs/grading.md.
    required_tool: str = ""
    seed: str = ""

    @property
    def asked(self) -> bool:
        """A challenge carries its question either way, never both and never neither."""
        return bool(self.prompt) != bool(self.turns)

    @property
    def written(self) -> bool:
        return self.asked and bool(self.target)

    @model_validator(mode="after")
    def _check_pairing(self) -> Challenge:
        if bool(self.half) != bool(self.pair_id):
            raise ValueError(f"{self.id}: half and pair_id travel together or not at all")
        return self

    def check_against(self, profile: Profile) -> list[str]:
        """Profile-level shape, kept off the validator so a Challenge stays portable."""
        try:
            spec = profile.spec(self.test_type)
        except KeyError as unknown:
            return [str(unknown)]
        missing = [name for name in spec.requires if getattr(self, name, None) is None]
        if not self.asked:
            missing.append("prompt or turns, never both")
        elif not self.target:
            missing.append("target")
        return [f"{self.id}: {self.test_type} challenge needs {name}" for name in missing]

    def label_set(self, profile: Profile) -> str:
        return profile.spec(self.test_type).label_set

    def word_cap(self, profile: Profile) -> int:
        return profile.spec(self.test_type).word_cap


class Response(BaseModel):
    """One run of one challenge. Inspect calls the repetition an epoch."""

    model_config = ConfigDict(frozen=True)

    challenge_id: str
    epoch: int
    text: str
    finish_reason: str = "stop"
    # Reasoning models return this beside the answer. Preserved as evidence,
    # never annotated, and never counted against the word cap.
    reasoning: str = ""
    model: str = ""
    outcome: str = ""
    tools: tuple[str, ...] = ()

    @property
    def words(self) -> int:
        return len(self.text.split())


class RunRecord(BaseModel):
    """A challenge measured over N runs, for a runner that scores intermittency.

    A single-run board has no use for this. A live-harness board cannot report
    without it, because the defect it hunts appears in 2 runs out of 10.
    """

    model_config = ConfigDict(frozen=True)

    challenge_id: str
    runs: int
    passed: int = 0
    failed: int = 0
    errors: int = 0
    max_failure_rate: float = 0.0
    responses: tuple[Response, ...] = ()

    @property
    def failure_rate(self) -> float:
        return self.failed / self.runs if self.runs else 0.0

    @property
    def breached(self) -> bool:
        return self.failure_rate > self.max_failure_rate


class Provenance(BaseModel):
    """What produced a run. A board without this is a number with no origin."""

    model_config = ConfigDict(frozen=True, extra="allow")

    definition: str = ""
    model: str = ""
    transport: str = ""
    substrate: str = ""
    composed: str = ""
    generated_at: str = ""


class DatasetEntry(BaseModel):
    """A written challenge carrying the output to annotate."""

    model_config = ConfigDict(frozen=True)

    challenge: Challenge
    output: str

    @model_validator(mode="after")
    def _check_written(self) -> DatasetEntry:
        if not self.challenge.written:
            raise ValueError(f"{self.challenge.id}: an unwritten challenge cannot be annotated")
        return self

    @property
    def id(self) -> str:
        return self.challenge.id

    def to_dict(self) -> dict[str, Any]:
        """Flattened so a dataset file reads as one record per challenge."""
        payload = self.challenge.model_dump(mode="json", exclude_none=True)
        payload["output"] = self.output
        return payload

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> DatasetEntry:
        return cls(challenge=Challenge.model_validate(raw), output=str(raw["output"]))


class Annotation(BaseModel):
    """One human decision. A critique is recorded only on a deduction.

    RULERS anchors every score to a verbatim quote from the input. `evidence`
    carries that span so a critique is auditable rather than impressionistic.
    """

    id: str
    label: Verdict | Fit
    critique: str = ""
    evidence: str = ""

    @property
    def is_deduction(self) -> bool:
        return self.label in DEDUCTIONS

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"id": self.id, "label": self.label.value}
        if self.critique:
            payload["critique"] = self.critique
        if self.evidence:
            payload["evidence"] = self.evidence
        return payload


@dataclass
class PairResult:
    """One paired attribute. The pair is the scoring unit, never the half."""

    pair_id: str
    entity: str
    attribute: str
    halves: dict[str, Verdict] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return {"in", "out"} <= self.halves.keys()

    @property
    def passed(self) -> bool:
        return self.complete and all(v is Verdict.PASS for v in self.halves.values())


def decode_label(value: str) -> Verdict | Fit:
    try:
        return Verdict(value)
    except ValueError:
        return Fit(value)


def annotation_order(
    dataset: list[DatasetEntry],
    profile: Profile = AGENT_COMPOSE,
    entity_order: list[str] | None = None,
) -> list[DatasetEntry]:
    """Entity-major, so an annotator holds one charter across that entity's challenges.

    Test-type-major degrades more gracefully, but annotation is resumable and
    entity context is the expensive thing to reload.
    """
    order = list(entity_order or profile.entity_order) or sorted(
        {entry.challenge.entity for entry in dataset}
    )
    attributes = list(profile.attribute_order)

    def key(entry: DatasetEntry) -> tuple[int, int, int, str]:
        challenge = entry.challenge
        entity_rank = order.index(challenge.entity) if challenge.entity in order else len(order)
        attribute_rank = (
            attributes.index(challenge.attribute) if challenge.attribute in attributes else 0
        )
        return (entity_rank, profile.rank(challenge.test_type), attribute_rank, entry.id)

    return sorted(dataset, key=key)


def pair_results(
    dataset: list[DatasetEntry], annotations: dict[str, Annotation]
) -> list[PairResult]:
    """Every pair the dataset declares, scored only where both halves are graded."""
    pairs: dict[str, PairResult] = {}
    for entry in dataset:
        challenge = entry.challenge
        if challenge.pair_id is None or challenge.half is None:
            continue
        annotation = annotations.get(entry.id)
        if annotation is None or not isinstance(annotation.label, Verdict):
            continue
        pair = pairs.setdefault(
            challenge.pair_id,
            PairResult(
                pair_id=challenge.pair_id,
                entity=challenge.entity,
                attribute=challenge.attribute or "",
            ),
        )
        pair.halves[challenge.half.value] = annotation.label
    return sorted(pairs.values(), key=lambda pair: pair.pair_id)
