"""The board's own profile. Declared here rather than imported from housecast.grade.

`Profile` exists so a deployment states its own test types without the shared
schema growing a branch per consumer, and this board needs a fourth that no
other consumer wants. The name stays `agent-compose` because it names the
roster under test, and committed evidence records it.
"""

from __future__ import annotations

from housecast.grade.schema import Profile, TestTypeSpec

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
        # Paired for boundary's reason: the out-half is what stops hedging
        # scoring as grounding. See docs/grading-grounding.md.
        TestTypeSpec("grounding", "binary", 50, ("attribute", "half", "pair_id")),
    ),
    attribute_order=(
        "build-foundational-software",
        "modify-live-backend",
        "suggest-external-comms",
        "seek-external-validation",
    ),
)
