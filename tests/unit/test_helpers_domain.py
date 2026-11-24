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
    EXAMPLE_CHOICES,
    EXAMPLES,
    GRAMMAR_CORRECT,
    GRAMMAR_INCORRECT,
    LEVELS,
    MALFORMED_CHOICES,
    MALFORMED_EXAMPLES,
    TRANSLATION,
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
        {**GRAMMAR_INCORRECT, "corrected": None},
        {**GRAMMAR_INCORRECT, "corrected": "  "},
    ],
    ids=["explanation-missing", "extra-field", "wrong-no-correction", "wrong-blank-correction"],
)
def test_a_verdict_outside_the_schema_is_invalid(reply: dict[str, Any]) -> None:
    """[P1] M-4 a verdict missing a field or carrying one more, or a wrong Target with no
    correction, is invalid output.
    """
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


@pytest.mark.p0
def test_a_translation_round_trips() -> None:
    """[P0] Capture and translate: `{russian}` validates and dumps back as the same wire."""
    from language_lab.domain.helpers import Translation

    assert Translation.model_validate(TRANSLATION).model_dump(by_alias=True) == TRANSLATION


@pytest.mark.p1
@pytest.mark.parametrize(
    "reply",
    [{}, {"russian": "   "}, {**TRANSLATION, "alternatives": []}],
    ids=["russian-missing", "blank-russian", "extra-field"],
)
def test_a_translation_outside_the_schema_is_invalid(reply: dict[str, Any]) -> None:
    """[P1] a missing or blank Russian, or a field more, is invalid output."""
    from language_lab.domain.helpers import Translation

    with pytest.raises(ValidationError):
        Translation.model_validate(reply)


@pytest.mark.p1
def test_the_translation_schema_is_strict() -> None:
    """[P1] the strict schema is closed with `russian` required."""
    from language_lab.domain.helpers import translation_json_schema

    schema = translation_json_schema()
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["russian"]


def example_choices(reply: dict[str, Any]) -> Any:
    from language_lab.domain.helpers import ExampleChoices

    return ExampleChoices.model_validate(reply)


@pytest.mark.p1
def test_ten_example_choices_round_trip_on_the_wire() -> None:
    """[P1] Regenerate example: exactly ten `{sentence, russian}` pairs validate and dump back
    unchanged.
    """
    choices = example_choices(EXAMPLE_CHOICES)

    assert len(choices.sentences) == 10
    assert choices.model_dump(by_alias=True, mode="json") == EXAMPLE_CHOICES


@pytest.mark.p1
@pytest.mark.parametrize("malformed", MALFORMED_CHOICES.values(), ids=MALFORMED_CHOICES.keys())
def test_anything_but_ten_non_blank_choices_fails_validation(malformed: dict[str, Any]) -> None:
    """[P1] nine or eleven pairs, or a blank field, fail validation: the adapter's retry."""
    with pytest.raises(ValidationError):
        example_choices(malformed)


@pytest.mark.p2
def test_the_example_choices_schema_is_strict() -> None:
    """[P2] the strict schema is closed, with `sentences` the only, required property."""
    from language_lab.domain.helpers import example_choices_json_schema

    schema = example_choices_json_schema()

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["sentences"]
