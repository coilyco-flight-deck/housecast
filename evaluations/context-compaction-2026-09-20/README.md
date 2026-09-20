# Does Jev compaction cut deepseek's per-turn cost

2026-09-20. Every number here comes from the files beside this one, and none
is rewritten to match a later source. The question, arms, claims and thresholds
were written in `PREREGISTER.md` before the runs. Where the design changed after
a tally, the addendum there says so and dates it.

## Held constant
* Model `evaluation/deepseek-v4-flash` through Agent Proxy, temperature 0.0, seed 7.
* Jev `jev-latest` through Agent Proxy's `/v1/systemone` shim, keepThreshold 0.5,
  6 pinned messages, fast-jev-compaction at e3f262a.
* 10 transcripts of 26 tool calls from this repository at 7a990d4d, mean result
  4048 characters, final question asks for one exact line read earlier.
* Prices are the deepseek-flash off-peak row of the provider's pricing page read
  on 2026-09-20 (a Sunday, off-peak all day): $0.003 per 1M cached input, $0.15
  per 1M uncached input, $0.6 per 1M output. Jev is estimated at $0.042 per 1M.

## Runs
* `runs/20260920b` - 517 requests, 70 cells (A1 to A3, B, C, D, F over 10
  transcripts), requests at turns 6, 10, 14, 18, 22, 26 and the final question.
  0 failed cells, 0 retries, every finish reason `stop`. `tally.txt` is the
  verbatim `analyze.py` output.
* `runs/20260920c` - 165 requests, 6 cells (A1 and D over t00 to t02), a request
  at every one of the 26 turns and the final question. 0 errors, 0 retries.
* `runs/20260920b/jev_scores.txt` - exploratory, Jev's scores at the final
  compaction for all 10 transcripts.

## Measured, sampled ladder (`runs/20260920b/tally.txt`)
* A, mean per transcript: 149394 prompt tokens, 79.0% cached, cost $0.00574,
  pass 100%. The three A repeats differ by 2.2% of mean cost and all pass 100%.
* B (rule, no model): 42861 prompt, 41.0% cached, cost $0.00456, pass 90%.
  The single miss is t03, where the model wrote
  `[call toolu_03_26] read_file(...)` instead of `RE-READ AGENTS.md`. It asked
  for a re-read in the wrong syntax, which reads as a format miss and not as a
  retrieval failure. That is my reading of one answer.
* C (Jev once): 125795 prompt, 71.5% cached, cost $0.00631 plus $0.00011 Jev,
  pass 100%, 0.70 re-reads per transcript.
* D (Jev every turn): 28293 prompt, 19.3% cached, cost $0.00405 plus $0.00056 Jev,
  pass 100%, 0.70 re-reads per transcript.
* F (random, same count as C): 125795 prompt and 71.5% cached, the same as C,
  cost $0.00628 against C's $0.00631. C dropped every unpinned call in 10 of 10
  transcripts, so F is not informative, as the addendum said it would be.
* C4: completion is 12.0% of A's cost. Reasoning is 76.2% of A's output
  characters (EST, no reasoning token count is reported).

## Measured, dense ladder (`runs/20260920c/tally.txt`)
* A: 510599 prompt tokens per transcript, 93.2% cached, 34695 uncached, cost
  $0.00915, pass 100%.
* D: 104129 prompt tokens, 10.9% cached, 92737 uncached, cost $0.01618 plus $0.00056
  Jev, pass 100%, 1.00 re-reads per transcript, the needle's result gone in 3 of 3.
* D uses 79.6% fewer prompt tokens than A and 2.67 times as many uncached ones.
  D's cost including Jev is 82.9% above A's.

## Measured, exploratory (`runs/20260920b/jev_scores.txt`)
* In 7 of 7 early transcripts Jev ranks the needle's result first of 23 by
  keepResult, at 0.27 to 0.36. No other call scores above 0.08. Every score is
  under the 0.5 threshold, which is why C dropped everything.
* This picked out the one needed result. A threshold chosen from these same 7
  transcripts would be tuning on the test set, so it is a lead and not a result.

## Claims against the thresholds in `PREREGISTER.md`
* C1 held. D's cache-hit share is 19.3% against A's 79.0% (sampled) and 10.9%
  against 93.2% (dense), so 59.7 and 82.3 points lost against a threshold of 10.
* C2 held in the sampled run and failed in the dense run. Sampled, D cuts cost
  19.7%. Dense, D raises it 82.9%. B cut 20.5% in the sampled run, so Jev was
  within 0.8 points of a rule with no model, and B's dense cost was not run.
* C3 held for C, D and F. B lost 10 points, which is one format miss in 10.
* C4 did not hold. Completion is 12.0% of A's cost sampled and 27.5% dense,
  against a threshold of 30%.
* C5 held. D costs more than A when every turn is sent, as predicted before the run.
* The E gate is met (76.2% of output characters are reasoning, threshold 20%).
  E was not run, because a teacher-forced replay never carries reasoning into
  the next turn, so it needs a live harness.
* Decision rule: C1 holds, so per-turn compaction is not promoted.

## Reading, separate from the numbers
* Tokens are not cost here. DeepSeek charges 50 times less for a cached token
  than an uncached one, so any edit that changes the prefix converts cheap reads
  into full-price ones. D reads 80% fewer tokens and still pays more.
* The sampled ladder flattered D, and the dense ladder showed it. A tally that
  counts 6 of 26 requests counts 6 full misses where a live loop pays 26.
* EXPECTED, arithmetic on the token sizes above and the prices, not a run:
  compacting a 30606-token history to 3418 tokens costs $0.000513 to read once
  uncached and saves $0.000082 per later turn, so it repays after 6.3 turns, and
  only if no re-read is needed. Compact rarely and late, never every turn.

## Not run, and what limits this
* No live agent loop, and no harness. 3 transcripts in the dense run, all early
  and all easy questions, with A run once when dense. Its noise floor is unmeasured.
* B was not run dense, and by the same mechanism it is expected to pay more per
  turn than A too. That is EXPECTED and unmeasured.
* Thinking cost is measured only as completion tokens on a workload with short
  thinking. A harder task has more, so C4 could move.
* Follow-ups are filed under `teable:coilyco-flight-deck/housecast#8007`.

## Reproducing
```sh
cd evaluations/context-compaction-2026-09-20
python build_workload.py ../.. 7a990d4d3d0f4d5dd6a0e56e6a45aa19e069fce3 workload
python analyze.py runs/20260920b/cells.jsonl
python analyze.py runs/20260920c/cells.jsonl
python jev_scores.py workload PATH_TO_FAST_JEV_COMPACTION_CHECKOUT
```
`workload/t*.json` is gitignored and regenerates byte for byte, checked against
`workload/manifest.json`. The `lib` path in each `meta.json` is redacted, since it
named a local scratch directory. Offline tests: `just test evaluations/context-compaction-2026-09-20`.
