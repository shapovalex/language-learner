"""Items' content type and its generated-fields models (AD-11), a stored Item, the Save audio
intent (AD-6), and text normalization (AD-12).

`ItemContent` is one flat union discriminated by `category`, camelCase on the wire, used
unchanged by Draft responses, Save requests and Item reads. `russian` is the primary meaning and
`russianAlternatives` a list whose entries may not contain a comma (AD-10); only the Anki adapter
joins and splits it.

The generated-fields models are what the LLM answers with, per Category: `ItemContent` less
`target` (input, never generated), `category` (the model chosen) and `mnemonic` (FR-14), and for
Sentence less `example` (FR-15). `strict_json_schema()` is the schema OpenRouter gets, and the
same model validates the reply.
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from language_lab.domain.catalog import Category

_APOSTROPHES = str.maketrans(dict.fromkeys("’ʼ′‘", "'"))
_WHITESPACE = re.compile(r"\s+")


def _not_blank(text: str) -> str:
    if not text.strip():
        raise ValueError("blank")
    return text  # stored exactly as typed


# Non-blank text, kept as typed: an Item's Target and Russian, a Capture's text, a Draft's Target
NonBlank = Annotated[str, AfterValidator(_not_blank)]


class AudioIntent(StrEnum):
    """What Save does with the Item's `Audio` field (AD-6)."""

    KEEP = "keep"
    REPLACE = "replace"
    REMOVE = "remove"


def _alternatives(alternatives: list[str]) -> list[str]:
    for alternative in alternatives:
        if not alternative.strip() or "," in alternative:
            raise ValueError("an alternative is blank or contains a comma")
    return alternatives


_Alternatives = Annotated[list[str], AfterValidator(_alternatives)]


class _Content(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, frozen=True)

    target: NonBlank
    russian: NonBlank
    russian_alternatives: _Alternatives = []
    hint: str = ""


class VocabularyContent(_Content):
    category: Literal[Category.VOCABULARY]
    part_of_speech: str = ""
    grammar: str = ""
    example: str = ""
    example_russian: str = ""
    mnemonic: str = ""


class SentenceContent(_Content):
    category: Literal[Category.SENTENCE]
    note: str = ""


ItemContent = Annotated[VocabularyContent | SentenceContent, Field(discriminator="category")]


@dataclass(frozen=True)
class Item:
    """An Item as Anki holds it: its ItemId (AD-8), its content (AD-11), and whether its
    `Audio` field holds Reference audio: read-only list metadata, never part of the content.
    """

    item_id: str
    content: VocabularyContent | SentenceContent
    has_audio: bool = False
    audio: str | None = None

    def wire(self) -> dict[str, Any]:
        """The Item on the wire: `{itemId, ...ItemContent}`, flat like the Draft and the Save."""
        return {"itemId": self.item_id, **self.content.model_dump(by_alias=True, mode="json")}


class _Generated(BaseModel):
    # Every field required, none defaulted: the strict schema has no defaults (AD-11)
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, frozen=True, extra="forbid"
    )
    _content: ClassVar[type[VocabularyContent] | type[SentenceContent]]
    _category: ClassVar[Category]

    russian: NonBlank
    russian_alternatives: _Alternatives
    hint: str | None

    def to_content(self, target: str) -> VocabularyContent | SentenceContent:
        """The Draft's ItemContent: `target` as given, nulls as empty, and no mnemonic."""
        fields = {name: "" if value is None else value for name, value in self}
        return self._content(category=self._category, target=target, **fields)


class GeneratedVocabulary(_Generated):
    _content = VocabularyContent
    _category = Category.VOCABULARY

    part_of_speech: str | None
    grammar: str | None
    example: str  # one example by default (FR-14)
    example_russian: str


class GeneratedSentence(_Generated):
    _content = SentenceContent
    _category = Category.SENTENCE

    note: str | None


type GeneratedFields = GeneratedVocabulary | GeneratedSentence

_GENERATED: dict[Category, type[GeneratedVocabulary] | type[GeneratedSentence]] = {
    Category.VOCABULARY: GeneratedVocabulary,
    Category.SENTENCE: GeneratedSentence,
}


def generated_model(category: Category) -> type[GeneratedVocabulary] | type[GeneratedSentence]:
    """The generated-fields model of `category`."""
    return _GENERATED[category]


def _strict(node: Any) -> Any:
    """`node` with titles and defaults dropped, a nullable `anyOf` as a type list, and every
    object closed with all of its properties required.
    """
    if isinstance(node, list):
        return [_strict(value) for value in node]
    if not isinstance(node, dict):
        return node
    strict = {
        key: (
            {name: _strict(prop) for name, prop in value.items()}
            if key == "properties"
            else _strict(value)
        )
        for key, value in node.items()
        if key not in ("title", "default")
    }
    options = strict.get("anyOf")
    if options and all(set(option) == {"type"} for option in options):
        del strict["anyOf"]
        strict["type"] = [option["type"] for option in options]
    if "properties" in strict:
        strict["additionalProperties"] = False
        strict["required"] = list(strict["properties"])
    return strict


def strict_json_schema(category: Category) -> dict[str, Any]:
    """The JSON Schema of `category`'s generated fields for strict structured output (AD-11):
    closed objects, every property required, optional fields nullable, and no defaults.
    """
    return _strict(generated_model(category).model_json_schema(by_alias=True))


def _is_edge(char: str) -> bool:
    return char.isspace() or unicodedata.category(char).startswith("P")


def normalize_text(text: str) -> str:
    """`text` for matching (AD-12): NFC, casefold, apostrophe variants as `'`, inner whitespace
    collapsed to one space, and surrounding whitespace and Unicode punctuation trimmed.
    Diacritics stay significant.
    """
    folded = unicodedata.normalize("NFC", text).translate(_APOSTROPHES).casefold()
    folded = _WHITESPACE.sub(" ", unicodedata.normalize("NFC", folded))
    start, end = 0, len(folded)
    while start < end and _is_edge(folded[start]):
        start += 1
    while end > start and _is_edge(folded[end - 1]):
        end -= 1
    return folded[start:end]
