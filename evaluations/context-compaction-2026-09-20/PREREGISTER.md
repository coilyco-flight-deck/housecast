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
  Not yet authored, so no arm runs until it exists.
* Jev egress: those public-safe transcripts only, no secrets, no private
  overlays. The key reaches the probe through the parameter store, never chat.
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
* Jev's data-handling terms are an outside question Kai holds.

## Blocked on a human
* Kai stashes the TypeSafe key as a FILL_ME_IN value file through `just ssm-stash`.
* The workload needs authoring before arm A runs.
