"""Deterministic grading. No LLM judge, and that is not a shortcut.

Deterministic checks run first in the real design too, because the failures this
loop is built to find are structural - a tool selected that should not have
been, a precondition skipped, a poll that never terminated - and every one of
those is visible in the call sequence without asking a model what it thinks.

Two method constraints from the brief hold here and are easy to violate by
accident:

* the grading material never names the expected calls **to the model**. The
  rules below are the grader's and never travel over the wire. The subject's
  descriptions and the prompt are all the model ever sees.
* an executor or service failure is separated from an interface failure. A
  transport error is recorded as `error` on the trial and the trial is scored
  `None` rather than zero, because scoring a dropped connection as a prose
  defect is how a run measures the network.

Each check answers for one prompt and carries the evidence that decided it, so
a tester reading the triaged queue sees why a row is there rather than a bare
red mark.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from housecast.mcpeval.runner import Trial

# The six dimensions of the brief, and which evidence each reads:
# docs/grading.md has the split.
OUTCOME = "outcome"
SELECTION = "selection"
PRECONDITION = "precondition"
POLLING = "polling"
EFFICIENCY = "efficiency"
RECOVERY = "recovery"

DIMENSIONS = (OUTCOME, SELECTION, PRECONDITION, POLLING, EFFICIENCY, RECOVERY)


@dataclass(frozen=True)
class CheckResult:
    """One dimension's verdict for one prompt."""

    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class Grade:
    """Every check for one prompt, and the scalar a paired comparison reads."""

    prompt_id: str
    checks: tuple[CheckResult, ...]
    score: float | None
    error: str = ""

    @property
    def failed(self) -> tuple[CheckResult, ...]:
        return tuple(check for check in self.checks if not check.passed)

    @property
    def outcome_passed(self) -> bool:
        return all(check.passed for check in self.checks if check.name == OUTCOME)

    def as_dict(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "checks": [check.as_dict() for check in self.checks],
            "score": self.score,
            "error": self.error,
        }


def _payloads(trial: Trial) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for call in trial.calls:
        try:
            parsed = json.loads(call.result)
        except (json.JSONDecodeError, TypeError):
            parsed = {}
        out.append(parsed if isinstance(parsed, dict) else {})
    return out


def _check_outcome(trial: Trial, rule: Mapping[str, Any]) -> CheckResult:
    """Did the result satisfy a correctness rule written before the run?"""
    expect = rule.get("expect", "transcript")
    answer = (trial.answer or "").lower()
    if expect == "transcript":
        needle = str(rule.get("answer_contains", "")).lower()
        if not needle:
            return CheckResult(OUTCOME, False, "no answer_contains rule declared for this prompt")
        if not trial.finished:
            return CheckResult(OUTCOME, False, f"never reached an answer in {trial.turns} turns")
        if needle in answer:
            return CheckResult(OUTCOME, True, f"answer carries the transcript ({needle!r})")
        return CheckResult(
            OUTCOME, False, f"answer does not carry the transcript; {needle!r} absent"
        )
    if expect == "no_audio":
        markers = ("no audio", "no speech", "does not contain audio", "without an audio")
        if any(marker in answer for marker in markers):
            return CheckResult(OUTCOME, True, "correctly reported the file has no audio track")
        return CheckResult(OUTCOME, False, "did not report the missing audio track to the user")
    if expect == "convert":
        needle = str(rule.get("answer_contains", "")).lower()
        if needle and needle in answer:
            return CheckResult(OUTCOME, True, f"answer confirms the conversion ({needle!r})")
        return CheckResult(
            OUTCOME, False, f"answer does not confirm the conversion; {needle!r} absent"
        )
    return CheckResult(OUTCOME, False, f"unknown expect {expect!r}")


def _check_selection(trial: Trial, rule: Mapping[str, Any]) -> CheckResult:
    """Did it choose the tool that can do the job, and not one that only looks like it?"""
    required = set(rule.get("required_tools") or ())
    discouraged = set(rule.get("discouraged_tools") or ())
    called = set(trial.call_names)
    unadvertised = [call.name for call in trial.calls if not call.advertised]
    if unadvertised:
        return CheckResult(
            SELECTION, False, f"called tools that were never advertised: {unadvertised}"
        )
    missing = sorted(required - called)
    if missing:
        return CheckResult(SELECTION, False, f"never called {missing}")
    wrong = sorted(discouraged & called)
    if wrong:
        return CheckResult(
            SELECTION, False, f"called {wrong}, which cannot do this job despite its description"
        )
    return CheckResult(SELECTION, True, f"called {list(trial.call_names)}")


def _check_precondition(trial: Trial, rule: Mapping[str, Any]) -> CheckResult:
    """Was the registration done before the call that needs it?"""
    before = rule.get("before")
    after = rule.get("after")
    if not before or not after:
        return CheckResult(PRECONDITION, True, "no ordering rule declared for this prompt")
    names = list(trial.call_names)
    if after not in names:
        return CheckResult(PRECONDITION, False, f"never called {after}")
    if before not in names:
        return CheckResult(PRECONDITION, False, f"called {after} without ever calling {before}")
    if names.index(before) < names.index(after):
        return CheckResult(PRECONDITION, True, f"{before} preceded {after}")
    return CheckResult(PRECONDITION, False, f"called {after} before {before}")


def _check_polling(trial: Trial, rule: Mapping[str, Any]) -> CheckResult:
    """Did it poll to completion, and stop there?"""
    poll_tool = rule.get("poll_tool")
    if not poll_tool:
        return CheckResult(POLLING, True, "no polling rule declared for this prompt")
    payloads = _payloads(trial)
    indices = [i for i, call in enumerate(trial.calls) if call.name == poll_tool]
    if not indices:
        if rule.get("expect") != "transcript":
            return CheckResult(POLLING, True, "no job was started, so nothing to poll")
        return CheckResult(POLLING, False, f"never called {poll_tool}, so no result was collected")
    completed_at = next(
        (i for i in indices if payloads[i].get("state") == "completed"),
        None,
    )
    if completed_at is None:
        return CheckResult(
            POLLING, False, f"polled {len(indices)} times and stopped before the job completed"
        )
    after = [i for i in indices if i > completed_at]
    if after:
        return CheckResult(POLLING, False, f"kept polling {len(after)} times after completion")
    return CheckResult(POLLING, True, f"polled {len(indices)} times and stopped at completion")


def _check_efficiency(trial: Trial, rule: Mapping[str, Any]) -> CheckResult:
    """A correct answer after avoidable retries is strictly weaker than a first-call one."""
    budget = int(rule.get("max_calls") or 0)
    if budget <= 0:
        return CheckResult(EFFICIENCY, True, "no call budget declared for this prompt")
    count = len(trial.calls)
    if count <= budget:
        return CheckResult(EFFICIENCY, True, f"{count} calls, budget {budget}")
    return CheckResult(EFFICIENCY, False, f"{count} calls against a budget of {budget}")


def _check_recovery(trial: Trial, rule: Mapping[str, Any]) -> CheckResult:
    """When the subject returned a correctable error, did the model act on the correction?"""
    errors = [i for i, call in enumerate(trial.calls) if call.is_error]
    if not errors:
        return CheckResult(RECOVERY, True, "the subject returned no error to recover from")
    last = errors[-1]
    followed = trial.calls[last + 1 :]
    if not followed:
        return CheckResult(
            RECOVERY, False, f"{trial.calls[last].name} errored and nothing was tried after it"
        )
    healthy = [call for call in followed if not call.is_error]
    if healthy:
        return CheckResult(
            RECOVERY,
            True,
            f"recovered after {trial.calls[last].name} errored, via {healthy[0].name}",
        )
    return CheckResult(RECOVERY, False, f"every call after {trial.calls[last].name} also errored")


CHECKS = {
    OUTCOME: _check_outcome,
    SELECTION: _check_selection,
    PRECONDITION: _check_precondition,
    POLLING: _check_polling,
    EFFICIENCY: _check_efficiency,
    RECOVERY: _check_recovery,
}


def grade(trial: Trial, rule: Mapping[str, Any], dimensions: Sequence[str] = DIMENSIONS) -> Grade:
    """Every declared dimension for one prompt.

    A trial carrying a transport error scores `None` rather than zero. Zero
    would enter the paired comparison as a regression caused by the network.
    """
    if trial.error:
        return Grade(prompt_id=trial.prompt_id, checks=(), score=None, error=trial.error)
    results = tuple(CHECKS[name](trial, rule) for name in dimensions if name in CHECKS)
    passed = sum(1 for check in results if check.passed)
    return Grade(
        prompt_id=trial.prompt_id,
        checks=results,
        score=passed / len(results) if results else None,
    )
