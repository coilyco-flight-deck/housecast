"""The MCP tool-description evaluation loop: change a description, know if it helped.

housecast is the middle, the MCP client and the model client, so the subject can be
any language serving HTTP MCP. A prose edit overlays a clone of `tools/list` and never
mutates the running subject. Two runs of one task with one change are paired prompt
to prompt, never compared as two averages. Shape: housecast#7816.
"""

from __future__ import annotations

__all__ = ["__doc__"]
