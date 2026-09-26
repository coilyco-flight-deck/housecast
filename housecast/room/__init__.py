"""The live room: prompt intake, fan-out to subjects, divergence, and a restart log.

One process owns the whole room. A consumer brings `subjects.json` and nothing
else, so the room never learns where a subject's system prompt came from.
See docs/room.md.
"""
