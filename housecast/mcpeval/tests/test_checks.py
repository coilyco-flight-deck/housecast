"""Deterministic grading, including the separations that keep it a measurement."""

from __future__ import annotations

import json

from housecast.mcpeval.checks import DIMENSIONS, grade
from housecast.mcpeval.runner import CallRecord, Trial

RULE = {
    "expect": "transcript",
    "answer_contains": "cache coherence",
    "required_tools": ["media_transcribe"],
    "discouraged_tools": ["media_analyze"],
    "before": "media_register",
    "after": "media_transcribe",
    "poll_tool": "media_job_status",
    "max_calls": 5,
}


def call(name: str, result: object, is_error: bool = False, advertised: bool = True) -> CallRecord:
    return CallRecord(
        name=name,
        arguments={},
        result=json.dumps(result) if not isinstance(result, str) else result,
        is_error=is_error,
        advertised=advertised,
        duration_ms=1,
    )


def trial(calls: list[CallRecord], answer: str, finished: bool = True, error: str = "") -> Trial:
    return Trial(
        prompt_id="p1",
        prompt="x",
        definition_digest="d",
        roster_digest="r",
        roster_names=("media_register", "media_transcribe", "media_job_status", "media_analyze"),
        subject_version="v",
        model={},
        calls=tuple(calls),
        answer=answer,
        turns=1,
        finished=finished,
        duration_ms=1,
        prompt_tokens=0,
        completion_tokens=0,
        error=error,
    )


GOOD = [
    call("media_register", {"media_id": "m"}),
    call("media_transcribe", {"job_id": "j"}),
    call("media_job_status", {"state": "running"}),
    call("media_job_status", {"state": "completed", "transcript": "..."}),
]


def test_a_clean_path_passes_every_dimension() -> None:
    result = grade(trial(GOOD, "Here it is: cache coherence and the invalidation protocol."), RULE)
    assert result.score == 1.0
    assert not result.failed


def test_a_transport_error_scores_none_rather_than_zero() -> None:
    """Zero would enter a paired comparison as a regression caused by the network."""
    result = grade(trial([], "", finished=False, error="TransportError: shed"), RULE)
    assert result.score is None
    assert result.error


def test_calling_the_over_broad_tool_fails_selection() -> None:
    calls = [*GOOD, call("media_analyze", {"duration_seconds": 1})]
    result = grade(trial(calls, "cache coherence"), RULE)
    failed = {c.name for c in result.failed}
    assert "selection" in failed


def test_a_tool_that_was_never_advertised_fails_selection_before_anything_else() -> None:
    calls = [call("invented_tool", {"error": "no_such_tool"}, is_error=True, advertised=False)]
    result = grade(trial(calls, ""), RULE)
    detail = next(c.detail for c in result.failed if c.name == "selection")
    assert "never advertised" in detail


def test_polling_past_completion_fails() -> None:
    calls = [*GOOD, call("media_job_status", {"state": "completed", "transcript": "..."})]
    result = grade(trial(calls, "cache coherence"), RULE)
    assert any(c.name == "polling" and "after completion" in c.detail for c in result.failed)


def test_stopping_before_completion_fails() -> None:
    calls = GOOD[:3]
    result = grade(trial(calls, "cache coherence"), RULE)
    assert any(c.name == "polling" and "stopped before" in c.detail for c in result.failed)


def test_calling_the_dependent_tool_first_fails_the_precondition() -> None:
    calls = [GOOD[1], GOOD[0], *GOOD[2:]]
    result = grade(trial(calls, "cache coherence"), RULE)
    assert any(c.name == "precondition" for c in result.failed)


def test_recovery_asks_whether_the_correction_was_acted_on() -> None:
    calls = [
        call("media_transcribe", {"error": "unknown_media_id"}, is_error=True),
        call("media_register", {"media_id": "m"}),
    ]
    result = grade(trial(calls, ""), RULE)
    recovery = next(c for c in result.checks if c.name == "recovery")
    assert recovery.passed


def test_an_error_with_nothing_after_it_fails_recovery() -> None:
    calls = [call("media_transcribe", {"error": "unknown_media_id"}, is_error=True)]
    result = grade(trial(calls, ""), RULE)
    recovery = next(c for c in result.checks if c.name == "recovery")
    assert not recovery.passed


def test_the_no_audio_edge_case_wants_a_report_rather_than_a_transcript() -> None:
    rule = dict(RULE, expect="no_audio", required_tools=[], poll_tool="", max_calls=4)
    good = grade(
        trial([GOOD[0]], "That file has no audio track, so there is nothing to transcribe."), rule
    )
    assert good.outcome_passed
    bad = grade(trial([GOOD[0]], "Here is the transcript."), rule)
    assert not bad.outcome_passed


def test_every_declared_dimension_is_graded() -> None:
    result = grade(trial(GOOD, "cache coherence"), RULE)
    assert {c.name for c in result.checks} == set(DIMENSIONS)
