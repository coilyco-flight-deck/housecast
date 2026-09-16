"""The MCP board's profile: its test types, and how a graded pair reads back.

Declaring a profile is how a second board adopts the schema without the schema
growing a branch for it. This is the first one that is not a role board, and it
is the reason `TestTypeSpec.readings` exists: four boundary sentences used to
live inside the grading page and made every board a boundary board.

The readings are the whole point of the pairing. A tool description that wins
selection everywhere passes the in-half and fails the out-half, and a board
that scored only the in-half would call that a success.
"""

from __future__ import annotations

from types import MappingProxyType

from housecast.grade.schema import Profile, TestTypeSpec

PAIRED = ("attribute", "half", "pair_id")

SELECTABLE = TestTypeSpec(
    "selectable",
    "binary",
    50,
    PAIRED,
    readings=MappingProxyType(
        {
            "pass/pass": "reachable for its own task, and no other",
            "fail/pass": "not reachable for the task it is for",
            "pass/fail": "fires on its neighbour's task",
            "fail/fail": "the description selects nothing correctly",
        }
    ),
)

DESCRIPTION_GROUNDED = TestTypeSpec(
    "description-grounded",
    "binary",
    50,
    PAIRED,
    readings=MappingProxyType(
        {
            "pass/pass": "claims what it does, and does what it claims",
            "fail/pass": "claims a capability the schema cannot reach",
            "pass/fail": "does more than it admits to",
            "fail/fail": "the description and the tool are unrelated",
        }
    ),
)

SCHEMA_HONEST = TestTypeSpec(
    "schema-honest",
    "binary",
    50,
    PAIRED,
    readings=MappingProxyType(
        {
            "pass/pass": "the schema refuses what the handler would have to",
            "fail/pass": "rejects a call the schema declares valid",
            "pass/fail": "accepts a call only the handler refuses",
            "fail/fail": "the schema constrains nothing",
        }
    ),
)

BOUNDED_FAILURE = TestTypeSpec(
    "bounded-failure",
    "binary",
    50,
    PAIRED,
    readings=MappingProxyType(
        {
            "pass/pass": "an error a model can act on, both ways",
            "fail/pass": "a valid call errors",
            "pass/fail": "an invalid call returns a silent empty or a stack trace",
            "fail/fail": "failure is unreadable in both directions",
        }
    ),
)

MCP_TOOLS = Profile(
    name="mcp-tools",
    # `selectable` and `description-grounded` are adjacent on purpose. O-4 makes
    # the second mandatory wherever the loop optimizes the first.
    test_types=(SELECTABLE, DESCRIPTION_GROUNDED, SCHEMA_HONEST, BOUNDED_FAILURE),
    group_by="entity",
)
