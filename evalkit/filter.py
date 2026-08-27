"""Read an Inspect eval log and build the dataset a human annotates.

The join and its drop report live in `aos_eval.dataset`, shared with every
other runner. What stays here is the part only Inspect can do: reading its log
format. The annotator sees epoch 1, and the other epochs stay in the log as
evidence a reader can open. See docs/evaluation.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from aos_eval.dataset import DatasetReport, build, validate
from aos_eval.io import save_dataset
from aos_eval.schema import AGENT_COMPOSE, Challenge, Response
from inspect_ai.log import read_eval_log


def load_responses(path: Path) -> list[Response]:
    """Read subject outputs from an Inspect eval log, one Response per epoch."""
    log = read_eval_log(str(path))
    if log.status != "success":
        raise SystemExit(f"eval log status is {log.status}, refusing to read it")
    responses: list[Response] = []
    # Inspect calls its own dataset row a sample, so that noun stays here.
    for sample in log.samples or []:
        message = sample.output.choices[0].message if sample.output.choices else None
        responses.append(
            Response(
                challenge_id=str(sample.id),
                epoch=int(sample.epoch),
                text=(sample.output.completion or "").strip(),
                finish_reason=str(getattr(message, "stop_reason", "") or "stop"),
                reasoning=_reasoning(message),
            )
        )
    return responses


def load_challenges(path: Path) -> list[Challenge]:
    """Authoring is where a malformed case must fail.

    The shared Challenge stays portable across profiles, so it enforces only what
    is true of every deployment. A board case that omits a field this profile
    requires is not a portability question, it is an unauthored case that would
    read as graded coverage.
    """
    raw = yaml.safe_load(path.read_text()) or {}
    written = [Challenge.model_validate(entry) for entry in raw.get("challenges", [])]
    if problems := validate(written, AGENT_COMPOSE):
        raise ValueError("\n".join(problems))
    return written


def run(written: list[Challenge], responses: list[Response]) -> DatasetReport:
    return build(written, responses)


def _reasoning(message: object) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, list):
        parts = [getattr(c, "reasoning", "") for c in content]
        return "\n".join(p for p in parts if p).strip()
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the annotation dataset from a run.")
    parser.add_argument("--challenges", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True, help=".eval log from inspect eval")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    report = build(load_challenges(args.challenges), load_responses(args.log))
    save_dataset(args.out, report.kept)

    print(report.summary)
    for drop in report.dropped:
        print(f"  dropped {drop.challenge_id}: {drop.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
