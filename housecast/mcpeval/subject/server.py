"""The subject: five media tools whose descriptions are deliberately flawed.

This stands in for the customer's Node server, which is not available. It is a
real HTTP MCP server rather than a mock, because the loop's whole claim is that
the subject can be any language behind HTTP and housecast never notices.

The flaws are the demo. Each is a documented failure shape, and each is
reachable by a prose edit alone, so a tester can actually fix one and watch the
number move:

* `media_analyze` is over-broad. It says it extracts "text, speech, metadata and
  content" and in fact returns only metadata, so it wins a transcription
  selection it should lose.
* `media_transcribe` buries its precondition. It needs a `media_id` from
  `media_register`, and that sentence sits at the end of a long paragraph after
  three sentences of unrelated capability prose.
* `media_register` never says it is a prerequisite for anything, so a model with
  a file path in hand has no reason to call it first.
* `media_job_status` never names its terminal states, so a model either stops
  polling while the job still runs or polls past completion.
* `media_convert` gives no unit or format for `ratio`, so a model guesses
  between "16:9" and 1.7778.

Nothing here is secret from the model: it is shown these descriptions. What it
is never shown is the correctness rule, which lives in the task file and is
never sent over the wire. Grading material naming the expected calls would
measure whether the agent can read the answer key.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from housecast.mcpeval.subject.state import LIBRARY, TRANSCRIPTS, Library

# Recorded on every trial, so a comparison across two subject versions is
# refused rather than averaged.
SUBJECT_VERSION = "mediakit-0.4.2"

_ANALYZE = (
    "Analyze a media file and extract information from it. Handles video and "
    "audio in all common containers and codecs. Returns text, speech, metadata "
    "and content details for the file you point it at. Use this whenever you "
    "need to know what is in a piece of media."
)

_TRANSCRIBE = (
    "Produce a written transcript of the speech in a media file. Supports "
    "sixty-one languages with automatic detection, speaker diarization for up "
    "to eight distinct voices, and word-level timestamps suitable for subtitle "
    "generation. Output is returned as plain text by default and can be "
    "requested as WebVTT or SRT instead. Long files are processed "
    "asynchronously and the call returns a job identifier rather than a "
    "transcript. Takes a media_id."
)

_REGISTER = "Add a file to the media library and return an identifier for it."

_JOB_STATUS = "Check on a job that was started earlier."

_CONVERT = (
    "Change the aspect ratio of a video, padding or cropping as needed to reach "
    "the requested shape."
)


def build(library: Library | None = None) -> MCPServer:
    """One subject instance over one fixture table.

    Identifiers are unguessable, which is what keeps concurrent prompts from
    reading each other - see `state.Library`. The table itself is shared,
    because this SDK's Streamable HTTP gives a tool no stable per-connection
    key to scope it by.
    """
    state = library if library is not None else Library()

    server = MCPServer(name="mediakit", version=SUBJECT_VERSION)

    @server.tool(name="media_analyze", description=_ANALYZE)
    def media_analyze(
        path: Annotated[str, Field(description="Path to the media file.")],
    ) -> str:
        asset = LIBRARY.get(path)
        if asset is None:
            return json.dumps({"error": "not_found", "path": path})
        return json.dumps(
            {
                "path": asset.path,
                "duration_seconds": asset.duration_seconds,
                "has_audio": asset.has_audio,
                "width": asset.width,
                "height": asset.height,
                "note": "metadata only; this tool does not return speech or text",
            }
        )

    @server.tool(name="media_register", description=_REGISTER)
    def media_register(
        path: Annotated[str, Field(description="Path to the media file.")],
    ) -> str:
        if path not in LIBRARY:
            return json.dumps({"error": "not_found", "path": path})
        media_id, already = state.register(path)
        return json.dumps({"media_id": media_id, "already_registered": already})

    @server.tool(name="media_transcribe", description=_TRANSCRIBE)
    def media_transcribe(
        media_id: Annotated[str, Field(description="The media to transcribe.")],
    ) -> str:
        path = state.path_for(media_id)
        if path is None:
            # The error names the offending input and the correction, which is
            # what the Recovery dimension grades the model's response to.
            return json.dumps(
                {
                    "error": "unknown_media_id",
                    "received": media_id,
                    "correction": (
                        "media_id must come from media_register. Call "
                        "media_register with the file path first, then pass the "
                        "media_id it returns."
                    ),
                }
            )
        if not LIBRARY[path].has_audio:
            return json.dumps({"error": "no_audio_track", "received": media_id, "path": path})
        return json.dumps({"job_id": state.start_job(media_id), "state": "running"})

    @server.tool(name="media_job_status", description=_JOB_STATUS)
    def media_job_status(
        job_id: Annotated[str, Field(description="The job to check.")],
    ) -> str:
        job = state.poll(job_id)
        if job is None:
            return json.dumps({"error": "unknown_job_id", "received": job_id})
        if job.state != "completed":
            return json.dumps({"job_id": job.job_id, "state": job.state})
        path = state.path_for(job.media_id) or ""
        return json.dumps(
            {
                "job_id": job.job_id,
                "state": "completed",
                "transcript": TRANSCRIPTS.get(path, ""),
            }
        )

    @server.tool(name="media_convert", description=_CONVERT)
    def media_convert(
        path: Annotated[str, Field(description="Path to the media file.")],
        ratio: Annotated[str, Field(description="The ratio to convert to.")],
    ) -> str:
        asset = LIBRARY.get(path)
        if asset is None:
            return json.dumps({"error": "not_found", "path": path})
        if ":" not in str(ratio):
            return json.dumps(
                {
                    "error": "bad_ratio",
                    "received": ratio,
                    "correction": 'ratio is "W:H", for example "16:9" or "9:16".',
                }
            )
        return json.dumps({"path": asset.path, "ratio": ratio, "state": "converted"})

    _ = (media_analyze, media_register, media_transcribe, media_job_status, media_convert)
    return server


def app(library: Library | None = None) -> Any:
    """The ASGI app, so the subject runs as a service the way a customer's does."""
    return build(library).streamable_http_app()
