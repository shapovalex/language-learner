"""The managed manifest (AD-3, A3): the one source of Anki names and structure.

`build_manifest(prefix)` declares, from the Prefix alone, the five note types with their fields,
card templates and CSS (read from `templates/` as package data), the 28-deck tree, where each
card ord goes, the `<Prefix>` preset with its three bury flags, and the current SchemaVersion.
Setup diffs Anki against it; every feature reads Anki names from it.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from types import MappingProxyType

from language_lab.domain.catalog import Category, Exercise, Language
from language_lab.settings import PREFIX_PATTERN

SCHEMA_VERSION = 1

EXERCISE_BY_ORD: Mapping[int, Exercise] = MappingProxyType(
    {0: Exercise.UNDERSTAND, 1: Exercise.PRODUCE, 2: Exercise.WRITE, 3: Exercise.PRONOUNCE}
)
_STUDY_ORDS = (0, 1, 2)  # ord 3 (Pronounce) goes to the Pronunciation branch

_LANGUAGE_NAMES: Mapping[Language, str] = {Language.EN: "English", Language.FR: "French"}
# (note type word, deck word): the note type is singular, the deck plural (A3)
_CATEGORY_NAMES: Mapping[Category, tuple[str, str]] = {
    Category.VOCABULARY: ("Vocabulary", "Vocabulary"),
    Category.SENTENCE: ("Sentence", "Sentences"),
}

# Target/Text first: Anki sorts and checks duplicates by the first field (decided 2026-10-21).
# Hidden means no card template renders the field.
_HIDDEN = frozenset({"ItemId", "CaptureId", "SchemaVersion"})
_FIELDS: Mapping[Category | None, tuple[str, ...]] = {
    Category.VOCABULARY: (
        "Target",
        "Russian",
        "RussianAlternatives",
        "Hint",
        "PartOfSpeech",
        "Grammar",
        "Example",
        "ExampleRussian",
        "Mnemonic",
        "Audio",
        "ItemId",
        "SchemaVersion",
    ),
    Category.SENTENCE: (
        "Target",
        "Russian",
        "RussianAlternatives",
        "Hint",
        "Note",
        "Audio",
        "ItemId",
        "SchemaVersion",
    ),
    None: ("Text", "CreatedAt", "CaptureId", "SchemaVersion"),  # Capture
}

BURY_FLAGS: Mapping[str, bool] = MappingProxyType(
    {"new.bury": False, "rev.bury": False, "buryInterdayLearning": False}
)

_TEMPLATES = files("language_lab.adapters.anki") / "templates"


def _template_text(name: str) -> str:
    return (_TEMPLATES / name).read_text(encoding="utf-8")


@dataclass(frozen=True)
class Field:
    name: str
    hidden: bool = False


@dataclass(frozen=True)
class CardTemplate:
    name: str
    ord: int
    front: str
    back: str


@dataclass(frozen=True)
class NoteType:
    name: str
    fields: tuple[Field, ...]
    templates: tuple[CardTemplate, ...]
    css: str
    language: Language | None = None  # None for Capture
    category: Category | None = None


@dataclass(frozen=True)
class Preset:
    """The `<Prefix>` deck options preset: it owns only the sibling-burying flags (FR-8)."""

    name: str
    bury_flags: Mapping[str, bool]
    decks: tuple[str, ...]


@dataclass(frozen=True)
class Manifest:
    prefix: str
    schema_version: int
    note_types: tuple[NoteType, ...]
    decks: tuple[str, ...]  # parents before children
    preset: Preset

    def card_deck(self, note_type_name: str, ord: int) -> str:
        """The deck a card of this note type and ord belongs in (FR-20)."""
        note_type = next((nt for nt in self.note_types if nt.name == note_type_name), None)
        if note_type is None:
            raise KeyError(note_type_name)
        if ord not in {t.ord for t in note_type.templates}:
            raise ValueError(f"{note_type_name} has no card ord {ord}")
        if note_type.language is None or note_type.category is None:
            return f"{self.prefix}::Captures"
        branch = _branch(note_type.language, note_type.category)
        if ord in _STUDY_ORDS:
            return f"{self.prefix}::Study::{branch}::{EXERCISE_BY_ORD[ord].title()}"
        return f"{self.prefix}::Pronunciation::{branch}"


def _branch(language: Language, category: Category) -> str:
    return f"{_LANGUAGE_NAMES[language]}::{_CATEGORY_NAMES[category][1]}"


def _fields(category: Category | None) -> tuple[Field, ...]:
    return tuple(Field(name, name in _HIDDEN) for name in _FIELDS[category])


def _item_templates(category: Category) -> tuple[CardTemplate, ...]:
    return tuple(
        CardTemplate(
            name=exercise.title(),
            ord=ord,
            front=_template_text(f"{category}-{exercise}-front.html"),
            back=_template_text(f"{category}-{exercise}-back.html"),
        )
        for ord, exercise in EXERCISE_BY_ORD.items()
    )


def _decks(prefix: str) -> tuple[str, ...]:
    study, pronunciation = f"{prefix}::Study", f"{prefix}::Pronunciation"
    decks = [prefix, f"{prefix}::Captures", study, pronunciation]
    for language in Language:
        lang = _LANGUAGE_NAMES[language]
        decks += [f"{study}::{lang}", f"{pronunciation}::{lang}"]
        for category in Category:
            branch = _branch(language, category)
            decks += [f"{study}::{branch}", f"{pronunciation}::{branch}"]
            decks += [f"{study}::{branch}::{EXERCISE_BY_ORD[o].title()}" for o in _STUDY_ORDS]
    return tuple(decks)


def build_manifest(prefix: str) -> Manifest:
    """The manifest for one Prefix; every name derives from it (AD-3, NFR-1)."""
    if not re.fullmatch(PREFIX_PATTERN, prefix):
        raise ValueError(f"Prefix {prefix!r} does not match {PREFIX_PATTERN}")
    css = _template_text("cards.css")
    capture = NoteType(
        name=f"{prefix} Capture",
        fields=_fields(None),
        templates=(
            CardTemplate(
                name="Capture",
                ord=0,
                front=_template_text("capture-front.html"),
                back=_template_text("capture-back.html"),
            ),
        ),
        css=css,
    )
    items = tuple(
        NoteType(
            name=f"{prefix} {_LANGUAGE_NAMES[language]} {_CATEGORY_NAMES[category][0]}",
            fields=_fields(category),
            templates=_item_templates(category),
            css=css,
            language=language,
            category=category,
        )
        for language in Language
        for category in Category
    )
    decks = _decks(prefix)
    branches = (f"{prefix}::Study", f"{prefix}::Pronunciation")
    preset_decks = tuple(
        d for d in decks if any(d == root or d.startswith(f"{root}::") for root in branches)
    )
    return Manifest(
        prefix=prefix,
        schema_version=SCHEMA_VERSION,
        note_types=(capture, *items),
        decks=decks,
        preset=Preset(name=prefix, bury_flags=BURY_FLAGS, decks=preset_decks),
    )
