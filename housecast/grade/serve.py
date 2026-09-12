"""The local grading session, served to a page instead of a terminal.

`export.py` projects a run one way onto a public display surface. This is the
other direction and is deliberately not that: it holds one run open for one
human on loopback, hands the page the grader-private fields, and writes every
decision straight back to `annotations.yaml`.

The split is the safety property rather than a layering preference. A built
artifact embeds the public export and can neither read a critique nor write a
label, so the file opened on a projector cannot leak one. Private text exists
only while this process runs. See docs/grading.md.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from housecast.grade.io import (
    annotations_name,
    load_annotations,
    load_dataset,
    save_annotations,
)
from housecast.grade.queue import load_queue, order_by_queue, queue_path
from housecast.grade.schema import (
    AGENT_COMPOSE,
    DEDUCTIONS,
    LABEL_SETS,
    Annotation,
    DatasetEntry,
    Profile,
    annotation_order,
    decode_label,
    pair_results,
)

if TYPE_CHECKING:  # fastapi rides the eval extra and is imported lazily
    from fastapi import FastAPI

# A new wire format takes this package's name rather than another `aos-eval.*`
# id. See docs/grading.md.
GRADING_FORMAT = "housecast.grading.v1"

DEFAULT_PORT = 8765

# `localhost` is here because a human types it. It resolves to loopback.
LOOPBACK_NAMES = frozenset({"localhost", ""})


class AnnotationRejectedError(Exception):
    """A decision the committed record will not accept. The page shows the reason."""


class BindRefusedError(Exception):
    """Raised instead of listening. The session payload is grader-private."""


def is_loopback(host: str) -> bool:
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_bind(host: str, expose: bool) -> None:
    """Refuse rather than warn, matching how the exporter treats a public target."""
    if is_loopback(host) or expose:
        return
    raise BindRefusedError(
        f"refusing to bind {host}, because the session payload carries the critique and "
        "evidence written for the grader. Pass --expose to accept that, or keep the "
        "default and reach it over loopback."
    )


class Decision(BaseModel):
    """One decision arriving from the page."""

    id: str
    label: str
    critique: str = ""
    evidence: str = ""


@dataclass
class GradingSession:
    """One run held open for one grader. Every decision lands on disk immediately."""

    run_dir: Path
    profile: Profile = AGENT_COMPOSE
    entries: list[DatasetEntry] = field(default_factory=list)
    annotations: dict[str, Annotation] = field(default_factory=dict)
    roster: dict[str, Any] | None = None
    grader: str | None = None

    @classmethod
    def open(
        cls,
        run_dir: Path,
        profile: Profile = AGENT_COMPOSE,
        roster: dict[str, Any] | None = None,
        grader: str | None = None,
        use_queue: bool = True,
    ) -> GradingSession:
        dataset_path = run_dir / "dataset.yaml"
        if not dataset_path.exists():
            raise FileNotFoundError(f"{run_dir} has no dataset.yaml, so there is nothing to grade")
        entity_order = list(roster.get("entity_order", [])) if roster else None
        entries = annotation_order(load_dataset(dataset_path), profile, entity_order)
        # Costs the charter locality annotation_order exists for, buys covering
        # the least stable cases first. docs/grading-surfaces.md carries why.
        ranked = queue_path(run_dir / "dataset.yaml")
        if use_queue and ranked.exists():
            entries, _ = order_by_queue(entries, load_queue(ranked))
        return cls(
            run_dir=run_dir,
            profile=profile,
            entries=entries,
            annotations=load_annotations(run_dir / annotations_name(grader)),
            roster=roster,
            grader=grader,
        )

    @property
    def annotations_path(self) -> Path:
        return self.run_dir / annotations_name(self.grader)

    def entry(self, case_id: str) -> DatasetEntry:
        for candidate in self.entries:
            if candidate.id == case_id:
                return candidate
        raise AnnotationRejectedError(f"this run holds no case {case_id!r}")

    def record(self, decision: Decision) -> Annotation:
        """Every rule the terminal loop enforces, enforced once here instead.

        The verbatim check is the one that changes character in a browser: the
        page anchors a span by selection rather than by retyping, so this stops
        being the guard that catches a typo and becomes the guard that catches a
        page sending a span from the wrong case.
        """
        entry = self.entry(decision.id)
        try:
            label = decode_label(decision.label)
        except ValueError as unknown:
            raise AnnotationRejectedError(f"{decision.label!r} is not a label") from unknown

        allowed = set(LABEL_SETS[entry.challenge.label_set(self.profile)].values())
        if label not in allowed:
            names = ", ".join(sorted(str(value) for value in allowed))
            raise AnnotationRejectedError(f"{entry.challenge.test_type} takes one of: {names}")
        if label in DEDUCTIONS and not decision.critique.strip():
            raise AnnotationRejectedError("a deduction needs a critique")
        if decision.evidence and decision.evidence.lower() not in entry.output.lower():
            raise AnnotationRejectedError("the evidence span is not verbatim in the output")

        annotation = Annotation(
            id=decision.id,
            label=label,
            critique=decision.critique,
            evidence=decision.evidence,
        )
        self.annotations[decision.id] = annotation
        save_annotations(self.annotations_path, self.annotations, self.grader)
        return annotation

    def case(self, entry: DatasetEntry) -> dict[str, Any]:
        """The challenge entire, plus what the page needs to grade it.

        Slugs travel. They are suppressed on the audience surface rather than
        withheld here, because the grader navigates the board by them.

        `seed` is the exception and it never travels. It is not a slug about the
        board: a deriver is free to seed a case with whatever identifies the
        thing it was built from, and `evaluations/self-report-2026-09-17` seeds
        each case with the source message's timestamp. Beside a withheld prompt
        that is a key back to the text somebody took out.

        Unconditional, and the conditional version is why. It first dropped the
        field only when `--expose` was passed, which reads as the safe default
        and is not one: a container binding loopback behind a proxy never passes
        that flag while being as public as anything else. The signal was the
        wrong one. Nothing reads this field on the way out, the page never
        renders it and `attributes.py` takes it from the dataset rather than the
        payload, so there is no case for sending it at all.
        """
        payload = entry.challenge.model_dump(mode="json", exclude_none=True)
        payload.pop("seed", None)
        annotation = self.annotations.get(entry.id)
        payload.update(
            output=entry.output,
            words=len(entry.output.split()),
            word_cap=entry.challenge.word_cap(self.profile),
            label_set=entry.challenge.label_set(self.profile),
            label=annotation.label.value if annotation else None,
            critique=annotation.critique if annotation else "",
            evidence=annotation.evidence if annotation else "",
        )
        return payload

    def profile_payload(self) -> dict[str, Any]:
        """Keystrokes travel, so one-key grading survives the move to a browser."""
        return {
            "name": self.profile.name,
            "group_by": self.profile.group_by,
            "test_types": [
                {
                    "name": spec.name,
                    "label_set": spec.label_set,
                    "word_cap": spec.word_cap,
                    "requires": list(spec.requires),
                }
                for spec in self.profile.test_types
            ],
            "label_sets": {
                name: [
                    {"key": key, "value": label.value, "deduction": label in DEDUCTIONS}
                    for key, label in keys.items()
                ]
                for name, keys in LABEL_SETS.items()
            },
        }

    def counts(self) -> dict[str, int]:
        """`annotated` is progress. `scored` is the denominator a rate may use.

        A non-score is a decision, so it advances progress, and it is not a
        verdict, so it never enters a rate. Reporting one number for both is
        how an instrument's blind spots get published as the subject's passes.
        """
        ids = {entry.id for entry in self.entries}
        mine = [self.annotations[key] for key in self.annotations if key in ids]
        non_scored = sum(1 for annotation in mine if annotation.is_non_score)
        return {
            "cases": len(self.entries),
            "annotated": len(mine),
            "scored": len(mine) - non_scored,
            "non_scored": non_scored,
        }

    def pairs(self) -> list[dict[str, Any]]:
        return [
            {
                "pair_id": pair.pair_id,
                "entity": pair.entity,
                "attribute": pair.attribute,
                "halves": {half: verdict.value for half, verdict in sorted(pair.halves.items())},
                "complete": pair.complete,
                "passed": pair.passed,
            }
            for pair in pair_results(self.entries, self.annotations)
        ]

    def payload(self) -> dict[str, Any]:
        """No secret scan here, unlike the exporter.

        That scan guards a public projection. This payload is the private side
        of the same run, on loopback, and refusing to show a grader her own
        board because a response quotes an email address would be the wrong
        instrument pointed at the wrong target.
        """
        return {
            "format": GRADING_FORMAT,
            "run": self.run_dir.name,
            "grader": self.grader,
            "profile": self.profile_payload(),
            "roster": self.roster or {},
            "counts": self.counts(),
            "pairs": self.pairs(),
            "cases": [self.case(entry) for entry in self.entries],
        }


NO_BUILD = """housecast grade serve is running and no page is mounted.

Point --static at a built grading page, or read the session directly:

    GET  /api/session      the run, the profile, and every current annotation
    POST /api/annotations  one decision: {"id", "label", "critique", "evidence"}
    GET  /api/health       liveness and the run being graded
"""


def create_app(session: GradingSession, static: Path | None = None) -> FastAPI:
    """API first, then the page, because a mount at / would shadow the routes."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import PlainTextResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="housecast grade", docs_url=None, redoc_url=None)

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "run": session.run_dir.name,
            "grader": session.grader,
            **session.counts(),
        }

    @app.get("/api/session")
    def read_session() -> dict[str, Any]:
        return session.payload()

    @app.post("/api/annotations")
    def write_annotation(decision: Decision) -> dict[str, Any]:
        try:
            annotation = session.record(decision)
        except AnnotationRejectedError as rejected:
            raise HTTPException(status_code=422, detail=str(rejected)) from rejected
        return {
            "saved": annotation.to_dict(),
            "counts": session.counts(),
            "pairs": session.pairs(),
        }

    if static is not None:
        app.mount("/", StaticFiles(directory=str(static), html=True), name="page")
    else:

        @app.get("/", response_class=PlainTextResponse)
        def no_build() -> str:
            return NO_BUILD

    return app


def serve(
    session: GradingSession,
    host: str = "127.0.0.1",
    port: int = DEFAULT_PORT,
    static: Path | None = None,
    expose: bool = False,
) -> None:
    import uvicorn

    check_bind(host, expose)
    uvicorn.run(create_app(session, static), host=host, port=port, log_level="warning")
