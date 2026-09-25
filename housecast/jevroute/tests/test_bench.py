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


def _gated(probs: dict[str, float], conf: float, gate: float) -> dict[str, object]:
    return {
        "answers": {"tool": {"probabilities": probs, "confidence": conf}, "gate": {"noul": gate}}
    }


def test_gate_no_routes_to_no_tool_at_gate_confidence() -> None:
    row = score({"q": "x", "ok": ["no_tool"]}, _gated({"get_market": 0.9}, 0.9, 0.04), 0.9)
    assert row["win"] == "no_tool" and row["conf"] == 0.96 and row["pass"]


def test_gate_yes_takes_the_less_sure_of_gate_and_choice() -> None:
    row = score({"q": "x", "ok": ["get_market"]}, _gated({"get_market": 0.97}, 0.96, 0.85), 0.9)
    assert row["win"] == "get_market" and row["conf"] == 0.85 and not row["pass"]


def test_pass_any_counts_a_split_between_two_acceptable_tools() -> None:
    row = score({"q": "x", "ok": ["a", "b"]}, _answer({"a": 0.62, "b": 0.30, "c": 0.08}, 0.6), 0.9)
    assert not row["pass"] and row["pass_any"] and row["ok_mass"] == 0.92


def test_fallback_turns_a_low_confidence_pick_into_no_tool() -> None:
    low = _answer({"get_recipes": 0.5, "get_skills": 0.5}, 0.4)
    assert score({"q": "x", "ok": ["no_tool"]}, low, 0.9, fallback=True)["pass"]
    assert not score({"q": "x", "ok": ["get_recipes"]}, low, 0.9, fallback=True)["pass"]


def test_fallback_still_counts_a_confident_tool_on_a_no_tool_question_as_wrong() -> None:
    row = score(
        {"q": "x", "ok": ["no_tool"]}, _answer({"get_server_status": 0.98}, 0.97), 0.9, True
    )
    assert row["confident_wrong"] and not row["pass"]
