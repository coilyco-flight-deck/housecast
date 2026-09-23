"""Two runs of one task, matched prompt to prompt. Never two averages.

A mean that rises while three prompts break reads as a win. This reports improved,
regressed and held by name, then an exact sign test as confidence, not a verdict. The
decision rule is net improvement with no regression past a declared threshold. A
difference in anything but the prose refuses the comparison and names the side.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import comb
from typing import Any

from housecast.mcpeval.run import Run

IMPROVED = "improved"
REGRESSED = "regressed"
HELD = "held"
UNCOMPARABLE = "uncomparable"


class ComparisonError(ValueError):
    """Raised when two runs cannot be compared, rather than compared anyway."""


@dataclass(frozen=True)
class DecisionRule:
    """What a team agreed in advance qualifies as an improvement."""

    regression_threshold: float = 0.25
    require_net_improvement: bool = True
    max_regressions: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "regression_threshold": self.regression_threshold,
            "require_net_improvement": self.require_net_improvement,
            "max_regressions": self.max_regressions,
        }


@dataclass(frozen=True)
class PromptDelta:
    """One prompt, both arms, and what moved between them."""

    prompt_id: str
    before: float | None
    after: float | None
    direction: str
    gained: tuple[str, ...] = ()
    lost: tuple[str, ...] = ()

    @property
    def delta(self) -> float | None:
        if self.before is None or self.after is None:
            return None
        return self.after - self.before

    def as_dict(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "before": self.before,
            "after": self.after,
            "delta": self.delta,
            "direction": self.direction,
            "gained": list(self.gained),
            "lost": list(self.lost),
        }


def sign_test(improved: int, regressed: int) -> float:
    """Exact two-tailed binomial p at q=0.5 over the prompts that moved.

    Computed rather than looked up, so the numbers in the brief's power table
    are reproduced instead of restated: 15 of 20 gives 0.041, 9 of 10 gives
    0.021. Held prompts are excluded, which is what makes it a sign test rather
    than a test of whether anything happened at all.
    """
    n = improved + regressed
    if n == 0:
        return 1.0
    k = min(improved, regressed)
    tail = float(sum(comb(n, i) for i in range(k + 1))) / float(2**n)
    return min(1.0, 2.0 * tail)


@dataclass(frozen=True)
class Comparison:
    """The paired report a tester reads to make the promotion decision."""

    task: str
    before_run: str
    after_run: str
    before_label: str
    after_label: str
    deltas: tuple[PromptDelta, ...]
    rule: DecisionRule
    dropped: tuple[str, ...] = ()

    @property
    def improved(self) -> tuple[PromptDelta, ...]:
        return tuple(d for d in self.deltas if d.direction == IMPROVED)

    @property
    def regressed(self) -> tuple[PromptDelta, ...]:
        return tuple(d for d in self.deltas if d.direction == REGRESSED)

    @property
    def held(self) -> tuple[PromptDelta, ...]:
        return tuple(d for d in self.deltas if d.direction == HELD)

    @property
    def p_value(self) -> float:
        return sign_test(len(self.improved), len(self.regressed))

    @property
    def past_threshold(self) -> tuple[PromptDelta, ...]:
        """Prompts that regressed further than the team agreed to tolerate."""
        limit = -abs(self.rule.regression_threshold)
        return tuple(d for d in self.regressed if (d.delta or 0.0) <= limit)

    @property
    def decision(self) -> str:
        """`promote`, `hold` or `reject`, by the declared rule rather than by p."""
        if self.past_threshold:
            return "reject"
        if (
            self.rule.max_regressions is not None
            and len(self.regressed) > self.rule.max_regressions
        ):
            return "reject"
        net = len(self.improved) - len(self.regressed)
        if self.rule.require_net_improvement and net <= 0:
            return "hold"
        return "promote"

    @property
    def underpowered(self) -> bool:
        """Can this many moved prompts support a conclusion at all?"""
        return self.p_value > 0.05

    def headline(self) -> str:
        return (
            f"{len(self.improved)} improved, {len(self.regressed)} regressed, "
            f"{len(self.held)} held, of {len(self.deltas)} paired"
        )

    def render(self) -> str:
        lines = [
            f"{self.task}: {self.before_label or self.before_run} -> "
            f"{self.after_label or self.after_run}",
            f"  {self.headline()}",
        ]
        for name, group in (("improved", self.improved), ("regressed", self.regressed)):
            if group:
                named = ", ".join(f"{d.prompt_id}{d.delta:+.2f}" for d in group)
                lines.append(f"  {name}: {named}")
        reading = "cannot support a conclusion at this n" if self.underpowered else "clears 0.05"
        moved = len(self.improved) + len(self.regressed)
        lines.append(f"  sign test p={self.p_value:.3f} over {moved} moved ({reading})")
        if self.past_threshold:
            named = ", ".join(d.prompt_id for d in self.past_threshold)
            lines.append(
                f"  past the {self.rule.regression_threshold:.2f} regression threshold: {named}"
            )
        if self.dropped:
            lines.append(
                f"  {len(self.dropped)} prompt(s) not paired (transport error in one arm): "
                f"{', '.join(self.dropped)}"
            )
        lines.append(f"  DECISION {self.decision}")
        return "\n".join(lines)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "before_run": self.before_run,
            "after_run": self.after_run,
            "before_label": self.before_label,
            "after_label": self.after_label,
            "deltas": [d.as_dict() for d in self.deltas],
            "rule": self.rule.as_dict(),
            "dropped": list(self.dropped),
            "improved": len(self.improved),
            "regressed": len(self.regressed),
            "held": len(self.held),
            "p_value": self.p_value,
            "underpowered": self.underpowered,
            "decision": self.decision,
            "past_threshold": [d.prompt_id for d in self.past_threshold],
        }


def _moved_checks(before: Any, after: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Which named dimensions turned on and which turned off."""
    was = {c.name: c.passed for c in before.checks}
    now = {c.name: c.passed for c in after.checks}
    gained = tuple(sorted(n for n in now if now[n] and not was.get(n, False)))
    lost = tuple(sorted(n for n in now if not now[n] and was.get(n, False)))
    return gained, lost


def require_comparable(before: Run, after: Run) -> None:
    """Refuse across a difference in anything but the prose, and say which side moved."""
    if before.task != after.task:
        raise ComparisonError(
            f"these runs are of different tasks ({before.task} and {after.task}), "
            "so no pairing exists between their prompts"
        )
    moved = sorted(
        key
        for key in set(before.fingerprint) | set(after.fingerprint)
        if before.fingerprint.get(key) != after.fingerprint.get(key)
    )
    if moved:
        detail = "; ".join(
            f"{key}: {before.fingerprint.get(key)!r} -> {after.fingerprint.get(key)!r}"
            for key in moved
        )
        raise ComparisonError(
            f"cannot compare these runs: {', '.join(moved)} moved as well as the prose. "
            f"Differing prose is the measurement, so every other input must be identical. {detail}"
        )
    if before.definition_digest == after.definition_digest:
        raise ComparisonError(
            "both arms ran the same definition set, so there is nothing to compare. "
            f"Both are {before.definition_digest[:19]}."
        )


def compare(before: Run, after: Run, rule: DecisionRule | None = None) -> Comparison:
    """Pair the two arms prompt by prompt."""
    require_comparable(before, after)
    rule = rule or DecisionRule()
    lhs, rhs = before.by_prompt, after.by_prompt
    deltas: list[PromptDelta] = []
    dropped: list[str] = []
    for prompt_id in [g.prompt_id for g in before.grades]:
        left, right = lhs.get(prompt_id), rhs.get(prompt_id)
        if left is None or right is None:
            dropped.append(prompt_id)
            continue
        if left.score is None or right.score is None:
            # A transport error in either arm breaks the pair. Scoring it zero
            # would enter the network as a prose regression.
            dropped.append(prompt_id)
            continue
        gained, lost = _moved_checks(left, right)
        if right.score > left.score:
            direction = IMPROVED
        elif right.score < left.score:
            direction = REGRESSED
        else:
            direction = HELD
        deltas.append(
            PromptDelta(
                prompt_id=prompt_id,
                before=left.score,
                after=right.score,
                direction=direction,
                gained=gained,
                lost=lost,
            )
        )
    return Comparison(
        task=before.task,
        before_run=before.run_id,
        after_run=after.run_id,
        before_label=before.definition_label,
        after_label=after.definition_label,
        deltas=tuple(deltas),
        rule=rule,
        dropped=tuple(dropped),
    )
