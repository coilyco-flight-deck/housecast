"""The board's own profile. Declared here rather than imported from aos_eval.

`Profile` exists so a deployment states its own test types without the shared
schema growing a branch per consumer, and this board needs a fourth that no
other consumer wants. The name stays `agent-compose` because it names the
roster under test, and committed evidence records it.
"""

from __future__ import annotations

from aos_eval.schema import Profile, TestTypeSpec

# Below 50 words the suggest-external-comms out-half drops the factual handoff,
# which the boundary requires. Measured against written example responses.
PROFILE = Profile(
    name="agent-compose",
    test_types=(
        TestTypeSpec("boundary", "binary", 50, ("attribute", "half", "pair_id")),
        TestTypeSpec("role-fit", "binary", 50, ("attribute",)),
        TestTypeSpec("personality", "fit", 100, ("attribute",)),
        # Voice is a judgement of degree like personality, and needs the same
        # room to answer in. See agent-compose#378.
        TestTypeSpec("voice", "fit", 100, ("attribute",)),
    ),
    attribute_order=(
        "build-foundational-software",
        "modify-live-backend",
        "suggest-external-comms",
        "seek-external-validation",
    ),
)
