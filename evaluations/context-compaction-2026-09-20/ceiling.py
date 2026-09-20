"""Upper bound on what tool-result compaction can remove from a committed run set.

Usage: python ceiling.py RUNS_DIR [PIN]

Sizes are chars/4 estimates, and the resend model assumes one call per turn,
so both are marked EST in the output. Prompt totals are the reported figures.
"""
import glob
import json
import sys

runs_dir = sys.argv[1]
pin = int(sys.argv[2]) if len(sys.argv) > 2 else 6  # fast-jev-compaction preserveRecentMessages default

trials = calls = cand = 0
prompt = completion = 0
resent = cand_resent = 0.0
result_chars = 0
for path in sorted(glob.glob(f"{runs_dir}/*.json")):
    for t in json.load(open(path))["trials"]:
        trials += 1
        prompt += t["prompt_tokens"]
        completion += t["completion_tokens"]
        n = len(t["calls"])
        messages = 1 + 2 * n  # first user message, then assistant and result per call
        for j, c in enumerate(t["calls"]):
            chars = len(str(c["result"]))
            result_chars += chars
            calls += 1
            later = max(t["turns"] - 1 - j, 0) * chars / 4
            resent += later
            index = 2 + 2 * j
            if index < messages - pin:  # unpinned, so a candidate for removal
                cand += 1
                cand_resent += later

print(f"trials={trials} calls={calls} candidate_calls={cand} pin={pin}")
print(f"prompt_tokens={prompt} completion_tokens={completion} ratio={prompt / completion:.1f}")
print(f"result_chars={result_chars} mean_per_call={result_chars / calls:.0f}")
print(f"EST result share of prompt={resent / prompt:.1%}")
print(f"EST candidate-only share (ceiling)={cand_resent / prompt:.1%}")
