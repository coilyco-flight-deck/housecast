"""Frozen tool-loop transcripts with large tool results, built from one pinned git ref.

Usage: python build_workload.py REPO_DIR REF OUT_DIR

The source is this public repository at REF, so every result is public-safe.
Each transcript ends with a question whose answer is one exact line of one file
read earlier, so a dropped result is detectable. Early transcripts ask about a
call that compaction may drop, recent ones about a call it must keep.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from harness import QUESTION

N_TRANSCRIPTS = 10
N_EARLY = 7
N_CALLS = 26
SEED = 7
GOAL = (
    "You are exploring a code repository to prepare for one question that I will ask at the "
    "end. Use read_file, grep and list_dir as needed."
)
MIN_MEAN_RESULT_CHARS = 2000
MIN_UNPINNED_CALLS = 20


def git(repo: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, check=True
    ).stdout


def load_files(repo: str, ref: str) -> tuple[dict[str, str], list[str]]:
    paths = git(repo, "ls-tree", "-r", "--name-only", ref).splitlines()
    files: dict[str, str] = {}
    for path in paths:
        if not path.endswith((".py", ".md")) or path.startswith("evaluations/"):
            continue
        text = git(repo, "show", f"{ref}:{path}")
        if 2500 <= len(text) <= 12000 and text.count("\n") >= 60:
            files[path] = text
    return files, paths


def number(text: str) -> str:
    return "\n".join(f"{i:>4}\t{line}" for i, line in enumerate(text.split("\n"), 1))


def pick_needle(text: str, rng: random.Random) -> tuple[int, str] | None:
    """A unique 50 to 110 character line past the first 600 characters of the rendering."""
    lines = text.split("\n")
    counts: dict[str, int] = {}
    for line in lines:
        counts[line.strip()] = counts.get(line.strip(), 0) + 1
    offset = 0
    found: list[tuple[int, str]] = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if (
            offset > 600
            and 50 <= len(stripped) <= 110
            and counts[stripped] == 1
            and re.search(r"[A-Za-z]{4}", stripped)
        ):
            found.append((i, stripped))
        offset += len(f"{i:>4}\t{line}") + 1
    return rng.choice(found) if found else None


def grep_result(files: dict[str, str], pattern: str) -> str | None:
    hits = [
        f"{path}:{i}: {line.strip()[:160]}"
        for path, text in sorted(files.items())
        for i, line in enumerate(text.split("\n"), 1)
        if pattern in line
    ]
    if not 3 <= len(hits) <= 400:
        return None
    extra = f"\n... ({len(hits) - 30} more matches)" if len(hits) > 30 else ""
    return "\n".join(hits[:30]) + extra


def ls_result(paths: list[str], directory: str) -> str:
    prefix = "" if directory == "." else directory + "/"
    names = {
        p[len(prefix) :].split("/")[0] + ("/" if "/" in p[len(prefix) :] else "")
        for p in paths
        if p.startswith(prefix)
    }
    return "\n".join(sorted(names))


def build_transcript(
    index: int, files: dict[str, str], paths: list[str], ref: str
) -> dict[str, Any]:
    rng = random.Random(SEED * 1000 + index)
    early = index < N_EARLY
    needle_pos = rng.randint(1, 7) if early else rng.choice([N_CALLS - 3, N_CALLS - 2, N_CALLS - 1])
    kinds = ["read"] * 15 + ["grep"] * 6 + ["ls"] * 4
    rng.shuffle(kinds)
    kinds.insert(needle_pos, "read")
    if kinds[0] != "read":
        swap = next(i for i, k in enumerate(kinds) if k == "read" and i != needle_pos)
        kinds[0], kinds[swap] = kinds[swap], kinds[0]
    read_paths = rng.sample(sorted(files), kinds.count("read"))
    needle_file = needle_line = None
    for candidate in rng.sample(read_paths, len(read_paths)):
        needle = pick_needle(files[candidate], rng)
        if needle:
            needle_file, needle_line = candidate, needle
            break
    assert needle_file and needle_line
    read_paths.remove(needle_file)
    order = iter(read_paths)
    directories = sorted({str(Path(p).parent) for p in paths})

    messages: list[dict[str, Any]] = [{"role": "user", "text": GOAL, "toolUses": []}]
    for pos, kind in enumerate(kinds):
        tool_id = f"toolu_{index:02d}_{pos:02d}"
        if kind == "read":
            path = needle_file if pos == needle_pos else next(order)
            call, result = ("read_file", {"path": path}), number(files[path])
        elif kind == "grep":
            word, result = "", None
            while result is None:
                word = rng.choice(re.findall(r"[A-Za-z_]{7,}", files[rng.choice(sorted(files))]))
                result = grep_result(files, word)
            call = ("grep", {"pattern": word})
        else:
            directory = rng.choice(directories)
            call, result = ("list_dir", {"path": directory}), ls_result(paths, directory)
        messages.append(
            {
                "role": "assistant",
                "text": "",
                "toolUses": [{"tool_use_id": tool_id, "tool": call[0], "input": call[1]}],
            }
        )
        messages.append(
            {
                "role": "user",
                "text": "",
                "toolUses": [],
                "toolResults": [{"tool_use_id": tool_id, "text": result}],
            }
        )
    return {
        "id": f"t{index:02d}",
        "kind": "early" if early else "recent",
        "ref": ref,
        "needle_call": needle_pos + 1,
        "path": needle_file,
        "line": needle_line[0],
        "expected": needle_line[1],
        "question": QUESTION.format(path=needle_file, line=needle_line[0]),
        "messages": messages,
    }


def main(repo: str, ref: str, out: str) -> None:
    files, paths = load_files(repo, ref)
    Path(out).mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"ref": ref, "seed": SEED, "files_available": len(files), "t": []}
    chars: list[int] = []
    for i in range(N_TRANSCRIPTS):
        transcript = build_transcript(i, files, paths, ref)
        body = json.dumps(transcript, indent=1, sort_keys=True)
        (Path(out) / f"{transcript['id']}.json").write_text(body + "\n")
        sizes = [len(r["text"]) for m in transcript["messages"] for r in m.get("toolResults", [])]
        chars += sizes
        manifest["t"].append(
            {
                "id": transcript["id"],
                "kind": transcript["kind"],
                "needle_call": transcript["needle_call"],
                "calls": len(sizes),
                "result_chars": sum(sizes),
                "sha256": hashlib.sha256(body.encode()).hexdigest()[:16],
            }
        )
    manifest["mean_result_chars"] = round(sum(chars) / len(chars))
    assert manifest["mean_result_chars"] >= MIN_MEAN_RESULT_CHARS, manifest["mean_result_chars"]
    assert N_CALLS - 3 >= MIN_UNPINNED_CALLS
    (Path(out) / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "t"}))
    for row in manifest["t"]:
        print(row)


if __name__ == "__main__":
    main(*sys.argv[1:4])
