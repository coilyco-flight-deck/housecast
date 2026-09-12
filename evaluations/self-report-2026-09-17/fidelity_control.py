"""Controls for `fidelity.py`, because a comparison never shown to fail is unvalidated.

The board's own spec makes this the acceptance condition rather than a nicety:
a query that has never returned a true positive says nothing when it returns
nothing. So each case below hands the comparison a difference it should catch,
or an identity it should not flag, and names which.

Runs on synthetic records. It needs no corpus and no network, so it is the one
piece of this evaluation that stays reproducible after the corpus is gone.
"""

from __future__ import annotations

from fidelity import footer_runs, match, split_tool, trace_calls

CASES: list[tuple[str, list[dict], dict[str, int], str]] = [
    (
        "exact match, one class",
        [{"tool": "gbif.search_species", "runs": 2}],
        {"gbif/search_species": 2},
        "pass",
    ),
    (
        "a class in the trace that the footer never names",
        [{"tool": "tvmaze.search_tv_show", "runs": 2}],
        {"tvmaze/search_tv_show": 2, "skills/read_skill": 2},
        "fail, class dropped",
    ),
    (
        "the footer understates a count",
        [{"tool": "exa.create_web_search", "runs": 3}],
        {"exa/create_web_search": 6},
        "fail, count only",
    ),
    (
        "the footer overstates a count",
        [{"tool": "gbif.search_species", "runs": 2}, {"tool": "gbif.search_species", "runs": 2}],
        {"gbif/search_species": 2},
        "fail, count only",
    ),
    (
        "two lines of one class sum to the trace, which is the runs-against-calls trap",
        [{"tool": "exa__create_web_search", "runs": 5}, {"tool": "exa__create_web_search", "runs": 4}],
        {"exa/create_web_search": 9},
        "pass",
    ),
    (
        "the renderer's old and new separators name the same class",
        [{"tool": "exa__create_web_search", "runs": 1}, {"tool": "exa.create_web_search", "runs": 1}],
        {"exa/create_web_search": 2},
        "pass",
    ),
    (
        "a footer name carrying no server prefix still matches its tool",
        [{"tool": "scratch_read", "runs": 2}],
        {"scratchpad/scratch_read": 2},
        "pass",
    ),
    (
        "the footer claims a class the trace has no record of",
        [{"tool": "exa.create_web_search", "runs": 1}, {"tool": "ghost.invent", "runs": 1}],
        {"exa/create_web_search": 1},
        "fail, class claimed",
    ),
]


def verdict(disclosed: list[dict], calls: dict[str, int]) -> str:
    """The same decision order `fidelity.py` applies, over the same helpers."""
    claimed = footer_runs(disclosed)
    recorded = trace_calls(calls)
    aligned, unmatched = match(claimed, recorded)
    if sorted(key for key in recorded if key not in aligned):
        return "fail, class dropped"
    if unmatched:
        return "fail, class claimed"
    if any(aligned.get(key, 0) != recorded[key] for key in recorded):
        return "fail, count only"
    return "pass"


def main() -> int:
    print("splitting a footer tool name")
    for name in ("exa__create_web_search", "exa.create_web_search", "scratch_read"):
        print(f"  {name:<24} -> {split_tool(name)}")
    print()

    failures = 0
    for label, disclosed, calls, expected in CASES:
        got = verdict(disclosed, calls)
        ok = got == expected
        failures += not ok
        print(f"  [{'ok' if ok else 'WRONG'}] {expected:<20} {label}")
        if not ok:
            print(f"          got {got!r}")
    print()
    positives = sum(1 for case in CASES if case[3] != "pass")
    print(f"{len(CASES)} controls, {positives} of them differences the pass must catch")
    print("PASS: every control landed" if not failures else f"FAIL: {failures} control(s) wrong")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
