from housecast.jevroute.servers import judge, server_text, tally


def test_judge_counts_mass_across_acceptable_answers() -> None:
    j = judge({"a": 0.6, "b": 0.35, "c": 0.05}, 0.55, ["a", "b"], 0.9)
    assert j["any"] and not j["strict"] and not j["cw"]


def test_judge_flags_confident_wrong() -> None:
    assert judge({"c": 0.97}, 0.95, ["a"], 0.9)["cw"]


def test_empty_live_description_falls_back_to_skill_text() -> None:
    assert server_text({"description": "", "skill_description": "S"}, "live") == "S"
    assert server_text({"description": "L", "skill_description": "S"}, "live") == "L"
    assert server_text({"description": "L", "skill_description": "S"}, "skill") == "S"


def test_tally_front_only_rows_skip_server_counts() -> None:
    row = {"front": {"any": True, "cw": False}, "sec_server": 0.1, "raw_server": {}}
    s = tally([row])
    assert s["front_any"] == 1 and "server_any" not in s
