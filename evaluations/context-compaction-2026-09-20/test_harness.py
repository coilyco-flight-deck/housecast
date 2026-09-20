"""Offline tests for the compaction harness. Run by path, they are outside testpaths.

just test evaluations/context-compaction-2026-09-20
"""

import random

import build_workload as bw
import harness as h

CALL = {
    "role": "assistant",
    "text": "",
    "toolUses": [{"tool_use_id": "a", "tool": "read_file", "input": {"path": "x.py"}}],
}
RESULT = {
    "role": "user",
    "text": "",
    "toolUses": [],
    "toolResults": [{"tool_use_id": "a", "text": "body"}],
}


def test_render_call_and_result():
    assert h.render_message(CALL) == '[call a] read_file({"path": "x.py"})'
    assert h.render_message(RESULT) == "[result a]\nbody"


def test_to_chat_merges_same_role_and_skips_empty():
    goal = {"role": "user", "text": "goal", "toolUses": []}
    gone = {"role": "assistant", "text": "", "toolUses": []}
    chat = h.to_chat([goal, gone, RESULT], "sys", tail="next")
    assert [m["role"] for m in chat] == ["system", "user"]
    assert chat[1]["content"] == "goal\n\n[result a]\nbody\n\nnext"


def test_to_chat_is_stable_for_identical_history():
    assert h.sha256(h.to_chat([CALL, RESULT], "s")) == h.sha256(h.to_chat([CALL, RESULT], "s"))
    assert h.sha256(h.to_chat([CALL, RESULT], "s")) != h.sha256(h.to_chat([CALL, RESULT], "t"))


def test_grade_pass_unknown_wrong():
    line = "    return sorted(files)  # stable"
    assert h.grade(f"   42\t{line}", line) == "pass"
    assert h.grade("`" + line + "`", line) == "pass"
    assert h.grade("UNKNOWN", line) == "unknown"
    assert h.grade("RE-READ a.py", line) == "unknown"
    assert h.grade("return unsorted(files)", line) == "wrong"


def test_reread_target_needs_whole_reply():
    assert h.reread_target("RE-READ evalkit/coverage.py") == "evalkit/coverage.py"
    assert h.reread_target("`RE-READ evalkit/coverage.py`") == "evalkit/coverage.py"
    assert h.reread_target("I would RE-READ evalkit/coverage.py first") is None
    assert h.reread_target("the answer") is None


def test_billed_derives_misses_from_cached():
    assert h.billed(1000, 400, 100, 1.0, 0.1, 2.0) == (600 * 1.0 + 400 * 0.1 + 100 * 2.0) / 1e6


def test_cached_tokens_reads_both_shapes():
    assert h.cached_tokens({"prompt_tokens_details": {"cached_tokens": 7}}) == 7
    assert h.cached_tokens({"prompt_cache_hit_tokens": 9}) == 9
    assert h.cached_tokens({}) == 0


def test_drop_counts():
    decisions = [{"action": a} for a in ("keep", "drop_result", "drop_call", "drop_call")]
    assert h.drop_counts(decisions) == {"resultsDropped": 1, "callsDropped": 2}


def test_pick_needle_is_unique_late_and_deterministic():
    lines = [
        f"line number {i} with enough words to be a real needle candidate here" for i in range(80)
    ]
    lines[10] = lines[11]
    text = "\n".join(lines)
    first = bw.pick_needle(text, random.Random(3))
    assert first == bw.pick_needle(text, random.Random(3))
    assert first is not None
    _, needle = first
    assert lines.count(needle) == 1
    rendered = bw.number(text)
    assert rendered.index(needle) > 600


def test_grep_and_ls_results():
    files = {"a.py": "x\nfoo_bar\nfoo_bar\nfoo_bar\n", "b.md": "nothing"}
    assert bw.grep_result(files, "foo_bar") == "a.py:2: foo_bar\na.py:3: foo_bar\na.py:4: foo_bar"
    assert bw.grep_result(files, "absent") is None
    assert bw.ls_result(["a/x.py", "a/b/y.py", "c.md"], "a") == "b/\nx.py"
