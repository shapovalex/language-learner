"""Changes to a set-up `LanguageLab` Prefix, shared by the Setup preview and apply tests.

Each mutator makes one change to a `managed_collection(MANIFEST)`; `from_set_up(change)` is a
builder of a fresh set-up collection with that change. `as_tuples(items)` is a plan's items as
`(action, kind, name)` tuples, to compare as a set.
"""

from collections.abc import Callable
from typing import Any

from language_lab.adapters.anki.manifest import build_manifest
from tests.support.anki_state import (
    DEFAULT_PRESET,
    Collection,
    managed_collection,
    preset_config,
    set_path,
)

PREFIX = "LanguageLab"
MANIFEST = build_manifest(PREFIX)

VOCABULARY = f"{PREFIX} English Vocabulary"
SENTENCE = f"{PREFIX} French Sentence"
STUDY_LEAF = f"{PREFIX}::Study::English::Vocabulary::Produce"
READING_RULE = f"{PREFIX} French Reading Rule"
READING_RULES_DECK = f"{PREFIX}::Study::French::Reading Rules"
DELETED_RULE = MANIFEST.reading_rules[1]  # "ou + vowel"


def as_tuples(items: Any) -> set[tuple[str, str, str]]:
    return {(str(item.action), str(item.kind), item.name) for item in items}


def from_set_up(change: Callable[[Collection], None]) -> Callable[[], Collection]:
    def build() -> Collection:
        collection = managed_collection(MANIFEST)
        change(collection)
        return collection

    return build


def changed_front(c: Collection) -> None:
    c.models[VOCABULARY].templates["Produce"]["Front"] += "<hr>"


def changed_css(c: Collection) -> None:
    c.models[SENTENCE].css += "\n.card { color: red; }"


def missing_card_template(c: Collection) -> None:
    del c.models[VOCABULARY].templates["Pronounce"]


def missing_deck(c: Collection) -> None:
    del c.decks[STUDY_LEAF]


def missing_note_type(c: Collection) -> None:
    del c.models[f"{PREFIX} Capture"]


def bury_flag_on(c: Collection) -> None:
    set_path(c.presets[PREFIX], "rev.bury", True)


def deck_on_default(c: Collection) -> None:
    c.decks[STUDY_LEAF] = DEFAULT_PRESET


def no_preset(c: Collection) -> None:
    del c.presets[PREFIX]
    for deck, preset in c.decks.items():
        if preset == PREFIX:
            c.decks[deck] = DEFAULT_PRESET


def two_prefix_presets(c: Collection) -> None:
    c.presets["Twin"] = preset_config(PREFIX)  # a second config named the Prefix, its own id
    c.decks[STUDY_LEAF] = "Twin"


def user_options(c: Collection) -> None:
    for path, value in {"new.perDay": 50, "rev.maxIvl": 3650, "desiredRetention": 0.85}.items():
        set_path(c.presets[PREFIX], path, value)


def field_removed(c: Collection) -> None:
    c.models[VOCABULARY].fields.remove("Mnemonic")


def rule_deleted(c: Collection) -> None:
    """The user deleted one reading rule's note (and so its card) in Anki; its media stay."""
    (note_id,) = (i for i, n in c.notes.items() if n.fields.get("RuleId") == DELETED_RULE.id)
    del c.notes[note_id]
    for card_id in [i for i, card in c.cards.items() if card.note == note_id]:
        del c.cards[card_id]
