"""The subject's fixture state: a small media library and a job table.

Deterministic on purpose. A job advances by poll count rather than by wall
clock, so a run at concurrency 8 and a run at concurrency 1 see the same number
of polls, and `efficiency` measures the model rather than the machine.
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field

# Two polls before a job completes. Enough that a model must poll at all, few
# enough that a correct one is not punished for the subject being slow.
POLLS_UNTIL_DONE = 2


@dataclass(frozen=True)
class Asset:
    """One file the library knows about."""

    path: str
    duration_seconds: int
    has_audio: bool
    width: int
    height: int


LIBRARY: dict[str, Asset] = {
    "/media/lecture.mp4": Asset("/media/lecture.mp4", 2400, True, 1920, 1080),
    "/media/interview.mov": Asset("/media/interview.mov", 1810, True, 1280, 720),
    "/media/standup-2026-09-02.mp4": Asset("/media/standup-2026-09-02.mp4", 902, True, 1920, 1080),
    "/media/keynote.webm": Asset("/media/keynote.webm", 3605, True, 3840, 2160),
    "/media/b-roll-skyline.mp4": Asset("/media/b-roll-skyline.mp4", 45, False, 3840, 2160),
    "/media/podcast-ep12.wav": Asset("/media/podcast-ep12.wav", 4210, True, 0, 0),
}

TRANSCRIPTS: dict[str, str] = {
    "/media/lecture.mp4": (
        "Good morning. Today we are covering cache coherence, and specifically why "
        "the invalidation protocol most textbooks show you is not the one your "
        "processor runs..."
    ),
    "/media/interview.mov": (
        "Thanks for making the time. I want to start with the migration, because "
        "everyone I have spoken to describes it differently..."
    ),
    "/media/standup-2026-09-02.mp4": (
        "Quick one today. The ingest queue drained overnight, the backfill is at "
        "eighty percent, and I am blocked on the credential rotation..."
    ),
    "/media/keynote.webm": (
        "It is good to be back. Three years ago on this stage we said the hard part "
        "was not the model, it was everything around it..."
    ),
    "/media/podcast-ep12.wav": (
        "Welcome back to episode twelve. My guest today has spent a decade building "
        "storage systems nobody is supposed to notice..."
    ),
}


@dataclass
class Job:
    """One asynchronous transcription, advanced by polling rather than by time."""

    job_id: str
    media_id: str
    polls: int = 0

    @property
    def state(self) -> str:
        return "completed" if self.polls >= POLLS_UNTIL_DONE else "running"


@dataclass
class Library:
    """Subject state, shared by every connection to one subject process.

    Identifiers are random rather than sequential, and that is the isolation
    mechanism rather than a detail. Streamable HTTP as this SDK serves it hands
    a tool no stable per-connection key - measured 2026-09-16, three calls on
    one client session produced three different session objects and no
    `mcp-session-id` header - so per-prompt state cannot be keyed on the
    connection.

    Sequential ids would make that fatal: a model that skipped `media_register`
    and guessed `med_0001` would succeed on a registration some other prompt
    made, and at concurrency 8 whether it succeeded would not even be
    deterministic. With `med_<12 hex>` the only way to hold an id is to have
    been given it, so sharing the table costs nothing a grade can see. Two
    prompts registering one path share an id, which is what a real library does.
    """

    _registered: dict[str, str] = field(default_factory=dict)
    _by_id: dict[str, str] = field(default_factory=dict)
    _jobs: dict[str, Job] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def register(self, path: str) -> tuple[str, bool]:
        """Return `(media_id, already_registered)`.

        Idempotent by path, because a tool that mints a second id for a file it
        already holds is a defect in the subject rather than a case worth
        grading a model on.
        """
        with self._lock:
            existing = self._registered.get(path)
            if existing is not None:
                return existing, True
            media_id = f"med_{secrets.token_hex(6)}"
            self._registered[path] = media_id
            self._by_id[media_id] = path
            return media_id, False

    def path_for(self, media_id: str) -> str | None:
        with self._lock:
            return self._by_id.get(media_id)

    def is_registered(self, path: str) -> bool:
        with self._lock:
            return path in self._registered

    def start_job(self, media_id: str) -> str:
        with self._lock:
            job_id = f"job_{secrets.token_hex(6)}"
            self._jobs[job_id] = Job(job_id=job_id, media_id=media_id)
            return job_id

    def poll(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.polls += 1
            return job
