"""Fan one prompt out to every subject, then score how far apart they landed.

Each subject answers on its own task, so the room shows four clocks rather than
one spinner. Divergence runs once every answer is terminal, over the answers
that came back non-empty.
"""

from __future__ import annotations

import asyncio
import secrets
from typing import Any

import httpx

from housecast.room import models
from housecast.room.store import PHASES, TERMINAL, Room, now

MAX_PROMPT = 280
MAX_REASON = 140
VERDICTS = frozenset({"pass", "fail"})


class PromptRefusedError(Exception):
    """A request the room will not take. The page shows `reason` verbatim."""

    def __init__(self, reason: str, status: int = 422) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status


class Engine:
    def __init__(
        self, room: Room, cfg: models.Settings, client: httpx.AsyncClient, concurrency: int = 40
    ) -> None:
        self.room = room
        self.cfg = cfg
        self.client = client
        self._slots = asyncio.Semaphore(concurrency)
        self._tasks: set[asyncio.Task[None]] = set()

    def _spawn(self, coro: Any) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def validate(self, text: str) -> str:
        text = text.strip()
        if self.room.phase != "submissions":
            raise PromptRefusedError("submissions are not open", 409)
        if not text:
            raise PromptRefusedError("the prompt is empty")
        if len(text) > MAX_PROMPT:
            raise PromptRefusedError(f"the prompt is over {MAX_PROMPT} characters")
        return text

    def submit(self, text: str) -> dict[str, Any]:
        text = self.validate(text)
        prompt = {
            "id": secrets.token_hex(4),
            "seq": len(self.room.prompts) + 1,
            "text": text,
            "at": now(),
        }
        self.room.emit("prompt", prompt)
        self.room.emit("divergence", {"prompt_id": prompt["id"], "state": "pending"})
        for subject in self.room.subjects:
            self.room.emit(
                "answer",
                {"prompt_id": prompt["id"], "subject_id": subject["id"], "state": "queued"},
            )
            self._spawn(self._answer(prompt, subject))
        return prompt

    async def _answer(self, prompt: dict[str, Any], subject: dict[str, str]) -> None:
        base = {"prompt_id": prompt["id"], "subject_id": subject["id"]}
        async with self._slots:
            started = now()
            self.room.emit("answer", {**base, "state": "running", "started_at": started})
            try:
                text = await models.answer(self.client, self.cfg, subject["system"], prompt["text"])
            except Exception as failed:  # the room shows it, and the other subjects carry on
                self.room.emit(
                    "answer",
                    {
                        **base,
                        "state": "failed",
                        "started_at": started,
                        "finished_at": now(),
                        "reason": _reason(failed),
                    },
                )
            else:
                done: dict[str, Any] = {**base, "started_at": started, "finished_at": now()}
                if text:
                    done.update(state="done", text=text)
                else:
                    done.update(state="empty", reason="the subject returned no text")
                self.room.emit("answer", done)
        await self._maybe_score(prompt)

    async def _maybe_score(self, prompt: dict[str, Any]) -> None:
        answers = self.room.answers_for(prompt["id"])
        if len(answers) < len(self.room.subjects) or any(
            a["state"] not in TERMINAL for a in answers
        ):
            return
        if self.room.divergence.get(prompt["id"], {}).get("state") != "pending":
            return
        texts = [a["text"] for a in answers if a["state"] == "done"]
        base = {"prompt_id": prompt["id"]}
        if len(texts) < 2:
            self.room.emit(
                "divergence",
                {**base, "state": "failed", "reason": "fewer than two answers came back"},
            )
            return
        # Marked before the await, so two subjects finishing at once score once.
        self.room.divergence[prompt["id"]] = {**base, "state": "scoring"}
        try:
            score = await models.stance(self.client, self.cfg, prompt["text"], texts, prompt["id"])
            method = "stance"
        except Exception:  # lexical is the measured fallback, looser than Jev
            score, method = models.lexical(texts), "lexical"
        self.room.emit(
            "divergence", {**base, "state": "done", "score": round(score, 4), "method": method}
        )

    def set_phase(self, phase: str) -> None:
        if phase not in PHASES:
            raise PromptRefusedError(f"a phase is one of {', '.join(PHASES)}")
        self.room.emit("phase", {"phase": phase})

    def pick(self, prompt_id: str) -> dict[str, Any]:
        """Start the next round on one prompt. The pick is also the moderation filter."""
        if not any(p["id"] == prompt_id for p in self.room.prompts):
            raise PromptRefusedError("no such prompt")
        current = self.room.current
        round_ = {"n": (current["n"] + 1) if current else 1, "prompt_id": prompt_id}
        self.room.emit("round", round_)
        self.room.emit("phase", {"phase": "grading"})
        return round_

    def grade(self, n: int, device: str, marks: dict[str, str], reasons: dict[str, str]) -> int:
        current = self.room.current
        if self.room.phase != "grading" or current is None:
            raise PromptRefusedError("grading is not open", 409)
        if n != current["n"]:
            raise PromptRefusedError("that round is over", 409)
        if not device:
            raise PromptRefusedError("a grade needs a device token")
        known = {s["id"] for s in self.room.subjects}
        graded: dict[str, dict[str, str]] = {}
        for subject_id, verdict in marks.items():
            if subject_id not in known or verdict not in VERDICTS:
                raise PromptRefusedError("each grade is pass or fail for a known subject")
            mark = {"verdict": verdict}
            reason = reasons.get(subject_id, "").strip()
            if len(reason) > MAX_REASON:
                raise PromptRefusedError(f"a reason is at most {MAX_REASON} characters")
            if reason and verdict == "fail":
                mark["reason"] = reason
            graded[subject_id] = mark
        if not graded:
            raise PromptRefusedError("no grades were sent")
        self.room.emit("grades", {"n": n, "device": device, "grades": graded})
        return self.room.graded(n)

    def resume(self) -> int:
        """Re-run what a restart cut off, and re-score prompts left pending."""
        prompts = {p["id"]: p for p in self.room.prompts}
        subjects = {s["id"]: s for s in self.room.subjects}
        cut = self.room.unfinished()
        for answer in cut:
            prompt, subject = prompts.get(answer["prompt_id"]), subjects.get(answer["subject_id"])
            if prompt and subject:
                self.room.emit(
                    "answer",
                    {**{k: answer[k] for k in ("prompt_id", "subject_id")}, "state": "queued"},
                )
                self._spawn(self._answer(prompt, subject))
        for prompt in self.room.prompts:
            if self.room.divergence.get(prompt["id"], {}).get("state") in ("pending", "scoring"):
                self.room.divergence[prompt["id"]] = {"prompt_id": prompt["id"], "state": "pending"}
                self._spawn(self._maybe_score(prompt))
        return len(cut)

    async def drain(self) -> None:
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)


def _reason(failed: Exception) -> str:
    if isinstance(failed, httpx.TimeoutException):
        return "the subject timed out"
    if isinstance(failed, httpx.HTTPStatusError):
        return f"the model route answered {failed.response.status_code}"
    return "the subject could not be reached"
