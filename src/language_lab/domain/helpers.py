"""The Target helpers' answers on the wire (AD-11): the grammar verdict and the CEFR example
sentences, camelCase like `domain/items.py`, and the strict JSON Schemas OpenRouter gets.

The strict schema can't count array items, so pydantic enforces the examples' shape: exactly the
six CEFR levels in A1→C2 order, five sentences each. Anything else fails validation, which the
adapter treats as invalid output (one retry, then `llm_invalid_output`). Nothing here is stored.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

from language_lab.domain.items import NonBlank, strict_schema

SENTENCES_PER_LEVEL = 5


class CefrLevel(StrEnum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class _Answer(BaseModel):
    # Every field required, none defaulted, nothing extra: the strict schema's shape (AD-11)
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, frozen=True, extra="forbid"
    )


class GrammarCheck(_Answer):
    """Whether a Target is grammatical, its corrected form when it isn't, and why, in Russian."""

    correct: bool
    corrected: str | None
    explanation: NonBlank

    @model_validator(mode="after")
    def _wrong_has_correction(self) -> GrammarCheck:
        # A wrong Target with no correction would read as correct: invalid output, retried
        if not self.correct and not (self.corrected or "").strip():
            raise ValueError("an incorrect Target needs its correction")
        return self


class ExampleSentence(_Answer):
    sentence: NonBlank
    russian: NonBlank


class LevelExamples(_Answer):
    level: CefrLevel
    sentences: list[ExampleSentence]

    @model_validator(mode="after")
    def _five_sentences(self) -> LevelExamples:
        if len(self.sentences) != SENTENCES_PER_LEVEL:
            raise ValueError(f"{self.level} needs {SENTENCES_PER_LEVEL} sentences")
        return self


class ExampleSet(_Answer):
    """Five example sentences, each with its Russian, for every CEFR level A1 to C2 in order."""

    levels: list[LevelExamples]

    @model_validator(mode="after")
    def _six_levels_in_order(self) -> ExampleSet:
        if [group.level for group in self.levels] != list(CefrLevel):
            raise ValueError("levels must be A1, A2, B1, B2, C1, C2 in order")
        return self


def grammar_json_schema() -> dict[str, Any]:
    """The strict JSON Schema of a grammar verdict."""
    return strict_schema(GrammarCheck)


def examples_json_schema() -> dict[str, Any]:
    """The strict JSON Schema of an example set (its 6 × 5 shape is checked on validation)."""
    return strict_schema(ExampleSet)
