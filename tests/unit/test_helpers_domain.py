"""Target helpers RED: the grammar verdict and the CEFR example sentences on the wire
(plan target-grammar-check-and-cefr-examples; I/O matrix M-1..M-4).

`domain/helpers.py` holds `CefrLevel` (A1..C2), `GrammarCheck {correct, corrected,
explanation}`, `ExampleSentence {sentence, russian}`, `LevelExamples {level, sentences}` and
`ExampleSet {levels}`, camelCase on the wire like `domain/items.py`. The strict schema can't
count array items, so pydantic enforces the shape: exactly the six levels in A1→C2 order, five
sentences each. Anything else fails validation and takes the adapter's invalid-output retry.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from tests.support.helpers import (
    EXAMPLES,
    GRAMMAR_CORRECT,
    GRAMMAR_INCORRECT,
    LEVELS,
    MALFORMED_EXAMPLES,
)

pytestmark = pytest.mark.skip(
    reason="Target helpers RED scaffold: activate when implementing the plan"
)


def grammar_check(reply: dict[str, Any]) -> Any:
    from language_lab.domain.helpers import GrammarCheck

    return GrammarCheck.model_validate(reply)


def example_set(reply: dict[str, Any]) -> Any:
    from language_lab.domain.helpers import ExampleSet

    return ExampleSet.model_validate(reply)


@pytest.mark.p1
def test_cefr_levels_are_a1_to_c2_in_order() -> None:
    """[P1] M-3 `CefrLevel` is the six CEFR levels, A1 to C2, in that order."""
    from language_lab.domain.helpers import CefrLevel

    assert [str(level) for level in CefrLevel] == LEVELS


@pytest.mark.p0
def test_a_correct_verdict_has_no_correction() -> None:
    """[P0] M-1 a correct Target: `correct` true, `corrected` null, a Russian explanation."""
    check = grammar_check(GRAMMAR_CORRECT)

    assert check.correct is True
    assert check.corrected is None
    assert check.model_dump(by_alias=True, mode="json") == GRAMMAR_CORRECT


@pytest.mark.p0
def test_an_incorrect_verdict_carries_the_corrected_target() -> None:
    """[P0] M-2 a wrong Target: `correct` false with the corrected text and the explanation."""
    check = grammar_check(GRAMMAR_INCORRECT)

    assert check.corrected == "He goes to school."
    assert check.correct is False
    assert check.model_dump(by_alias=True, mode="json") == GRAMMAR_INCORRECT


@pytest.mark.p1
@pytest.mark.parametrize(
    "reply",
    [
        {k: v for k, v in GRAMMAR_INCORRECT.items() if k != "explanation"},
        {**GRAMMAR_CORRECT, "confidence": 0.9},
    ],
    ids=["explanation-missing", "extra-field"],
)
def test_a_verdict_outside_the_schema_is_invalid(reply: dict[str, Any]) -> None:
    """[P1] M-4 a verdict missing a field or carrying one more is invalid output."""
    with pytest.raises(ValidationError):
        grammar_check(reply)


@pytest.mark.p0
def test_six_levels_of_five_sentences_validate_and_round_trip() -> None:
    """[P0] M-3 A1..C2 with five sentences each validates, and dumps back as the same wire."""
    examples = example_set(EXAMPLES)

    assert [str(group.level) for group in examples.levels] == LEVELS
    assert [len(group.sentences) for group in examples.levels] == [5] * 6
    assert examples.model_dump(by_alias=True, mode="json") == EXAMPLES


@pytest.mark.p1
@pytest.mark.parametrize("reply", MALFORMED_EXAMPLES.values(), ids=MALFORMED_EXAMPLES.keys())
def test_a_malformed_example_set_is_invalid(reply: dict[str, Any]) -> None:
    """[P1] M-4 a level missing, repeated or out of order, or a level without exactly five
    sentences, fails validation: the invalid output the adapter retries.
    """
    with pytest.raises(ValidationError):
        example_set(reply)


@pytest.mark.p1
@pytest.mark.parametrize(
    "change",
    [
        lambda reply: reply["levels"][0].update(level="D1"),
        lambda reply: reply["levels"][2]["sentences"][0].pop("russian"),
        lambda reply: reply["levels"][4]["sentences"][1].update(sentence="   "),
    ],
    ids=["unknown-level", "russian-missing", "blank-sentence"],
)
def test_an_unknown_level_or_an_incomplete_sentence_is_invalid(change: Any) -> None:
    """[P1] M-4 an unknown level, a sentence without its Russian, or a blank sentence."""
    import copy

    reply = copy.deepcopy(EXAMPLES)
    change(reply)

    with pytest.raises(ValidationError):
        example_set(reply)
