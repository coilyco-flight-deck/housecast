from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from housecast.room.models import Settings
from housecast.room.server import create_app
from housecast.room.store import Room
from housecast.room.tests.test_room import SUBJECTS, proxy

CFG = Settings(proxy="http://proxy", model="route", jev_model="jev")
TOKEN = {"X-Control-Token": "tok"}


def client(rate: float = 20.0) -> tuple[TestClient, Room]:
    room = Room(subjects=SUBJECTS)
    upstream = httpx.AsyncClient(transport=proxy({s["system"]: s["label"] for s in SUBJECTS}))
    app = create_app(room, CFG, "tok", rate_seconds=rate, client=upstream, page=None)
    return TestClient(app), room


def test_snapshot_shows_labels_never_system_prompts() -> None:
    tc, _ = client()
    with tc:
        body = tc.get("/api/room").json()
    assert body["subjects"] == [{"id": s["id"], "label": s["label"]} for s in SUBJECTS]
    assert body["rev"] == 0 and body["phase"] == "holding"


def test_intake_pick_and_grade_through_http() -> None:
    tc, room = client()
    with tc:
        assert tc.post("/api/prompts", json={"text": "early"}).status_code == 409
        assert tc.post("/api/control/phase", json={"phase": "submissions"}).status_code == 403
        tc.post("/api/control/phase", json={"phase": "submissions"}, headers=TOKEN)
        ok = tc.post("/api/prompts", json={"text": "favourite colour?"})
        assert ok.status_code == 201 and "id" in ok.json()
        again = tc.post("/api/prompts", json={"text": "again"})
        assert again.status_code == 429 and again.json()["reason"].startswith("one prompt")
        other = tc.post("/api/prompts", json={"text": "again", "device": "phone-2"})
        assert other.status_code == 201
        empty = tc.post("/api/prompts", json={"text": "", "device": "phone-3"})
        assert empty.status_code == 422 and empty.json() == {"reason": "the prompt is empty"}
        assert tc.post("/api/prompts", json={"text": "x" * 300}).status_code == 422
        assert tc.get("/api/control/room").status_code == 403
        assert tc.get("/api/control/room", headers=TOKEN).json()["phase"] == "submissions"
        pick = {"prompt_id": ok.json()["id"]}
        assert tc.post("/api/control/pick", json=pick, headers=TOKEN).json()["n"] == 1
        sheet = {"round": 1, "device": "d1", "grades": {"s1": "pass"}}
        assert tc.post("/api/grades", json=sheet).json() == {"graded": 1}
        late = tc.post("/api/prompts", json={"text": "hi", "device": "phone-4"})
        assert late.status_code == 409 and late.json() == {"reason": "submissions are not open"}
    assert room.prompts[0]["text"] == "favourite colour?"


def test_screen_view_withholds_unpicked_prompt_text() -> None:
    tc, _ = client()
    with tc:
        tc.post("/api/control/phase", json={"phase": "submissions"}, headers=TOKEN)
        tc.post("/api/prompts", json={"text": "secret prompt"})
        assert "text" not in tc.get("/api/room?view=screen").json()["prompts"][0]
        assert tc.get("/api/room").json()["prompts"][0]["text"] == "secret prompt"
        assert tc.get("/api/room/events?view=presenter").status_code == 403


def test_kit_css_is_served_from_the_present_page() -> None:
    tc, _ = client()
    with tc:
        reply = tc.get("/kit.css")
    assert reply.status_code == 200 and reply.headers["content-type"].startswith("text/css")
