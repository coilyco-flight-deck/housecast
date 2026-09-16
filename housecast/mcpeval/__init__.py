"""The MCP tool-description evaluation loop.

Change a tool's description and know if it helped.

This package is the whole loop and nothing else: an HTTP MCP subject to point
at, a runner that makes real model calls against it, deterministic grading, a
concurrent run over a task's prompts, a paired comparison, and the visual flow
a tester drives it from.

The shape is fixed by `teable:coilyco-flight-deck/housecast#7816` and the
customer brief. Three things about it are load-bearing and are easy to undo by
accident:

* housecast is the middle. It is the MCP client and the model client, and the
  model never speaks to the subject. That is what makes the loop
  language-agnostic: the subject can be Node, Go, anything that serves HTTP MCP.
* the prose edit never mutates the running subject. `definitions.py` overlays a
  clone of what `tools/list` returned, in memory, between the list and the model
  call. The subject the tool calls are routed back to is the unedited one.
* a task holds 10-25 prompts and a run executes all of them against one
  definition set. Two runs of one task with one thing changed are the two arms
  of a controlled experiment, and the comparison is paired prompt to prompt.
  Never two averages.
"""

from __future__ import annotations

__all__ = ["__doc__"]
