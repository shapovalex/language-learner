"""Story 2.4: the managed manifest, the one source of Anki names and structure (AD-3, A3).

`build_manifest(prefix)` declares, from `ANKI_PREFIX`, the six note types and their fields, the
card templates and CSS read from `adapters/anki/templates/`, the 29-deck tree, the card ord to
Exercise to deck mapping, the `<Prefix>` preset with its three bury flags, and the current
SchemaVersion. Setup diffs Anki against it (entry 6) and every feature reads names from it.

The French reading rules deck adds the sixth note type, `<Prefix> French Reading Rule` (one
Read card, its `RuleId` hidden), and the `<Prefix>::Study::French::Reading Rules` deck, on the
preset like every Study deck.

Fields put Target (or Text) first, decided with the user on 2026-10-21: Anki sorts and marks
duplicates by the first field. The ids and SchemaVersion are hidden: no template renders them.
"""

import re
from pathlib import Path

import pytest

import language_lab.adapters.anki
from language_lab.adapters.anki.manifest import (
    EXERCISE_BY_ORD,
    SCHEMA_VERSION,
    build_manifest,
)
from language_lab.domain.catalog import Category, Exercise, Language
from tests.support.anki_connect import anki_fixture

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
READING_RULE_FIELDS = (
    "Combination",
    "Transcription",
    "Note",
    "Example1",
    "Example1Audio",
    "Example2",
    "Example2Audio",
    "Example3",
    "Example3Audio",
    "RuleId",
    "SchemaVersion",
)

# What Anki substitutes itself; not field names
SPECIAL_REFS = frozenset({"FrontSide", "Tags", "Type", "Deck", "Subdeck", "Card", "CardFlag"})
_REF = re.compile(r"\{\{([^{}]+)\}\}")


def _note_type_names(prefix: str) -> tuple[str, ...]:
    items = tuple(f"{prefix} {lang} {word}" for lang in LANGUAGES for word, _ in CATEGORIES)
    return (f"{prefix} Capture", *items, f"{prefix} French Reading Rule")


def _expected_decks(prefix: str) -> list[str]:
    decks = [prefix, f"{prefix}::Captures", f"{prefix}::Study", f"{prefix}::Pronunciation"]
    for lang in LANGUAGES:
        decks += [f"{prefix}::Study::{lang}", f"{prefix}::Pronunciation::{lang}"]
        for _, deck_word in CATEGORIES:
            study = f"{prefix}::Study::{lang}::{deck_word}"
            decks += [study, f"{prefix}::Pronunciation::{lang}::{deck_word}"]
            decks += [f"{study}::{exercise}" for exercise in STUDY_EXERCISES]
    decks.append(f"{prefix}::Study::French::Reading Rules")
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


@pytest.mark.p0
def test_every_manifest_name_derives_from_the_prefix_and_prefixes_never_overlap() -> None:
    """AC-1: each name is the Prefix or under it; LanguageLab and LanguageLabDev share none."""
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


@pytest.mark.p1
def test_manifest_declares_six_note_types_with_their_fields() -> None:
    """AC-2: Capture, four Item note types with the A3/AD-10 fields and the French Reading
    Rule, ids and version hidden.
    """
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
        "LanguageLab French Reading Rule": READING_RULE_FIELDS,
    }
    assert hidden == {
        "LanguageLab Capture": {"CaptureId", "SchemaVersion"},
        "LanguageLab English Vocabulary": {"ItemId", "SchemaVersion"},
        "LanguageLab English Sentence": {"ItemId", "SchemaVersion"},
        "LanguageLab French Vocabulary": {"ItemId", "SchemaVersion"},
        "LanguageLab French Sentence": {"ItemId", "SchemaVersion"},
        "LanguageLab French Reading Rule": {"RuleId", "SchemaVersion"},
    }


@pytest.mark.p1
def test_item_note_types_have_four_card_templates_and_capture_one() -> None:
    """AC-3: Understand, Produce, Write, Pronounce at ord 0-3 per Item type; one Capture card;
    one Read card per reading rule.
    """
    manifest = build_manifest(RELEASE)
    counts = {nt.name: len(nt.templates) for nt in manifest.note_types}
    cards = {nt.name: tuple((t.ord, t.name) for t in nt.templates) for nt in manifest.note_types}
    capture, *items, reading_rule = _note_type_names(RELEASE)

    assert counts == {capture: 1, reading_rule: 1} | {name: 4 for name in items}
    assert cards[capture] == ((0, "Capture"),)
    assert cards[reading_rule] == ((0, "Read"),)
    assert all(cards[name] == tuple(enumerate(EXERCISES)) for name in items)


@pytest.mark.p0
def test_card_ord_maps_to_its_exercise_and_deck() -> None:
    """AC-4: ord 0-2 go to Study::<Language>::<Category>::<Exercise>, ord 3 to Pronunciation."""
    manifest = build_manifest(RELEASE)
    expected = {
        ("LanguageLab Capture", 0): "LanguageLab::Captures",
        ("LanguageLab French Reading Rule", 0): "LanguageLab::Study::French::Reading Rules",
    }
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


@pytest.mark.p1
def test_manifest_declares_the_29_deck_tree() -> None:
    """AC-5: the root, Captures, the Study tree to each Exercise and the French Reading Rules,
    and the Pronunciation tree.
    """
    decks = build_manifest(RELEASE).decks

    assert sorted(decks) == _expected_decks(RELEASE)
    assert len(decks) == len(set(decks)) == 29
    write = decks.index("LanguageLab::Study::French::Sentences::Write")
    assert decks[write + 1] == "LanguageLab::Study::French::Reading Rules"
    # parents before children, so creating in order never relies on Anki making a parent
    assert all(decks.index(d.rsplit("::", 1)[0]) < decks.index(d) for d in decks if "::" in d)


@pytest.mark.p0
def test_preset_turns_off_the_three_bury_flags_on_every_study_and_pronunciation_deck() -> None:
    """AC-6: the `<Prefix>` preset owns only the three bury flags, all off (FR-8, AC7)."""
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
    assert len(manifest.preset.decks) == 27
    assert "LanguageLab::Study::French::Reading Rules" in manifest.preset.decks


@pytest.mark.p2
def test_manifest_declares_the_current_schema_version() -> None:
    """AC-7: SchemaVersion 1, the same for every Prefix (AD-3: bumps only with a migration)."""
    assert build_manifest(RELEASE).schema_version == 1
    assert SCHEMA_VERSION == 1
    assert build_manifest(DEV).schema_version == SCHEMA_VERSION


@pytest.mark.p1
def test_card_templates_and_css_come_from_template_files_and_render_only_shown_fields() -> None:
    """AC-8: fronts, backs and CSS are files under templates/ and read only declared fields."""
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
    capture, *items, _reading_rule = manifest.note_types
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
            if nt is not capture:  # every back shows the whole note (FR-21), FrontSide included
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


STUDIO_HEXES = (
    "#FFF8F1",
    "#FFFFFF",
    "#221E2E",
    "#5C5669",
    "#5A45C8",
    "#ECE8FB",
    "#F0EAE2",
    "#E2DACF",
)


@pytest.mark.p1
def test_study_templates_place_russian_and_audio_per_fr21_and_css_uses_the_studio_tokens() -> None:
    """Story 4.4 (FR-21, AD-10): fronts, backs and audio placement; no script or IPA; Studio CSS."""
    manifest = build_manifest(RELEASE)
    capture, *items, reading_rule = manifest.note_types

    for nt in items:
        understand, produce, write, _pronounce = nt.templates
        assert "Audio" in _field_refs(understand.front), nt.name
        for t in (produce, write):
            front = _field_refs(t.front)
            assert "Russian" in front, (nt.name, t.name)
            assert not {"RussianAlternatives", "Audio"} & front, (nt.name, t.name)
        for t in (understand, produce, write):
            on_back = t.back + (t.front if "{{FrontSide}}" in t.back else "")
            assert on_back.count("{{Audio}}") == 1, (nt.name, t.name)
            assert "{{#Audio}}" in on_back, (nt.name, t.name)  # an empty Audio renders no player
            assert "Russian" in _field_refs(on_back), (nt.name, t.name)
    for nt in manifest.note_types:
        for t in nt.templates:
            for text in (t.front, t.back):
                assert "<script" not in text.lower(), (nt.name, t.name)
                assert "ipa" not in text.lower(), (nt.name, t.name)
    css = capture.css
    assert all(nt.css == css for nt in (*items, reading_rule))
    assert [h for h in STUDIO_HEXES if h.lower() not in css.lower()] == []
    assert ".nightMode" in css
    assert "Figtree" in css
    assert "@font-face" not in css and "url(" not in css  # the font is not embedded
    for old in (".prompt", ".hint", ".meta", ".note", ".example"):
        assert old in css, old


@pytest.mark.p2
@pytest.mark.parametrize("prefix", ["Bad Prefix", "Lang::Lab", 'Lang"Lab', "", "1Lab"])
def test_build_manifest_rejects_a_prefix_outside_the_pattern(prefix: str) -> None:
    """AC-1: a Prefix that fails PREFIX_PATTERN never becomes Anki names, even past settings."""
    with pytest.raises(ValueError, match="Prefix"):
        build_manifest(prefix)


@pytest.mark.p2
def test_card_deck_rejects_an_unknown_note_type_or_ord() -> None:
    """AC-4: no deck is guessed for a note type or card ord the manifest doesn't declare."""
    manifest = build_manifest(RELEASE)

    with pytest.raises(KeyError):
        manifest.card_deck("Basic", 0)
    with pytest.raises(KeyError):
        manifest.card_deck("LanguageLabDev French Sentence", 0)
    with pytest.raises(ValueError):
        manifest.card_deck("LanguageLab French Sentence", 4)
    with pytest.raises(ValueError):
        manifest.card_deck("LanguageLab Capture", 1)
    with pytest.raises(ValueError):
        manifest.card_deck("LanguageLab French Reading Rule", 1)


@pytest.mark.p1
def test_reading_rule_card_shows_the_combination_then_transcription_note_and_three_words() -> None:
    """Reading rules AC-2: the front is the combination alone; the back adds the transcription,
    any note, and each example word beside its own audio. Existing classes only.
    """
    manifest = build_manifest(RELEASE)
    note_type = next(nt for nt in manifest.note_types if nt.name == manifest.reading_rule_note_type)
    (read,) = note_type.templates

    assert note_type.name == "LanguageLab French Reading Rule"
    assert _field_refs(read.front) == {"Combination"}
    assert "{{FrontSide}}" in read.back and '<hr id="answer">' in read.back
    shown = {f.name for f in note_type.fields if not f.hidden}
    assert _field_refs(read.back) == shown - {"Combination"}  # FrontSide shows it
    assert '<div class="russian transcription">{{Transcription}}</div>' in read.back
    assert "{{#Note}}" in read.back
    for n in (1, 2, 3):
        row = f'{{{{#Example{n}}}}}<div class="example">{{{{Example{n}}}}} {{{{Example{n}Audio}}}}'
        assert row in read.back, n

    def classes(html: str) -> set[str]:
        return {c for cls in re.findall(r'class="([^"]+)"', html) for c in cls.split()}

    existing = set(re.findall(r"\.([a-z][a-z-]*)", note_type.css)) | {
        c
        for nt in manifest.note_types
        if nt is not note_type
        for t in nt.templates
        for c in classes(t.front + t.back)
    }
    assert classes(read.front + read.back) - existing == {"transcription"}  # a marker only


@pytest.mark.p1
def test_reading_rule_note_type_is_neither_an_item_nor_the_capture_type() -> None:
    """The reading rules have a Language and no Category: `item_note_type` never names them, and
    their one card goes to the Reading Rules deck, not Captures. The manifest carries the 46
    seeded rules in data order.
    """
    manifest = build_manifest(DEV)
    note_type = next(nt for nt in manifest.note_types if nt.name == manifest.reading_rule_note_type)

    assert (note_type.language, note_type.category) == (Language.FR, None)
    assert note_type.deck == "LanguageLabDev::Study::French::Reading Rules"
    assert manifest.card_deck(note_type.name, 0) == note_type.deck
    for language in Language:
        for category in Category:
            assert manifest.item_note_type(language, category) != note_type.name
    assert len(manifest.reading_rules) == 46
    assert manifest.reading_rules[0].combination == "ou"
