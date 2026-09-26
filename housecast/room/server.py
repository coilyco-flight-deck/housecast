"""The room's HTTP surface: one snapshot, one event stream, intake, and control.

The event stream carries the same shapes as the snapshot, each with the `rev`
it produced, so a page that sees a gap re-reads the snapshot instead of
guessing. Refusals answer `{reason}` for the form to show verbatim.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from housecast.room.engine import Engine, PromptRefusedError
from housecast.room.models import Settings
from housecast.room.store import Room

DEFAULT_PORT = 8767
PAGE = Path(__file__).parent / "page"
KIT = Path(__file__).parent.parent / "grade" / "present_page" / "kit.css"
HEARTBEAT = 15.0


class Intake(BaseModel):
    text: str = ""
    device: str = ""


class GradeSheet(BaseModel):
    round: int
    device: str = ""
    grades: dict[str, str]
    reasons: dict[str, str] = {}


class PhaseChange(BaseModel):
    phase: str


class Pick(BaseModel):
    prompt_id: str


class RateLimit:
    """One prompt per client per window. A room, not a fortress: two devices count twice."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self._last: dict[str, float] = {}

    def allow(self, client: str) -> bool:
        stamp = time.monotonic()
        if stamp - self._last.get(client, -self.seconds) < self.seconds:
            return False
        self._last[client] = stamp
        return True


def client_of(request: Request) -> str:
    # Behind the ingress the peer is the proxy, so the first forwarded hop is the client.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_app(
    room: Room,
    cfg: Settings,
    control_token: str,
    rate_seconds: float = 20.0,
    client: httpx.AsyncClient | None = None,
    page: Path | None = PAGE,
) -> FastAPI:
    limit = RateLimit(rate_seconds)
    state: dict[str, Engine] = {}

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        owned = client is None
        http = client or httpx.AsyncClient()
        state["engine"] = Engine(room, cfg, http)
        state["engine"].resume()
        try:
            yield
        finally:
            if owned:
                await http.aclose()

    app = FastAPI(title="housecast room", docs_url=None, redoc_url=None, lifespan=lifespan)

    def presenter(token: str | None) -> None:
        if not token or not secrets.compare_digest(token, control_token):
            raise HTTPException(status_code=403, detail="the control token does not match")

    def view_of(view: str | None, token: str | None) -> str:
        if view == "presenter":
            presenter(token)
            return "presenter"
        return "screen" if view == "screen" else "attendee"

    @app.get("/api/room")
    def snapshot(view: str | None = None) -> dict[str, Any]:
        return room.snapshot(view_of(view, None) if view != "presenter" else "attendee")

    @app.get("/api/control/room")
    def presenter_snapshot(x_control_token: str | None = Header(default=None)) -> dict[str, Any]:
        presenter(x_control_token)
        return room.snapshot("presenter")

    @app.get("/api/room/events")
    async def events(
        request: Request, view: str | None = None, token: str | None = None
    ) -> StreamingResponse:
        # EventSource sends no headers, so the presenter stream takes a query token.
        queue = room.subscribe(view_of(view, token))

        async def stream() -> AsyncIterator[str]:
            try:
                yield f"event: hello\ndata: {json.dumps({'rev': room.rev})}\n\n"
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT)
                    except TimeoutError:
                        yield ": keepalive\n\n"
                        continue
                    frame = json.dumps(event)
                    yield f"event: {event['kind']}\nid: {event['rev']}\ndata: {frame}\n\n"
            finally:
                room.unsubscribe(queue)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    def refuse(refused: PromptRefusedError) -> JSONResponse:
        return JSONResponse({"reason": refused.reason}, refused.status)

    @app.post("/api/prompts", status_code=201, response_model=None)
    async def submit(intake: Intake, request: Request) -> dict[str, Any] | JSONResponse:
        try:
            state["engine"].validate(intake.text)
            if not limit.allow(intake.device or client_of(request)):
                return JSONResponse({"reason": "one prompt at a time: wait a moment"}, 429)
            prompt = state["engine"].submit(intake.text)
        except PromptRefusedError as refused:
            return refuse(refused)
        return {"id": prompt["id"]}

    @app.post("/api/grades", response_model=None)
    def grade(sheet: GradeSheet) -> dict[str, Any] | JSONResponse:
        try:
            graded = state["engine"].grade(sheet.round, sheet.device, sheet.grades, sheet.reasons)
        except PromptRefusedError as refused:
            return refuse(refused)
        return {"graded": graded}

    @app.post("/api/control/phase", response_model=None)
    def set_phase(
        change: PhaseChange, x_control_token: str | None = Header(default=None)
    ) -> dict[str, Any] | JSONResponse:
        presenter(x_control_token)
        try:
            state["engine"].set_phase(change.phase)
        except PromptRefusedError as refused:
            return refuse(refused)
        return {"phase": room.phase}

    @app.post("/api/control/pick", response_model=None)
    def pick(
        choice: Pick, x_control_token: str | None = Header(default=None)
    ) -> dict[str, Any] | JSONResponse:
        presenter(x_control_token)
        try:
            return state["engine"].pick(choice.prompt_id)
        except PromptRefusedError as refused:
            return refuse(refused)

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"ok": True, "rev": room.rev}

    if KIT.exists():

        @app.get("/kit.css")
        def kit() -> FileResponse:
            return FileResponse(KIT, media_type="text/css")

    if page is not None and page.is_dir():
        for route, name in (("/screen", "screen.html"), ("/present", "present.html")):
            if (page / name).exists():
                app.add_api_route(route, _file(page / name), include_in_schema=False)
        app.mount("/", StaticFiles(directory=str(page), html=True), name="page")

    return app


def _file(path: Path) -> Any:
    def send() -> FileResponse:
        return FileResponse(path, media_type="text/html")

    return send


def serve(
    room: Room, cfg: Settings, control_token: str, host: str, port: int, rate_seconds: float
) -> None:
    import uvicorn

    uvicorn.run(
        create_app(room, cfg, control_token, rate_seconds),
        host=host,
        port=port,
        log_level="warning",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
