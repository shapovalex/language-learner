"""Story 2.4: the managed manifest, the one source of Anki names and structure (AD-3, A3).

`build_manifest(prefix)` declares, from `ANKI_PREFIX`, the five note types and their fields, the
card templates and CSS read from `adapters/anki/templates/`, the 28-deck tree, the card ord to
Exercise to deck mapping, the `<Prefix>` preset with its three bury flags, and the current
SchemaVersion. Setup diffs Anki against it (entry 6) and every feature reads names from it.

Fields put Target (or Text) first, decided with the user on 2026-10-21: Anki sorts and marks
duplicates by the first field. The ids and SchemaVersion are hidden: no template renders them.

Skipped until the manifest exists. Un-skip a test, watch it fail, then implement. Hoist the
imports once it's green.
"""

import re
from pathlib import Path

import pytest

import language_lab.adapters.anki
from tests.support.anki_connect import anki_fixture

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 2.4: un-skip with adapters/anki/manifest.py and templates/"
)

RELEASE = "LanguageLab"
DEV = "LanguageLabDev"
TEMPLATES_DIR = Path(language_lab.adapters.anki.__file__).parent / "templates"

LANGUAGES = ("English", "French")
# (note type word, deck word) per Category: the note type is singular, the deck plural (A3)
CATEGORIES = (("Vocabulary", "Vocabulary"), ("Sentence", "Sentences"))
STUDY_EXERCISES = ("Understand", "Produce", "Write")  # ord 0-2; ord 3 Pronounce has its own branch
EXERCISES = (*STUDY_EXERCISES, "Pronounce")

VOCABULARY_FIELDS = (
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
)
SENTENCE_FIELDS = (
    "Target",
    "Russian",
    "RussianAlternatives",
    "Hint",
    "Note",
    "Audio",
    "ItemId",
    "SchemaVersion",
)
CAPTURE_FIELDS = ("Text", "CreatedAt", "CaptureId", "SchemaVersion")

# What Anki substitutes itself; not field names
SPECIAL_REFS = frozenset({"FrontSide", "Tags", "Type", "Deck", "Subdeck", "Card", "CardFlag"})
_REF = re.compile(r"\{\{([^{}]+)\}\}")


def _note_type_names(prefix: str) -> tuple[str, ...]:
    items = tuple(f"{prefix} {lang} {word}" for lang in LANGUAGES for word, _ in CATEGORIES)
    return (f"{prefix} Capture", *items)


def _expected_decks(prefix: str) -> list[str]:
    decks = [prefix, f"{prefix}::Captures", f"{prefix}::Study", f"{prefix}::Pronunciation"]
    for lang in LANGUAGES:
        decks += [f"{prefix}::Study::{lang}", f"{prefix}::Pronunciation::{lang}"]
        for _, deck_word in CATEGORIES:
            study = f"{prefix}::Study::{lang}::{deck_word}"
            decks += [study, f"{prefix}::Pronunciation::{lang}::{deck_word}"]
            decks += [f"{study}::{exercise}" for exercise in STUDY_EXERCISES]
    return sorted(decks)


def _field_refs(template: str) -> set[str]:
    """The fields a template reads: `{{X}}`, `{{#X}}`, `{{/X}}`, `{{^X}}`, `{{type:X}}`."""
    refs = {ref.strip().lstrip("#/^").split(":")[-1].strip() for ref in _REF.findall(template)}
    return refs - SPECIAL_REFS


def _all_names(manifest) -> set[str]:
    return (
        {note_type.name for note_type in manifest.note_types}
        | set(manifest.decks)
        | {manifest.preset.name}
        | set(manifest.preset.decks)
    )


def _in_deck_scope(deck: str, root: str) -> bool:
    """What `deck:"<root>"` matches in Anki: the deck itself and its children (AD-4)."""
    return deck == root or deck.startswith(f"{root}::")


@RED_PHASE
@pytest.mark.p0
def test_every_manifest_name_derives_from_the_prefix_and_prefixes_never_overlap() -> None:
    """AC-1: each name is the Prefix or under it; LanguageLab and LanguageLabDev share none."""
    from language_lab.adapters.anki.manifest import build_manifest

    names = _all_names(build_manifest("Zq"))
    release = build_manifest(RELEASE)
    dev = build_manifest(DEV)

    assert [n for n in sorted(names) if not re.match(r"Zq($| |::)", n)] == []
    assert names
    assert not any("LanguageLab" in name for name in names)
    assert _all_names(release).isdisjoint(_all_names(dev))
    assert not any(_in_deck_scope(deck, RELEASE) for deck in dev.decks)
    assert not any(_in_deck_scope(deck, DEV) for deck in release.decks)
    assert release.prefix == RELEASE
    assert dev.prefix == DEV


@RED_PHASE
@pytest.mark.p1
def test_manifest_declares_five_note_types_with_their_fields() -> None:
    """AC-2: Capture and four Item note types with the A3/AD-10 fields, ids and version hidden."""
    from language_lab.adapters.anki.manifest import build_manifest

    manifest = build_manifest(RELEASE)
    fields = {nt.name: tuple(f.name for f in nt.fields) for nt in manifest.note_types}
    hidden = {nt.name: {f.name for f in nt.fields if f.hidden} for nt in manifest.note_types}

    assert tuple(nt.name for nt in manifest.note_types) == _note_type_names(RELEASE)
    assert fields == {
        "LanguageLab Capture": CAPTURE_FIELDS,
        "LanguageLab English Vocabulary": VOCABULARY_FIELDS,
        "LanguageLab English Sentence": SENTENCE_FIELDS,
        "LanguageLab French Vocabulary": VOCABULARY_FIELDS,
        "LanguageLab French Sentence": SENTENCE_FIELDS,
    }
    assert hidden == {
        "LanguageLab Capture": {"CaptureId", "SchemaVersion"},
        "LanguageLab English Vocabulary": {"ItemId", "SchemaVersion"},
        "LanguageLab English Sentence": {"ItemId", "SchemaVersion"},
        "LanguageLab French Vocabulary": {"ItemId", "SchemaVersion"},
        "LanguageLab French Sentence": {"ItemId", "SchemaVersion"},
    }


@RED_PHASE
@pytest.mark.p1
def test_item_note_types_have_four_card_templates_and_capture_one() -> None:
    """AC-3: Understand, Produce, Write, Pronounce at ord 0-3 per Item type; one Capture card."""
    from language_lab.adapters.anki.manifest import build_manifest

    manifest = build_manifest(RELEASE)
    counts = {nt.name: len(nt.templates) for nt in manifest.note_types}
    cards = {nt.name: tuple((t.ord, t.name) for t in nt.templates) for nt in manifest.note_types}
    capture, *items = _note_type_names(RELEASE)

    assert counts == {capture: 1} | {name: 4 for name in items}
    assert cards[capture] == ((0, "Capture"),)
    assert all(cards[name] == tuple(enumerate(EXERCISES)) for name in items)


@RED_PHASE
@pytest.mark.p0
def test_card_ord_maps_to_its_exercise_and_deck() -> None:
    """AC-4: ord 0-2 go to Study::<Language>::<Category>::<Exercise>, ord 3 to Pronunciation."""
    from language_lab.adapters.anki.manifest import EXERCISE_BY_ORD, build_manifest
    from language_lab.domain.catalog import Exercise

    manifest = build_manifest(RELEASE)
    expected = {("LanguageLab Capture", 0): "LanguageLab::Captures"}
    for lang in LANGUAGES:
        for word, deck_word in CATEGORIES:
            note_type = f"LanguageLab {lang} {word}"
            for ord_, exercise in enumerate(STUDY_EXERCISES):
                expected[note_type, ord_] = f"LanguageLab::Study::{lang}::{deck_word}::{exercise}"
            expected[note_type, 3] = f"LanguageLab::Pronunciation::{lang}::{deck_word}"
    actual = {
        (nt.name, t.ord): manifest.card_deck(nt.name, t.ord)
        for nt in manifest.note_types
        for t in nt.templates
    }

    assert actual == expected
    assert set(actual.values()) <= set(manifest.decks)
    assert EXERCISE_BY_ORD == {
        0: Exercise.UNDERSTAND,
        1: Exercise.PRODUCE,
        2: Exercise.WRITE,
        3: Exercise.PRONOUNCE,
    }


@RED_PHASE
@pytest.mark.p1
def test_manifest_declares_the_28_deck_tree() -> None:
    """AC-5: the root, Captures, the Study tree to each Exercise, and the Pronunciation tree."""
    from language_lab.adapters.anki.manifest import build_manifest

    decks = build_manifest(RELEASE).decks

    assert sorted(decks) == _expected_decks(RELEASE)
    assert len(decks) == len(set(decks)) == 28
    # parents before children, so creating in order never relies on Anki making a parent
    assert all(decks.index(d.rsplit("::", 1)[0]) < decks.index(d) for d in decks if "::" in d)


@RED_PHASE
@pytest.mark.p0
def test_preset_turns_off_the_three_bury_flags_on_every_study_and_pronunciation_deck() -> None:
    """AC-6: the `<Prefix>` preset owns only the three bury flags, all off (FR-8, AC7)."""
    from language_lab.adapters.anki.manifest import build_manifest

    manifest = build_manifest(RELEASE)
    recorded = anki_fixture("getDeckConfig")["response"]["result"]  # spike 2.2, Q5

    assert manifest.preset.bury_flags == {
        "new.bury": False,
        "rev.bury": False,
        "buryInterdayLearning": False,
    }
    assert manifest.preset.name == RELEASE
    for path in manifest.preset.bury_flags:  # each key names a bool in a real deck config
        value = recorded
        for key in path.split("."):
            value = value[key]
        assert isinstance(value, bool), path
    branches = ("LanguageLab::Study", "LanguageLab::Pronunciation")
    assert sorted(manifest.preset.decks) == sorted(
        d for d in manifest.decks if any(_in_deck_scope(d, root) for root in branches)
    )
    assert len(manifest.preset.decks) == 26


@RED_PHASE
@pytest.mark.p2
def test_manifest_declares_the_current_schema_version() -> None:
    """AC-7: SchemaVersion 1, the same for every Prefix (AD-3: bumps only with a migration)."""
    from language_lab.adapters.anki.manifest import SCHEMA_VERSION, build_manifest

    assert build_manifest(RELEASE).schema_version == 1
    assert SCHEMA_VERSION == 1
    assert build_manifest(DEV).schema_version == SCHEMA_VERSION


@RED_PHASE
@pytest.mark.p1
def test_card_templates_and_css_come_from_template_files_and_render_only_shown_fields() -> None:
    """AC-8: fronts, backs and CSS are files under templates/ and read only declared fields."""
    from language_lab.adapters.anki.manifest import build_manifest

    manifest = build_manifest(RELEASE)
    file_texts = {p.read_text(encoding="utf-8") for p in TEMPLATES_DIR.rglob("*") if p.is_file()}
    texts = [(nt.name, "css", nt.css) for nt in manifest.note_types] + [
        (nt.name, f"{t.name} {side}", text)
        for nt in manifest.note_types
        for t in nt.templates
        for side, text in (("front", t.front), ("back", t.back))
    ]
    missing = [(name, label) for name, label, text in texts if text not in file_texts]

    assert missing == []
    capture, *items = manifest.note_types
    for nt in manifest.note_types:
        declared = {f.name for f in nt.fields}
        hidden = {f.name for f in nt.fields if f.hidden}
        shown = declared - hidden
        assert nt.css.strip(), nt.name
        for t in nt.templates:
            front, back = _field_refs(t.front), _field_refs(t.back)
            assert front | back <= declared, (nt.name, t.name)  # no unknown field
            assert not (front | back) & hidden, (nt.name, t.name)
            assert front & shown, (nt.name, t.name)  # Anki makes no card from an empty front
            if nt is not capture:  # every back shows the whole Item (FR-21), FrontSide included
                on_back = back | (front if "{{FrontSide}}" in t.back else set())
                assert on_back == shown, (nt.name, t.name)
                assert "RussianAlternatives" not in front, (nt.name, t.name)  # AD-10
    assert "Text" in _field_refs(capture.templates[0].front)
    for nt in items:
        understand, produce, write, pronounce = nt.templates
        assert "Target" in _field_refs(understand.front)
        assert "Russian" not in _field_refs(understand.front)
        assert "Russian" in _field_refs(produce.front)
        assert not {"Target", "Audio"} & _field_refs(produce.front)  # FR-21
        assert "{{type:Target}}" in write.front
        assert "{{type:Target}}" in write.back  # Anki shows the typed comparison here
        assert "Russian" in _field_refs(write.front)
        assert "Audio" not in _field_refs(write.front)
        assert "Target" in _field_refs(pronounce.front)
