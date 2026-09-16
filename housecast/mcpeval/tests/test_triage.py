"""The queue, and the arithmetic that says what reading it costs."""

from __future__ import annotations

from housecast.mcpeval.checks import CheckResult, Grade
from housecast.mcpeval.run import Run
from housecast.mcpeval.triage import MINUTES_PER_RESULT, build


def _grade(prompt_id: str, outcome: bool, other: bool = True, score: float = 1.0) -> Grade:
    return Grade(
        prompt_id=prompt_id,
        checks=(
            CheckResult("outcome", outcome, "no answer" if not outcome else "ok"),
            CheckResult(
                "efficiency", other, "7 calls against a budget of 5" if not other else "ok"
            ),
        ),
        score=score,
    )


def _run(grades: list[Grade]) -> Run:
    return Run(
        run_id="r",
        task="t",
        definition_digest="d",
        definition_label="l",
        definition_authored_by="human:t",
        roster_digest="x",
        started_at="2026-09-16T00:00:00+00:00",
        finished_at="2026-09-16T00:01:00+00:00",
        fingerprint={},
        trials=(),
        grades=tuple(grades),
    )


def test_passing_rows_are_not_in_the_queue_at_all() -> None:
    """Scrolling past green rows spends attention the budget cannot refund."""
    queue = build(_run([_grade("p1", True), _grade("p2", True)]))
    assert queue.rows == ()
    assert queue.hidden == 2


def test_failures_come_before_inefficiency() -> None:
    queue = build(
        _run([_grade("p1", True, other=False, score=0.5), _grade("p2", False, score=0.5)])
    )
    assert [r.prompt_id for r in queue.rows] == ["p2", "p1"]
    assert queue.rows[0].reason == "failure"
    assert queue.rows[1].reason == "inefficiency"


def test_a_transport_error_outranks_every_prose_finding() -> None:
    errored = Grade(prompt_id="p0", checks=(), score=None, error="TransportError: shed")
    queue = build(_run([_grade("p1", False, score=0.0), errored]))
    assert queue.rows[0].prompt_id == "p0"
    assert queue.rows[0].reason == "transport"


def test_a_prompt_a_comparison_moved_is_surfaced_even_when_its_outcome_passed() -> None:
    queue = build(_run([_grade("p1", True), _grade("p2", True)]), moved=["p2"])
    assert [r.prompt_id for r in queue.rows] == ["p2"]
    assert queue.rows[0].reason == "moved"


def test_the_budget_is_reported_in_minutes_rather_than_rows() -> None:
    queue = build(_run([_grade(f"p{i}", False, score=0.0) for i in range(9)]))
    assert queue.minutes == 9 * MINUTES_PER_RESULT
