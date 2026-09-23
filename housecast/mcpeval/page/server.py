"""The visual flow's HTTP surface, the customer product rather than the annotator.

It imports nothing from `housecast.grade.page`, so moving it is a directory move. A run
is launched and left, never blocked on. The blind read lives here, not in the client:
`/api/compare` returns the arms as A and B in a server-chosen order and hands back the
mapping only once a judgement is committed.
"""

from __future__ import annotations

import asyncio
import pathlib
import random
import secrets
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from housecast.mcpeval import config as cfg
from housecast.mcpeval import store, triage
from housecast.mcpeval.compare import ComparisonError, DecisionRule, compare
from housecast.mcpeval.definitions import DefinitionError, DefinitionSet, ToolProse, baseline_from
from housecast.mcpeval.models import ModelConfig
from housecast.mcpeval.run import RunConfig, execute
from housecast.mcpeval.runner import advertised_tools
from housecast.mcpeval.subject.server import SUBJECT_VERSION
from housecast.mcpeval.task import available, load_slug

HERE = pathlib.Path(__file__).parent


class EditRequest(BaseModel):
    parent: str
    tool: str
    description: str
    author: str = "human:tester"
    label: str = ""


class ValidateRequest(BaseModel):
    parent: str
    tool: str
    description: str


class RunRequest(BaseModel):
    task: str
    definitions: str = ""
    label: str = ""
    concurrency: int = 8


class JudgeRequest(BaseModel):
    token: str
    verdict: str
    note: str = ""


class _Live:
    """One in-flight run, so the interface can poll rather than block."""

    def __init__(self, run_id: str, task: str, total: int, label: str) -> None:
        self.run_id = run_id
        self.task = task
        self.total = total
        self.label = label
        self.done = 0
        self.finished_id: str | None = None
        self.error = ""


def build_app(root: pathlib.Path | None = None) -> FastAPI:
    app = FastAPI(title="the loop")
    live: dict[str, _Live] = {}
    blinds: dict[str, dict[str, Any]] = {}
    # A task nobody holds a reference to is collectable mid-run, and the run
    # would vanish with no error anywhere. The handle owns it for its lifetime.
    running: set[asyncio.Task[None]] = set()

    def _defs(digest_or_empty: str) -> DefinitionSet:
        if not digest_or_empty:
            raise HTTPException(400, "no definition set named")
        path = (root or store.DEFAULT_ROOT) / "definitions" / f"{digest_or_empty}.json"
        if not path.is_file():
            raise HTTPException(404, f"no definition set {digest_or_empty}")
        return store.load_definitions(path)

    @app.get("/api/state")
    def state() -> dict[str, Any]:
        tasks = []
        for path in available():
            task = load_slug(path.stem)
            tasks.append(
                {
                    "slug": task.slug,
                    "title": task.title,
                    "capability": task.capability,
                    "prompts": len(task.prompts),
                }
            )
        sets = []
        for path in store.definitions(root):
            defs = store.load_definitions(path)
            sets.append(
                {
                    "digest": defs.short(),
                    "label": defs.label,
                    "authored_by": defs.authored_by,
                    "parent": (defs.parent or "").removeprefix("sha256:")[:12],
                }
            )
        runs = []
        for path in store.runs(root):
            done = store.load_run(path)
            runs.append(
                {
                    "run_id": done.run_id,
                    "task": done.task,
                    "definitions": done.definition_digest.removeprefix("sha256:")[:12],
                    "label": done.definition_label,
                    "mean": done.mean_score,
                    "started_at": done.started_at,
                    "seconds": round(done.duration_seconds, 1),
                    "scored": len(done.scored),
                    "errored": len(done.errored),
                }
            )
        return {
            "tasks": tasks,
            "definitions": sets,
            "runs": runs,
            "subject": {"url": cfg.subject_url(), "version": SUBJECT_VERSION},
            "model": {"name": cfg.model_name(), "base_url": cfg.model_base_url()},
            "live": [
                {
                    "run_id": item.run_id,
                    "task": item.task,
                    "done": item.done,
                    "total": item.total,
                    "label": item.label,
                    "finished": item.finished_id,
                    "error": item.error,
                }
                for item in live.values()
            ],
        }

    @app.get("/api/task/{slug}")
    def task(slug: str) -> dict[str, Any]:
        loaded = load_slug(slug)
        return {
            "slug": loaded.slug,
            "title": loaded.title,
            "capability": loaded.capability,
            "prompts": [{"id": p.id, "text": p.text} for p in loaded.prompts],
        }

    @app.post("/api/baseline")
    async def baseline() -> dict[str, Any]:
        from mcp.client.client import Client

        async with Client(cfg.subject_url()) as subject:
            advertised = await advertised_tools(subject)
        defs = baseline_from(advertised, authored_by="human:tester")
        store.save_definitions(defs, root)
        return _definition_payload(defs)

    @app.get("/api/definitions/{digest}")
    def definitions(digest: str) -> dict[str, Any]:
        return _definition_payload(_defs(digest))

    @app.post("/api/validate")
    def validate(request: ValidateRequest) -> dict[str, Any]:
        parent = _defs(request.parent)
        try:
            child = parent.edited(
                tool=request.tool, description=request.description, authored_by="human:tester"
            )
        except DefinitionError as exc:
            return {"ok": False, "notes": [str(exc)], "digest": "", "unchanged": False}
        return {
            "ok": True,
            "notes": child.validate(),
            "digest": child.short(),
            "unchanged": child.digest == parent.digest,
            "diff": parent.diff(child),
        }

    @app.post("/api/edit")
    def edit(request: EditRequest) -> dict[str, Any]:
        parent = _defs(request.parent)
        try:
            child = parent.edited(
                tool=request.tool,
                description=request.description,
                authored_by=request.author,
                label=request.label,
            )
        except DefinitionError as exc:
            raise HTTPException(400, str(exc)) from exc
        if child.digest == parent.digest:
            raise HTTPException(
                400,
                "this is the prose already under test, so it is the same version rather "
                "than a new one. An edit and a revert collide with their origin on purpose.",
            )
        store.save_definitions(child, root)
        return _definition_payload(child)

    @app.post("/api/run")
    async def start(request: RunRequest) -> dict[str, Any]:
        loaded = load_slug(request.task)
        defs = _defs(request.definitions) if request.definitions else None
        if defs is None:
            from mcp.client.client import Client

            async with Client(cfg.subject_url()) as subject:
                defs = baseline_from(await advertised_tools(subject), authored_by="human:tester")
            store.save_definitions(defs, root)
        handle = _Live(
            run_id=f"pending_{secrets.token_hex(4)}",
            task=loaded.slug,
            total=len(loaded.prompts),
            label=defs.label or defs.short(),
        )
        live[handle.run_id] = handle

        async def go() -> None:
            def progress(done: int, total: int, trial: object) -> None:
                handle.done = done

            try:
                run = await execute(
                    loaded,
                    defs,
                    RunConfig(
                        subject_url=cfg.subject_url(),
                        model=ModelConfig(
                            base_url=cfg.model_base_url(),
                            model=cfg.model_name(),
                            api_key=cfg.api_key(),
                            temperature=0.0,
                            seed=7,
                        ),
                        concurrency=request.concurrency,
                        subject_version=SUBJECT_VERSION,
                    ),
                    on_progress=progress,
                )
                store.save_run(run, root)
                handle.finished_id = run.run_id
            except Exception as exc:  # a failed run is a state, not a crash
                handle.error = f"{type(exc).__name__}: {exc}"

        task = asyncio.create_task(go())
        running.add(task)
        task.add_done_callback(running.discard)
        return {"pending": handle.run_id, "total": handle.total}

    @app.get("/api/run/{run_id}")
    def run_detail(run_id: str) -> dict[str, Any]:
        path = (root or store.DEFAULT_ROOT) / "runs" / f"{run_id}.json"
        if not path.is_file():
            raise HTTPException(404, f"no run {run_id}")
        loaded = store.load_run(path)
        queue = triage.build(loaded)
        return {
            "run": {
                "run_id": loaded.run_id,
                "task": loaded.task,
                "definitions": loaded.definition_digest.removeprefix("sha256:")[:12],
                "label": loaded.definition_label,
                "authored_by": loaded.definition_authored_by,
                "mean": loaded.mean_score,
                "seconds": round(loaded.duration_seconds, 1),
                "fingerprint": dict(loaded.fingerprint),
                "scored": len(loaded.scored),
                "errored": len(loaded.errored),
            },
            "queue": queue.as_dict(),
            "prompts": [
                {
                    "prompt_id": trial.prompt_id,
                    "prompt": trial.prompt,
                    "answer": trial.answer,
                    "calls": [call.as_dict() for call in trial.calls],
                    "turns": trial.turns,
                    "finished": trial.finished,
                    "duration_ms": trial.duration_ms,
                    "grade": loaded.by_prompt[trial.prompt_id].as_dict(),
                }
                for trial in loaded.trials
            ],
        }

    @app.get("/api/compare")
    def comparison(before: str, after: str, threshold: float = 0.25) -> Any:
        root_dir = root or store.DEFAULT_ROOT
        try:
            lhs = store.load_run(root_dir / "runs" / f"{before}.json")
            rhs = store.load_run(root_dir / "runs" / f"{after}.json")
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        try:
            report = compare(lhs, rhs, DecisionRule(regression_threshold=threshold))
        except ComparisonError as exc:
            return JSONResponse({"refused": str(exc)}, status_code=409)
        payload = report.as_dict()
        # The blind read: the person judging the prose wrote it one step ago,
        # so the arms go out unlabelled in an order the server chose.
        token = secrets.token_hex(8)
        flipped = random.random() < 0.5
        blinds[token] = {"before": before, "after": after, "flipped": flipped, "judged": None}
        payload["blind"] = {
            "token": token,
            "arm_a": "arm A",
            "arm_b": "arm B",
            "note": (
                "Which arm is the edit is hidden until you commit a judgement. "
                "You wrote the change one step ago, and that is the bias this removes."
            ),
        }
        for delta in payload["deltas"]:
            lo, hi = delta["before"], delta["after"]
            delta["arm_a"], delta["arm_b"] = (hi, lo) if flipped else (lo, hi)
            delta.pop("before")
            delta.pop("after")
            delta.pop("delta")
            delta.pop("direction")
        for key in (
            "improved",
            "regressed",
            "held",
            "p_value",
            "decision",
            "underpowered",
            "past_threshold",
            "before_label",
            "after_label",
        ):
            payload.pop(key, None)
        return payload

    @app.post("/api/compare/judge")
    def judge(request: JudgeRequest) -> dict[str, Any]:
        record = blinds.get(request.token)
        if record is None:
            raise HTTPException(404, "no blind read by that token")
        record["judged"] = {"verdict": request.verdict, "note": request.note}
        root_dir = root or store.DEFAULT_ROOT
        lhs = store.load_run(root_dir / "runs" / f"{record['before']}.json")
        rhs = store.load_run(root_dir / "runs" / f"{record['after']}.json")
        report = compare(lhs, rhs, DecisionRule())
        payload = report.as_dict()
        payload["judged"] = record["judged"]
        payload["arm_a_was"] = "after" if record["flipped"] else "before"
        payload["queue"] = triage.build(
            rhs, moved=[d.prompt_id for d in report.deltas if d.direction != "held"]
        ).as_dict()
        return payload

    def _definition_payload(defs: DefinitionSet) -> dict[str, Any]:
        return {
            "digest": defs.short(),
            "label": defs.label,
            "authored_by": defs.authored_by,
            "parent": (defs.parent or "").removeprefix("sha256:")[:12],
            "instructions": defs.instructions,
            "notes": defs.validate(),
            "tools": [
                {
                    "name": name,
                    "description": defs.tools[name].description,
                    "parameters": dict(defs.tools[name].parameters),
                }
                for name in sorted(defs.tools)
            ],
        }

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(HERE / "index.html")

    app.mount("/static", StaticFiles(directory=HERE), name="static")
    return app


__all__ = ["ToolProse", "build_app"]
