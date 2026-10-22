"""Item test data, shared by the Item domain, integration and API tests (tests/unit/
test_items_domain.py, tests/integration/test_anki_item_save.py, tests/api/test_items_save.py).

`VOCABULARY` and `SENTENCE` are ItemContent on the wire (camelCase, AD-11), every field filled,
with characters the codec escapes and a newline it turns into `<br>` (AD-9). `content(wire)`
validates one into `ItemContent`; `stored_fields(wire, item_id)` is what Save leaves in the
note's fields. `language_lab.domain.items` is imported inside the functions, so collection
passes before it exists.
"""

from typing import Any

from language_lab.adapters.anki.codec import encode_field, join_alternatives
from language_lab.adapters.anki.manifest import SCHEMA_VERSION
from tests.support.captures import PREFIX

NOTE_TYPES = {
    ("en", "vocabulary"): f"{PREFIX} English Vocabulary",
    ("en", "sentence"): f"{PREFIX} English Sentence",
    ("fr", "vocabulary"): f"{PREFIX} French Vocabulary",
    ("fr", "sentence"): f"{PREFIX} French Sentence",
}

VOCABULARY: dict[str, Any] = {
    "category": "vocabulary",
    "target": "jump to conclusions",
    "russian": "делать поспешные выводы",
    "russianAlternatives": ["торопиться с выводами", "спешить с выводами"],
    "hint": "about <evidence> & data",
    "partOfSpeech": "phrase",
    "grammar": "jump to conclusions about sth",
    "example": "Let's not jump to conclusions.\nWait for the data.",
    "exampleRussian": "Давай не будем делать поспешных выводов.",
    "mnemonic": "a leap over the facts",
}

SENTENCE: dict[str, Any] = {
    "category": "sentence",
    "target": "Ne tirons pas de conclusions hâtives.",
    "russian": "Не будем делать поспешных выводов.",
    "russianAlternatives": ["Не надо спешить с выводами."],
    "hint": "tirer des <conclusions>",
    "note": "hâtif & hâtive\nagree with the noun",
}

# ItemContent's wire keys -> the note type's fields (manifest.py)
FIELDS = {
    "target": "Target",
    "russian": "Russian",
    "hint": "Hint",
    "partOfSpeech": "PartOfSpeech",
    "grammar": "Grammar",
    "example": "Example",
    "exampleRussian": "ExampleRussian",
    "mnemonic": "Mnemonic",
    "note": "Note",
}


def content(wire: dict[str, Any]) -> Any:
    """`wire` validated as `ItemContent` (AD-11)."""
    from language_lab.domain.items import ItemContent
    from pydantic import TypeAdapter

    return TypeAdapter(ItemContent).validate_python(wire)


def keep() -> Any:
    """The `keep` audio intent (AD-6), the only one this story builds."""
    from language_lab.domain.items import AudioIntent

    return AudioIntent.KEEP


def stored_fields(wire: dict[str, Any], item_id: str) -> dict[str, str]:
    """The fields a new note holds after Save of `wire`: each through the codec, the
    alternatives joined with `", "`, Audio empty (keep, with no audio), ItemId and SchemaVersion.
    """
    fields = {FIELDS[key]: encode_field(value) for key, value in wire.items() if key in FIELDS}
    fields["RussianAlternatives"] = encode_field(join_alternatives(wire["russianAlternatives"]))
    fields["Audio"] = ""
    fields["ItemId"] = item_id
    fields["SchemaVersion"] = str(SCHEMA_VERSION)
    return fields


def note_type_of(language: str, wire: dict[str, Any]) -> str:
    return NOTE_TYPES[(language, wire["category"])]
