from typing import Any

import pytest

from housecast.grade.board import BOARD_SCHEMA, BoardError, load_board
from housecast.grade.schema import AGENT_COMPOSE, Profile, TestTypeSpec

SOLO = Profile(name="solo", test_types=(TestTypeSpec("clause", "binary", 50, ("attribute",)),))


def board(**overrides: Any) -> dict[str, Any]:
    raw = {
        "schema": BOARD_SCHEMA,
        "contexts": {"platform": "you build things"},
        "challenges": [
            {
                "id": "platform-a",
                "entity": "platform",
                "test_type": "clause",
                "attribute": "build",
                "prompt": "ship it",
                "target": "builds it",
            }
        ],
    }
    raw.update(overrides)
    return raw


def test_a_board_carries_its_contexts_and_challenges() -> None:
    loaded = load_board(board(), SOLO)
    assert loaded.entities == ["platform"]
    assert loaded.context_for(loaded.challenges[0]) == "you build things"


def test_a_deployment_may_namespace_the_schema() -> None:
    assert load_board(board(schema="sirens-discord-ops.board.v1"), SOLO).entities == ["platform"]


def test_another_schema_is_refused() -> None:
    with pytest.raises(BoardError, match="is not a board"):
        load_board(board(schema="aos-eval.attributes.v1"), SOLO)


def test_an_unwritten_challenge_is_refused_before_the_model_call() -> None:
    raw = board()
    del raw["challenges"][0]["prompt"]
    with pytest.raises(BoardError, match="unwritten"):
        load_board(raw, SOLO)


def test_a_challenge_with_no_context_is_refused() -> None:
    raw = board()
    raw["challenges"][0]["entity"] = "sysadmin"
    with pytest.raises(BoardError, match="no context for entity 'sysadmin'"):
        load_board(raw, SOLO)


def test_a_context_no_challenge_uses_is_refused() -> None:
    raw = board()
    raw["contexts"]["advocate"] = "you write things"
    with pytest.raises(BoardError, match="context with no challenge: advocate"):
        load_board(raw, SOLO)


def test_an_empty_context_is_refused() -> None:
    with pytest.raises(BoardError, match="context is empty"):
        load_board(board(contexts={"platform": "   "}), SOLO)


def test_an_empty_board_is_refused() -> None:
    with pytest.raises(BoardError, match="no challenges"):
        load_board(board(challenges=[]), SOLO)


def test_the_profile_still_decides_what_a_challenge_must_carry() -> None:
    raw = board()
    del raw["challenges"][0]["attribute"]
    with pytest.raises(BoardError, match="needs attribute"):
        load_board(raw, SOLO)


def test_a_transcript_is_a_question_the_same_way_a_prompt_is() -> None:
    raw = board()
    del raw["challenges"][0]["prompt"]
    raw["challenges"][0]["turns"] = [
        {"role": "user", "content": "morning"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "ship it"},
    ]
    loaded = load_board(raw, SOLO)
    assert loaded.challenges[0].turns[-1].content == "ship it"
    assert loaded.challenges[0].written


def test_a_challenge_carrying_both_a_prompt_and_turns_is_refused() -> None:
    raw = board()
    raw["challenges"][0]["turns"] = [{"role": "user", "content": "ship it"}]
    with pytest.raises(BoardError, match="prompt or turns, never both"):
        load_board(raw, SOLO)


def test_provenance_is_the_deployment_s_and_travels_untouched() -> None:
    loaded = load_board(board(provenance={"model": "x", "composed": "sha"}), SOLO)
    assert loaded.provenance == {"model": "x", "composed": "sha"}


def test_the_built_in_profile_is_the_default() -> None:
    raw = board()
    raw["challenges"][0]["test_type"] = "boundary"
    raw["challenges"][0]["half"] = "in"
    raw["challenges"][0]["pair_id"] = "platform-a"
    assert load_board(raw, AGENT_COMPOSE).entities == ["platform"]
