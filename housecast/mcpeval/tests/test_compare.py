"""The paired comparison, the sign test, and the refusals that keep it honest."""

from __future__ import annotations

import pytest

from housecast.mcpeval.checks import CheckResult, Grade
from housecast.mcpeval.compare import ComparisonError, DecisionRule, compare, sign_test
from housecast.mcpeval.run import Run

# The brief's own power table, §04. Computed here rather than restated, so a
# change to `sign_test` fails against the customer's numbers instead of ours.
POWER_TABLE = [
    (10, 9, 0.021),
    (12, 10, 0.039),
    (15, 12, 0.035),
    (20, 15, 0.041),
    (25, 18, 0.043),
    (10, 8, 0.109),
    (12, 9, 0.146),
    (15, 11, 0.118),
    (20, 14, 0.115),
    (25, 17, 0.108),
]


@pytest.mark.parametrize(("n", "moved", "expected"), POWER_TABLE)
def test_sign_test_reproduces_the_briefs_power_table(n: int, moved: int, expected: float) -> None:
    assert sign_test(moved, n - moved) == pytest.approx(expected, abs=0.0006)


def test_no_moved_prompts_is_p_one_rather_than_a_verdict() -> None:
    assert sign_test(0, 0) == 1.0


def _grade(prompt_id: str, score: float | None, error: str = "") -> Grade:
    checks = (CheckResult("outcome", bool(score and score > 0.5), ""),) if score is not None else ()
    return Grade(prompt_id=prompt_id, checks=checks, score=score, error=error)


def _run(run_id: str, digest: str, grades: list[Grade], **fingerprint: object) -> Run:
    return Run(
        run_id=run_id,
        task="t",
        definition_digest=digest,
        definition_label=run_id,
        definition_authored_by="human:test",
        roster_digest=f"roster-of-{digest}",
        started_at="2026-09-16T00:00:00+00:00",
        finished_at="2026-09-16T00:01:00+00:00",
        fingerprint={"task": "t", "model": "m", "temperature": 0.0, **fingerprint},
        trials=(),
        grades=tuple(grades),
    )


def test_pairs_prompt_to_prompt_and_never_averages() -> None:
    before = _run("a", "d1", [_grade("p1", 0.0), _grade("p2", 1.0), _grade("p3", 0.5)])
    after = _run("b", "d2", [_grade("p1", 1.0), _grade("p2", 0.0), _grade("p3", 0.5)])
    report = compare(before, after)
    assert (len(report.improved), len(report.regressed), len(report.held)) == (1, 1, 1)
    assert [d.prompt_id for d in report.improved] == ["p1"]
    assert [d.prompt_id for d in report.regressed] == ["p2"]


def test_a_differing_roster_digest_alone_does_not_refuse_the_comparison() -> None:
    """The roster is derived from the prose, which is the measurement."""
    before = _run("a", "d1", [_grade("p1", 0.0)])
    after = _run("b", "d2", [_grade("p1", 1.0)])
    assert before.roster_digest != after.roster_digest
    compare(before, after)


def test_refuses_when_anything_but_the_prose_moved_and_names_which_side() -> None:
    before = _run("a", "d1", [_grade("p1", 0.0)], model="m")
    after = _run("b", "d2", [_grade("p1", 1.0)], model="other")
    with pytest.raises(ComparisonError, match="model"):
        compare(before, after)


def test_refuses_two_arms_of_the_same_definition_set() -> None:
    before = _run("a", "d1", [_grade("p1", 0.0)])
    after = _run("b", "d1", [_grade("p1", 1.0)])
    with pytest.raises(ComparisonError, match="nothing to compare"):
        compare(before, after)


def test_a_transport_error_breaks_the_pair_rather_than_scoring_zero() -> None:
    """Scoring a dropped connection as a regression measures the network."""
    before = _run("a", "d1", [_grade("p1", 1.0), _grade("p2", 1.0)])
    after = _run("b", "d2", [_grade("p1", 1.0), _grade("p2", None, "boom")])
    report = compare(before, after)
    assert report.dropped == ("p2",)
    assert len(report.deltas) == 1


def test_a_single_bad_regression_rejects_even_with_a_net_gain() -> None:
    grades_before = [_grade(f"p{i}", 0.5) for i in range(6)]
    grades_after = [_grade(f"p{i}", 1.0) for i in range(5)] + [_grade("p5", 0.0)]
    report = compare(
        _run("a", "d1", grades_before),
        _run("b", "d2", grades_after),
        DecisionRule(regression_threshold=0.25),
    )
    assert len(report.improved) == 5
    assert report.past_threshold and report.decision == "reject"


def test_no_net_improvement_holds_rather_than_promotes() -> None:
    """One up, one down, neither past the threshold: a trade, not an improvement."""
    before = _run("a", "d1", [_grade("p1", 0.5), _grade("p2", 0.6)])
    after = _run("b", "d2", [_grade("p1", 0.6), _grade("p2", 0.5)])
    report = compare(before, after)
    assert not report.past_threshold
    assert report.decision == "hold"


def test_a_small_move_is_reported_as_unable_to_support_a_conclusion() -> None:
    grades_before = [_grade(f"p{i}", 0.5) for i in range(20)]
    grades_after = [_grade(f"p{i}", 0.6) for i in range(2)] + [
        _grade(f"p{i}", 0.5) for i in range(2, 20)
    ]
    report = compare(_run("a", "d1", grades_before), _run("b", "d2", grades_after))
    assert report.underpowered, "two prompts moving must not read as a result"
