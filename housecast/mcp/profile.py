"""The MCP tool board's profile, loaded from the YAML the CLI also takes.

The YAML is the source and this is a reader, so there is one place the wording
lives. Holding the same readings in Python as well would have made a second
copy, and a second copy needs a drift check, which is the thing that was
silently off for the kit for months.

`housecast grade --profile housecast/data/mcp-tools-profile.yaml` gets the same
object this module exposes. That is the point: the board is reachable from the
command line without importing anything.

The readings are the whole reason the pairing exists. A tool description that
wins selection everywhere passes the in-half and fails the out-half, and a
board scoring only the in-half would call that a success.
"""

from __future__ import annotations

import pathlib

from housecast.grade.io import load_profile
from housecast.grade.schema import Profile

PROFILE_PATH = pathlib.Path(__file__).parent.parent / "data" / "mcp-tools-profile.yaml"


def mcp_tools() -> Profile:
    """Read the shipped profile. Raises if it is missing, rather than defaulting.

    Falling back to `DEFAULT_PROFILE` here would hand an MCP board the boundary
    vocabulary, which is exactly the failure this whole change removed.
    """
    if not PROFILE_PATH.is_file():
        raise FileNotFoundError(
            f"{PROFILE_PATH} is missing, so the MCP board has no taxonomy. "
            "It ships with the package; a checkout without it is incomplete."
        )
    return load_profile(PROFILE_PATH)


MCP_TOOLS = mcp_tools()
