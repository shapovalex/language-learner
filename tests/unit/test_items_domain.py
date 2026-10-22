"""Story 4.1: the Items content type and text normalization in domain/items.py (AD-10, AD-11,
AD-12).

- **ItemContent (AD-11).** One flat Pydantic union discriminated by `category`, camelCase on
  the wire, used unchanged by Draft responses, Save requests and Item reads. Vocabulary carries
  `target`, `russian`, `russianAlternatives`, `hint`, `partOfSpeech`, `grammar`, `example`,
  `exampleRussian` and `mnemonic`; Sentence carries `target`, `russian`, `russianAlternatives`,
  `hint` and `note`.
- **Russian meaning (AD-10).** `russian` is the primary meaning; `russianAlternatives` is a
  list, and an alternative may not contain a comma. A blank Target or Russian meaning is
  refused (a default this story takes: Anki refuses an empty first field, and the Produce and
  Write fronts show the Russian meaning).
- **normalize_text (AD-12).** NFC, casefold, surrounding whitespace and Unicode punctuation
  trimmed, inner whitespace collapsed to one space, and `’ ʼ ′ ‘` mapped to `'`. Diacritics
  stay significant.

`language_lab.domain.items` doesn't exist yet, so it is imported inside the tests.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from tests.support.items import SENTENCE, VOCABULARY, content

pytestmark = pytest.mark.skip(reason="ATDD red phase: un-skip when story 4.1 adds domain/items.py")


@pytest.mark.p0
@pytest.mark.parametrize("wire", [VOCABULARY, SENTENCE], ids=["vocabulary", "sentence"])
def test_item_content_is_one_type_discriminated_by_category(wire: dict[str, Any]) -> None:
    """AC-1: Vocabulary and Sentence content validate as one `ItemContent` by `category`, each
    with its own fields, and dump back to the same camelCase wire shape.
    """
    from language_lab.domain.items import ItemContent
    from pydantic import TypeAdapter

    validated = content(wire)

    assert TypeAdapter(ItemContent).dump_python(validated, by_alias=True) == wire


def _with(**changes: Any) -> dict[str, Any]:
    return {**VOCABULARY, **changes}


REFUSED = {
    "comma-in-an-alternative": _with(russianAlternatives=["торопиться, спешить"]),
    "comma-in-a-sentence-alternative": {**SENTENCE, "russianAlternatives": ["не спеши, подумай"]},
    "blank-target": _with(target=" \n "),
    "blank-russian": _with(russian=""),
    "unknown-category": _with(category="idiom"),
}


@pytest.mark.p0
@pytest.mark.parametrize("wire", REFUSED.values(), ids=REFUSED.keys())
def test_item_content_refuses_a_comma_alternative_or_a_blank_required_field(
    wire: dict[str, Any],
) -> None:
    """AC-2: an alternative containing a comma (AD-10), a blank Target or Russian meaning, or
    an unknown category is refused.
    """
    with pytest.raises(ValidationError):
        content(wire)


NORMALIZED = {
    "case-and-surrounding-space": ("  Jump to Conclusions  ", "jump to conclusions"),
    "surrounding-punctuation": ("“Jump to conclusions!”", "jump to conclusions"),
    "unicode-punctuation": ("¿Qué tal?", "qué tal"),
    "inner-punctuation-kept": ("un rendez-vous.", "un rendez-vous"),
    "inner-whitespace": ("jump \t to\n\n conclusions", "jump to conclusions"),
    "right-single-quote": ("I’d rather", "i'd rather"),
    "modifier-apostrophe": ("Iʼd rather", "i'd rather"),
    "prime": ("I′d rather", "i'd rather"),
    "left-single-quote": ("I‘d rather", "i'd rather"),
    "nfc": ("été", "été"),
    "casefold": ("Straße", "strasse"),
}


@pytest.mark.p0
@pytest.mark.parametrize(("text", "expected"), NORMALIZED.values(), ids=NORMALIZED.keys())
def test_normalize_text_applies_the_ad12_rules(text: str, expected: str) -> None:
    """AC-3: `normalize_text` applies NFC and casefold, trims surrounding whitespace and Unicode
    punctuation, collapses inner whitespace, and maps apostrophe variants to `'`.
    """
    from language_lab.domain.items import normalize_text

    assert normalize_text(text) == expected


@pytest.mark.p1
def test_normalize_text_keeps_diacritics_significant() -> None:
    """AC-3: `été` and `ete` stay different (AD-12)."""
    from language_lab.domain.items import normalize_text

    assert normalize_text("été") != normalize_text("ete")
