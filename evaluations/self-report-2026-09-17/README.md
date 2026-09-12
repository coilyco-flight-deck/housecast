# The Self-Report Test

Grade Sirens Deep on its own account of itself, over 47 live replies from
2026-08-15 to 2026-08-19. The board this derives is what the PyLadies San
Francisco / Datadog 25 minutes on 2026-09-17 runs against.

Design spec, Portfolio Director, reviewed by the AI Risk Analyst 2026-09-10:
[The Self-Report Test](https://claude.ai/code/artifact/136030a0-86b4-4fc9-b9f9-04b722759216).
Record: `teable:coilyco-flight-deck/housecast#7430`. This directory is the
build of that spec, and where it departs from it, the departures are below.

## The corpus is not here

`s3://coilysiren-assets/housecast-corpora/sirens-deep-2026-08-15-to-2026-08-19/`,
with a MANIFEST. It carries a community member's Discord messages, and whether
it lands in git is Kai's call, open as of 2026-09-12. So nothing derived from
it is committed either: `derive.py` has no default `--out` inside this
repository, and every number in `independence.txt` is a count or a
distribution rather than a record.

## Running it

    uv run --all-extras python evaluations/self-report-2026-09-17/derive.py \
      --corpus <dir>/deep-replies.json --traces <dir>/traced.json \
      --out <dir>/board --grader kai --grader <second>

    uv run --extra eval housecast grade serve <dir>/board \
      --profile evaluations/self-report-2026-09-17/profile.yaml --grader kai

`traced.json` is a JSON list of the reply ids carrying a `discord.reply` span,
which is two SigNoz queries over 2026-08-15 to 2026-08-20 rather than anything
`derive.py` fetches:

* group `discord.reply` spans by `attribute.messaging.message.id`
* the same over `discord.receive`, to separate a turn the service declined
  from one that emitted nothing

## What the board is

188 cases: 47 replies by four dimensions. 130 are scorable and 58 are
[non-scores](../../docs/grading-non-scores.md) the deriver seeds mechanically
into every grader's file.

* `self-report-fidelity` - 15 scorable, measured. Only the 15 replies carrying
  a tool rollup claim anything to check.
* `failure-disclosure` - 38 scorable, judged.
* `premise-correction` - 38 scorable, judged.
* `bounded-refusal` - 39 scorable, judged.

`test_type` carries `measured` or `judged` and `attribute` carries the
dimension, because those are two procedures over four subjects rather than
four kinds of test. Keeping the stamp on `test_type` is what stops a judged
call reaching the board wearing a measured one, which the spec records as
having happened twice during review.

## Where this departs from the spec

**The corpus holds 39 Deep replies, not 47.** Five are the service speaking in
place of the subject, in two classes: three `busy, retry shortly` and two
`reply blocked by response check, rephrase`. Three more carry no message text.
The spec and the MANIFEST both say 47 replies, and that is the count of
records; it is not the count of things Deep said. `derive.py` matches the
notice by its shape rather than its wording, and on this corpus that rule
selects exactly the five replies carrying a trace id.

**The exclusion is not independent, and the spec asked.** `independence.txt`
is the check the spec specified and left unrun. The untraced replies are not a
random sample of the corpus:

* traced, n=40: median 800 characters, 0 empty bodies, all 15 disclosures
* untraced, n=7: median 69 characters, 3 empty bodies, 0 disclosures

Hour of day separates them not at all, so this is not a telemetry outage
window. A missing `discord.reply` span tracks a turn that produced no reply.
One of the seven is a genuine Deep reply with no span, and that one is the
only real instrument gap in the set.

So the four untraced cases cannot be reported as a clean drop. They are a
finding about what the five days contain, and the talk should say so rather
than stating a denominator of 43 and moving on.

## What this board cannot say

Carried from the spec because every one is a sentence a room invites.

* Not a pass rate. 130 cells graded once by two people is a demonstration.
* One subject, one deployment, five days.
* Two humans wrote every prompt.
* 193 replies sit in a second guild no permission grant here reaches.
* `self-report-fidelity` rests on a window borrowed from an adjacency in
  `agent.go` that nothing declares and no test protects. Tracked as
  `teable:coilyco-gaming/sirens-echo#7448`.
