"""Items' content type (AD-11), the Save audio intent (AD-6), and text normalization (AD-12).

`ItemContent` is one flat union discriminated by `category`, camelCase on the wire, used
unchanged by Draft responses, Save requests and Item reads. `russian` is the primary meaning and
`russianAlternatives` a list whose entries may not contain a comma (AD-10); only the Anki adapter
joins and splits it.
"""

import re
import unicodedata
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from language_lab.domain.catalog import Category

_APOSTROPHES = str.maketrans(dict.fromkeys("’ʼ′‘", "'"))
_WHITESPACE = re.compile(r"\s+")


class AudioIntent(StrEnum):
    """What Save does with the Item's `Audio` field (AD-6)."""

    KEEP = "keep"
    REPLACE = "replace"
    REMOVE = "remove"


def _not_blank(text: str) -> str:
    if not text.strip():
        raise ValueError("blank")
    return text  # stored exactly as typed


def _alternatives(alternatives: list[str]) -> list[str]:
    for alternative in alternatives:
        if not alternative.strip() or "," in alternative:
            raise ValueError("an alternative is blank or contains a comma")
    return alternatives


_Required = Annotated[str, AfterValidator(_not_blank)]
_Alternatives = Annotated[list[str], AfterValidator(_alternatives)]


class _Content(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, frozen=True)

    target: _Required
    russian: _Required
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
