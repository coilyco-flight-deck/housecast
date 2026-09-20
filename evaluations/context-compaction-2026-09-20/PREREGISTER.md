# Pre-registration: does Jev compaction cut deepseek's per-turn cost
Seat: Evie (science). housecast at bf83478. Written 2026-09-20 before any Jev call.

## The ask, and why it is not yet a measurement
Kai's premise: deepseek spends more tokens between turns on thinking and prior
context. Her proposal: run Jev (fast-jev-compaction e3f262a) between every
deepseek turn. The premise has no baseline on disk (the committed runs report no
reasoning split and no cache split), so arm A below is what makes it measurable.

## Already measured, not pre-registered
These were read or computed before this file was written. They bound the design
and are not claims under test.
* Source at e3f262a: zero mentions of thinking or reasoning in `src/`, both
  READMEs and `hooks/fast-jev.ts`. It removes tool call and result pairs only.
* It compacts on `session.compact`. `turn.complete` requests compaction at 60%
  of context, so per-turn use is a hook change and not the shipped behavior.
* Jev is a hosted scorer at a direct third-party endpoint, resending up to a
  25k-token state with every request.
* `mcp-tool-loop-2026-09-16`, 100 trials: prompt tokens are 7.2x completion
  tokens (597220 against 83110). Tool results are about 4.4% of prompt tokens
  and the part Jev could address is about 2.3% (chars/4 estimates, `ceiling.py`,
  output in `ceiling-output.txt`). Mean result is 106 characters, so that
  workload cannot test compaction.
* Agent Proxy documents that DeepSeek caching is automatic and reports
  `prompt_cache_hit_tokens` and `prompt_cache_miss_tokens`
  (`agent-proxy/docs/proxy-prompt-cache.md` at dc2f29f).

## Setup, frozen before the run
* Direct replay through Agent Proxy, no harness. Route
  `evaluation/deepseek-v4-flash`, temperature 0.0, seed 7.
* Workload: frozen, public-safe transcripts with large tool results, at least 20
  unpinned calls per transcript and mean result of at least 2000 characters.
  Built by `build_workload.py`, described in the amendment below.
* Jev egress: those public-safe transcripts only, no secrets, no private
  overlays. Kai said on 2026-09-20 that transcript handling by TypeSafe is not a
  concern. The calls go through Agent Proxy's `/v1/systemone` shim, which holds
  the key, so no key passes through this seat.
* Prices are read from the provider's published sheet on the run date and
  recorded beside the result.

## Arms
* A - control, no compaction. Repeated 3 times for the noise floor.
* B - rule, no model. Truncate results of unpinned calls to 300 characters plus
  a note, same pin window as Jev.
* C - Jev once at the library default, keepThreshold 0.5, 6 pinned messages.
* D - Jev before every turn, decisions sticky so an item dropped once stays dropped.
* F - random, drops the same count as C but chosen at random. Control for
  whether Jev's scores carry information beyond dropping the same amount.
* E - strip prior-turn reasoning. Runs only if A shows reasoning at or above
  20% of completion tokens, otherwise dropped and recorded as dropped.

## Claims, stated before the tally
* C1 - D's cache-hit share is at least 10 points below A's. Basis is inference:
  an edit mid-history invalidates every cached block after it.
* C2 - C or D cuts billed-equivalent cost by at least 15% against A on the
  large-result workload. If B reaches within 10 points of that cut, Jev's extra
  request is not earning its cost.
* C3 - no arm loses more than 5 points of frozen-grader pass rate against A,
  with the 3 repeats of A setting the noise floor.
* C4 - the premise: reasoning plus completion is at least 30% of A's
  billed-equivalent cost. Below 30% the premise fails on this route.

## Negative controls
* F against C. If F matches C, the scores are not informative.
* A repeated. Any delta inside its spread is not a delta.
* If C1 fails and D also loses no cache, the inference about prefix caching was wrong.

## Decision rule
Promote per-turn compaction only if C1 holds at less than 10 points lost, C2 and
C3 pass, and C or D beats both B and F on cost at equal quality. Otherwise record
the result and leave the harness unchanged.

## Not run
* No live agent loop. Direct replay does not test how a harness carries
  compacted history.

## Amendment, 2026-09-20, before the full run
The first design had a confound, found before any tally. Jev's questions assume a
dropped result can be recovered by re-running the tool, and the first final
question forbade tool calls. That would score every drop as a failure and measure
information retention instead of task completion. Changes, all made before the
full run:
* The final question allows `RE-READ <path>` for up to 2 re-reads. Each re-read
  is a counted request, so C2 cost includes the price of recovering a drop. C3
  quality is the pass rate after at most 2 re-reads. Re-read rate is reported.
* Workload: 10 transcripts of 26 tool calls (16 read_file, 6 grep, 4 list_dir)
  from this repository at 7a990d4d, seed 7, mean result 4048 characters. The
  final question asks for one exact line of a file read earlier. 7 transcripts
  ask about call 2 to 8 (droppable) and 3 about a call in the last 3 (pinned).
  `workload/manifest.json` holds hashes and the transcripts regenerate byte for
  byte from the ref.
* Ladder: deepseek requests at turns 6, 10, 14, 18, 22 and 26, then the final
  question, with earlier replies discarded. D compacts before every one of the
  26 turns and the ladder samples those states. C compacts once, at the final
  question. B and F apply at every ladder step and the final question, F only
  at the final question with C's drop counts.
* Each cell has its own salt in the system prompt, so no arm shares a cache
  prefix with another and every ladder starts cold.
* F is uninformative in any transcript where C drops every unpinned call, since
  a random pick of all of them is the same set. If that holds in at least 80% of
  transcripts, F is reported as not informative and C2 drops its F comparison.
* Smoke run on t00 before this amendment: C dropped all 23 unpinned calls
  including the needle (keepResult 0.36 against threshold 0.5), the re-read
  recovered the answer, and C's final prompt was 3704 tokens against A's 35563.
  One transcript, a plumbing check, not evidence for any claim.
* Reasoning share is measured from `reasoning_content` characters against
  content characters, since the proxy reports no reasoning token count. It is an
  estimate and is labelled EST.
