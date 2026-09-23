"""The MCP tool board's profile, loaded from the YAML the CLI also takes.

The YAML is the one source, so no second copy needs a drift check, and
`--profile housecast/data/mcp-tools-profile.yaml` yields this same object. The
readings are why the pairing exists: a description that wins selection everywhere
passes the in-half and fails the out-half, which an in-half-only board calls success.
"""

from __future__ import annotations

import pathlib

from housecast.grade.io import load_profile
from housecast.grade.schema import Profile

PROFILE_PATH = pathlib.Path(__file__).parent.parent / "data" / "mcp-tools-profile.yaml"


def mcp_tools() -> Profile:
    """Read the shipped profile. Raises if it is missing, rather than defaulting.

    Falling back to another deployment's profile here would hand an MCP board
    vocabulary it does not use.
    """
    if not PROFILE_PATH.is_file():
        raise FileNotFoundError(
            f"{PROFILE_PATH} is missing, so the MCP board has no taxonomy. "
            "It ships with the package; a checkout without it is incomplete."
        )
    return load_profile(PROFILE_PATH)


MCP_TOOLS = mcp_tools()
