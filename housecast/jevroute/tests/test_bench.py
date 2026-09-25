from pathlib import Path

import pytest

from housecast.jevroute.bench import load_cases, parse_mcp_body, score, summarize


def _answer(probs: dict[str, float], conf: float) -> dict[str, object]:
    return {"answers": {"tool": {"probabilities": probs, "confidence": conf}}}


def test_sse_reply_parses_last_data_line() -> None:
    raw = 'event: message\ndata: {"id": 1}\n\nevent: message\ndata: {"id": 2}\n'
    assert parse_mcp_body(raw) == {"id": 2}


def test_plain_json_reply_parses() -> None:
    assert parse_mcp_body('{"result": 1}') == {"result": 1}


def test_pass_needs_right_tool_and_threshold() -> None:
    case = {"q": "x", "ok": ["find_trade"]}
    assert score(case, _answer({"find_trade": 0.95, "get_stores": 0.05}, 0.93), 0.9)["pass"]
    low = score(case, _answer({"find_trade": 0.6, "get_stores": 0.4}, 0.5), 0.9)
    assert low["correct"] and not low["pass"] and not low["confident_wrong"]


def test_confident_wrong_is_counted_apart() -> None:
    row = score({"q": "x", "ok": ["find_trade"]}, _answer({"get_stores": 0.97}, 0.95), 0.9)
    assert row["confident_wrong"] and not row["pass"]
    assert summarize([row])["confident_wrong"] == 1


def test_error_answer_scores_as_a_failure_not_a_crash() -> None:
    row = score({"q": "x", "ok": ["a"]}, {"error": "timeout"}, 0.9)
    assert row["error"] == "timeout" and not row["pass"]


def test_duplicate_question_is_refused(tmp_path: Path) -> None:
    f = tmp_path / "c.yaml"
    f.write_text("cases:\n  - {q: a, ok: [x]}\n  - {q: a, ok: [y]}\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(f)


def test_committed_case_files_load() -> None:
    root = Path(__file__).resolve().parents[3] / "evaluations" / "jevroute-eco"
    for f in sorted(root.glob("cases-*.yaml")):
        assert load_cases(f)
