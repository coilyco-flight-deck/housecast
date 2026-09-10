"""Known-answer checks on `validity.py`, run before it saw any real score.

The instrument this directory is built around decides whether a criterion
survives. An arithmetic slip in it produces a verdict rather than an error, so
every statistic here is asserted against a value computed off the machine.
"""

from __future__ import annotations

import json
import math
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import validity


def test_fisher_matches_the_tea_tasting_table() -> None:
    # Fisher's own 2x2. The hypergeometric upper tail at a=3 is 17/70.
    assert validity.fisher_one_sided(3, 1, 1, 3) == pytest.approx(17 / 70)


def test_fisher_is_one_at_the_bottom_of_its_range() -> None:
    assert validity.fisher_one_sided(0, 4, 4, 0) == pytest.approx(1.0)


def test_fisher_returns_one_on_a_degenerate_margin() -> None:
    assert validity.fisher_one_sided(0, 0, 3, 3) == pytest.approx(1.0)


def test_trend_is_zero_when_every_level_disagrees_alike() -> None:
    assert validity.cochran_armitage([(2, 10), (2, 10), (2, 10)]) == pytest.approx(0.0)


def test_trend_matches_a_hand_computed_z() -> None:
    # p = 1/3, mean score 1, numerator 10, variance 40/9.
    assert validity.cochran_armitage([(0, 10), (0, 10), (10, 10)]) == pytest.approx(
        10 / math.sqrt(40 / 9)
    )


def test_trend_goes_negative_when_the_zeroes_disagree_more() -> None:
    assert validity.cochran_armitage([(10, 10), (0, 10), (0, 10)]) < 0


def test_trend_is_zero_when_nothing_disagreed() -> None:
    assert validity.cochran_armitage([(0, 10), (0, 10), (0, 10)]) == pytest.approx(0.0)


def test_normal_sf_at_the_critical_value() -> None:
    assert validity.normal_sf(validity.Z_ONE_SIDED) == pytest.approx(0.05, abs=0.0005)


def write_sheet(tmp_path: pathlib.Path, rows: list[tuple[str, str]]) -> pathlib.Path:
    path = tmp_path / "sheet.csv"
    lines = ["case,score"] + [f"{case},{score}" for case, score in rows]
    path.write_text("\n".join(lines) + "\n")
    return path


def write_report(tmp_path: pathlib.Path, cases: list[dict]) -> pathlib.Path:
    path = tmp_path / "disagreement.json"
    path.write_text(json.dumps({"per_case": cases}))
    return path


def test_unscored_rows_are_dropped_rather_than_read_as_zero(tmp_path: pathlib.Path) -> None:
    path = write_sheet(tmp_path, [("a", "2"), ("b", ""), ("c", "0")])
    assert validity.read_scores(path) == {"a": 2, "c": 0}


def test_a_score_outside_the_rubric_refuses(tmp_path: pathlib.Path) -> None:
    path = write_sheet(tmp_path, [("a", "3")])
    with pytest.raises(ValueError, match="not 0, 1 or 2"):
        validity.read_scores(path)


def test_an_incomplete_case_never_reaches_the_table(tmp_path: pathlib.Path) -> None:
    # `agreement.CaseAgreement.to_dict` omits `agreed` and carries `missing`
    # instead when some grader never reached the case.
    path = write_report(
        tmp_path,
        [
            {"id": "a", "labels": {"x": "pass", "y": "fail"}, "agreed": False},
            {"id": "b", "labels": {"x": "pass"}, "missing": ["y"]},
        ],
    )
    assert validity.read_disagreement(path) == {"a": True}


def test_tabulate_counts_only_the_join() -> None:
    scores = {"a": 2, "b": 0, "c": 1, "d": 2}
    disagreed = {"a": True, "b": False, "c": True}
    assert validity.tabulate(scores, disagreed) == [(0, 1), (1, 1), (1, 1)]


def test_the_rule_retires_a_criterion_pointing_the_wrong_way() -> None:
    result = validity.verdict([(10, 10), (0, 10), (0, 10)])
    assert result["direction"] is False
    assert result["retained"] is False


def test_the_rule_retires_a_direction_that_misses_alpha() -> None:
    # 2s disagree more, and on these counts the trend does not clear 1.645.
    result = validity.verdict([(2, 20), (2, 20), (3, 20)])
    assert result["direction"] is True
    assert result["trend_fires"] is False
    assert result["retained"] is False


def test_the_rule_retains_only_on_a_significant_upward_trend() -> None:
    result = validity.verdict([(1, 20), (5, 20), (12, 20)])
    assert result["direction"] is True
    assert result["trend_fires"] is True
    assert result["retained"] is True


def test_an_empty_stratum_cannot_retain() -> None:
    # Nobody scored a 2, so there is no contrast to read and no verdict to give.
    result = validity.verdict([(4, 20), (4, 20), (0, 0)])
    assert result["retained"] is False
