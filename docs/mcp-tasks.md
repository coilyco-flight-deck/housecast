# MCP loop tasks

What a task file under `housecast/mcpeval/tasks/` is, and what it withholds.

## A capability, not a case

`transcribe-video.yaml` carries twenty prompts. Past ten, prompts cost machine
time rather than review time, and a sign test needs 15 of 20 to move where it
needs 9 of 10.

## What the model never sees

Nothing in a task file is sent to the model, which sees the prompt text and the
subject's own tool descriptions only. `rules` is the grader's, and a rule naming
the expected calls would measure whether the agent can read the answer key.
Top-level `rules` apply to every prompt, and each prompt overrides them.

## The edge case

p13 and p14 point at a file with no audio track. The correct behaviour is to
discover that and tell the user, not to transcribe.
