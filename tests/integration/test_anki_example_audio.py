"""Example card and example audio through the real guarded Anki adapter (plan
example-audio-card-and-pronunciation-mix).

SchemaVersion 2 gives both Vocabulary note types an `ExampleAudio` field and a fifth card
template, Example (ord 4), whose front renders only once `ExampleAudio` and `ExampleRussian`
hold something. So the Example card exists only once Save (or the backfill) writes example
audio, and that same write moves it to `<Prefix>::Study::<Language>::Vocabulary::Example`:
Anki makes it in the deck of the note's first card. Example media uses the AD-7 name and is
cleaned up like `Audio`. Sentence note types are untouched.

Anki is the in-memory collection in tests/support/anki_state.py, which makes a card only for a
template whose front renders (tests/support/anki_state.py, Card generation).
"""

import dataclasses
import uuid
from typing import Any

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.guard import PrefixGuard
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import Manifest
from language_lab.adapters.anki.migrations import AddField, Migration, build_migrations
from language_lab.adapters.anki.setup_gate import SetupGate
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.catalog import Language
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.items import AudioIntent
from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind, SetupState, plan_hash
from tests.support.aio import run, settle
from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay
from tests.support.anki_state import (
    Collection,
    apply_manifest,
    collection_replies,
    item_note,
    managed_collection,
    managed_note,
    review_card,
    sent_writes,
    stock_collection,
)
from tests.support.audio import MP3, SECOND_MP3, managed_name
from tests.support.captures import MANIFEST, PREFIX, wired
from tests.support.items import SENTENCE, VOCABULARY, content

EN_VOCABULARY = f"{PREFIX} English Vocabulary"
FR_VOCABULARY = f"{PREFIX} French Vocabulary"
EN_SENTENCE = f"{PREFIX} English Sentence"
EXAMPLE_DECK = {
    "en": f"{PREFIX}::Study::English::Vocabulary::Example",
    "fr": f"{PREFIX}::Study::French::Vocabulary::Example",
}
EXAMPLE_ORD = 4


def cards_of(collection: Collection, note_id: int) -> dict[int, str]:
    """`{ord: deck}` of one note's cards."""
    return {c.ord: c.deck for c in collection.cards.values() if c.note == note_id}


def note_of(collection: Collection, item_id: str) -> tuple[int, Any]:
    (found,) = [(i, n) for i, n in collection.notes.items() if n.fields.get("ItemId") == item_id]
    return found


def example_card(collection: Collection, note_id: int) -> Any:
    (card,) = [c for c in collection.cards.values() if c.note == note_id and c.ord == EXAMPLE_ORD]
    return card


def unlock(store: Any, collection: Collection, item_id: str) -> None:
    """Answer the new Item's Understand card and run the unlock, as the next Sync does."""
    note_id, _ = note_of(collection, item_id)
    review_card(collection, note_id, 0)
    assert settle(store.unlock_answered_items()) == 1


def save(
    store: Any,
    item_id: str,
    wire: dict[str, Any],
    *,
    language: str = "en",
    example: bytes | None = None,
    audio: bytes | None = None,
) -> Any:
    intent = AudioIntent.REPLACE if audio is not None else AudioIntent.KEEP
    return settle(
        store.save_item(
            item_id,
            Language(language),
            content(wire),
            intent,
            audio_bytes=audio,
            example_audio_bytes=example,
        )
    )


# ---- Save ---------------------------------------------------------------------------------


@pytest.mark.p0
@pytest.mark.parametrize("language", ["en", "fr"])
def test_a_new_vocabulary_item_with_example_audio_gets_its_example_card(language: str) -> None:
    """Save with example audio: ExampleAudio holds the AD-7 clip, and the note's Example card
    is in its Study deck beside the four usual cards.
    """
    collection = managed_collection(MANIFEST, reading_rules=False)
    store, _ = wired(collection)
    item_id = str(uuid.uuid4())

    assert save(store, item_id, VOCABULARY, language=language, example=MP3) is None

    note_id, note = note_of(collection, item_id)
    name = managed_name(item_id, MP3)
    assert note.fields["ExampleAudio"] == f"[sound:{name}]"
    assert name in collection.media
    decks = cards_of(collection, note_id)
    assert sorted(decks) == [0, 1, 2, 3, 4]
    assert decks[EXAMPLE_ORD] == EXAMPLE_DECK[language]


@pytest.mark.p0
def test_a_vocabulary_item_saved_without_example_audio_has_no_example_card() -> None:
    """No example audio: ExampleAudio stays empty and Anki makes no Example card."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    store, replay = wired(collection)
    item_id = str(uuid.uuid4())

    save(store, item_id, VOCABULARY)

    note_id, note = note_of(collection, item_id)
    assert note.fields["ExampleAudio"] == ""
    assert sorted(cards_of(collection, note_id)) == [0, 1, 2, 3]
    assert "storeMediaFile" not in sent_writes(replay.sent)


@pytest.mark.p0
def test_example_audio_on_an_existing_item_moves_the_new_example_card_to_its_deck() -> None:
    """Update: Anki makes the Example card in the deck of the note's first card; Save moves it."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    item_id = str(uuid.uuid4())
    fields = {"Target": "jump", "Example": "Jump!", "ExampleRussian": "Прыгай!"}
    note_id = item_note(collection, MANIFEST, EN_VOCABULARY, item_id, fields)
    assert sorted(cards_of(collection, note_id)) == [0, 1, 2, 3]
    store, replay = wired(collection)

    save(store, item_id, VOCABULARY, example=MP3)

    assert cards_of(collection, note_id)[EXAMPLE_ORD] == EXAMPLE_DECK["en"]
    writes = sent_writes(replay.sent)
    assert writes.index("updateNoteFields") < writes.index("changeDeck")


@pytest.mark.p0
def test_an_edited_example_replaces_its_audio_and_deletes_the_old_clip() -> None:
    """Example edited: the new clip is stored and named, the old one deleted, one Example card."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    store, replay = wired(collection)
    item_id = str(uuid.uuid4())
    save(store, item_id, VOCABULARY, example=MP3)
    old = managed_name(item_id, MP3)

    edited = {**VOCABULARY, "example": "Don't jump yet."}
    save(store, item_id, edited, example=SECOND_MP3)

    note_id, note = note_of(collection, item_id)
    new = managed_name(item_id, SECOND_MP3)
    assert note.fields["ExampleAudio"] == f"[sound:{new}]"
    assert new in collection.media
    assert old not in collection.media
    assert [o for o in cards_of(collection, note_id) if o == EXAMPLE_ORD] == [EXAMPLE_ORD]


@pytest.mark.p1
def test_a_clip_shared_by_audio_and_example_audio_is_kept() -> None:
    """Reference and example audio of the same bytes share one AD-7 name: replacing the
    Reference audio never deletes the clip ExampleAudio still names.
    """
    collection = managed_collection(MANIFEST, reading_rules=False)
    store, _ = wired(collection)
    item_id = str(uuid.uuid4())
    save(store, item_id, VOCABULARY, audio=MP3, example=MP3)
    shared = managed_name(item_id, MP3)

    save(store, item_id, VOCABULARY, audio=SECOND_MP3)

    _, note = note_of(collection, item_id)
    assert note.fields["ExampleAudio"] == f"[sound:{shared}]"
    assert shared in collection.media


@pytest.mark.p1
def test_clearing_the_example_empties_example_audio_and_deletes_its_clip() -> None:
    """A Vocabulary Save with a blank Example empties ExampleAudio and cleans its clip."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    store, _ = wired(collection)
    item_id = str(uuid.uuid4())
    save(store, item_id, VOCABULARY, example=MP3)
    unlock(store, collection, item_id)

    save(store, item_id, {**VOCABULARY, "example": "", "exampleRussian": ""})

    note_id, note = note_of(collection, item_id)
    assert note.fields["ExampleAudio"] == ""
    assert managed_name(item_id, MP3) not in collection.media
    # Its Example card stays (never deleted) but is suspended: its front is empty now
    assert example_card(collection, note_id).suspended is True

    # Example audio written again: the same card is unsuspended, in its deck
    save(store, item_id, VOCABULARY, example=SECOND_MP3)

    card = example_card(collection, note_id)
    assert card.suspended is False
    assert card.deck == EXAMPLE_DECK["en"]
    assert [c.ord for c in collection.cards.values() if c.note == note_id].count(EXAMPLE_ORD) == 1


@pytest.mark.p0
@pytest.mark.parametrize(
    "unchanged",
    [False, True],
    ids=["edited-without-new-audio", "unchanged-without-new-audio"],
)
def test_an_edited_example_without_new_audio_drops_the_stale_clip(unchanged: bool) -> None:
    """The Example changed and no new bytes came (synthesis failed, or no Voice): the old clip
    speaks text no longer stored, so ExampleAudio is emptied, the clip deleted and the Example
    card suspended; the next Save or backfill can make it again. An unchanged Example keeps it.
    """
    collection = managed_collection(MANIFEST, reading_rules=False)
    store, _ = wired(collection)
    item_id = str(uuid.uuid4())
    save(store, item_id, VOCABULARY, example=MP3)
    unlock(store, collection, item_id)
    old = managed_name(item_id, MP3)

    wire = VOCABULARY if unchanged else {**VOCABULARY, "example": "Don't jump yet."}
    save(store, item_id, wire)

    note_id, note = note_of(collection, item_id)
    if unchanged:
        assert note.fields["ExampleAudio"] == f"[sound:{old}]"
        assert old in collection.media
        assert example_card(collection, note_id).suspended is False
    else:
        assert note.fields["ExampleAudio"] == ""
        assert old not in collection.media
        assert example_card(collection, note_id).suspended is True


@pytest.mark.p0
def test_a_sentence_item_takes_no_example_audio_and_keeps_its_shape() -> None:
    """AC: a Sentence Save writes no ExampleAudio; example bytes for one are refused unsent."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    store, replay = wired(collection)
    item_id = str(uuid.uuid4())

    save(store, item_id, SENTENCE)
    refused = save(store, str(uuid.uuid4()), SENTENCE, example=MP3)

    note_id, note = note_of(collection, item_id)
    assert "ExampleAudio" not in note.fields
    assert sorted(cards_of(collection, note_id)) == [0, 1, 2, 3]
    assert isinstance(refused, AppError) and refused.code is ErrorCode.VALIDATION_FAILED
    assert "storeMediaFile" not in sent_writes(replay.sent)


@pytest.mark.p1
def test_deleting_an_item_cleans_its_example_clip_too() -> None:
    collection = managed_collection(MANIFEST, reading_rules=False)
    store, _ = wired(collection)
    item_id = str(uuid.uuid4())
    save(store, item_id, VOCABULARY, audio=SECOND_MP3, example=MP3)

    run(store.delete_item(Language.EN, item_id))

    assert collection.media == set()


# ---- the backfill's write -----------------------------------------------------------------


def example_item(collection: Collection, **fields: str) -> tuple[str, int]:
    item_id = str(uuid.uuid4())
    stored = {"Target": "jump", "Example": "Jump!", "ExampleRussian": "Прыгай!", **fields}
    return item_id, item_note(collection, MANIFEST, EN_VOCABULARY, item_id, stored)


@pytest.mark.p0
def test_store_example_audio_gives_the_item_its_audio_and_example_card() -> None:
    collection = managed_collection(MANIFEST, reading_rules=False)
    item_id, note_id = example_item(collection)
    store, _ = wired(collection)

    written = run(store.store_example_audio(Language.EN, item_id, "Jump!", MP3))

    assert written is True
    name = managed_name(item_id, MP3)
    assert collection.notes[note_id].fields["ExampleAudio"] == f"[sound:{name}]"
    assert name in collection.media
    assert cards_of(collection, note_id)[EXAMPLE_ORD] == EXAMPLE_DECK["en"]


@pytest.mark.p1
@pytest.mark.parametrize(
    ("fields", "example"),
    [
        ({}, "Jump now!"),  # the Example changed since the read
        ({"ExampleAudio": "[sound:mine.mp3]"}, "Jump!"),  # already has example audio
        ({"ExampleRussian": ""}, "Jump!"),  # no Russian: no Example card to make
    ],
    ids=["changed", "has-audio", "no-russian"],
)
def test_store_example_audio_writes_nothing_for_an_item_it_no_longer_fits(
    fields: dict[str, str], example: str
) -> None:
    collection = managed_collection(MANIFEST, reading_rules=False)
    item_id, _ = example_item(collection, **fields)
    store, replay = wired(collection)

    written = run(store.store_example_audio(Language.EN, item_id, example, MP3))

    assert written is False
    assert sent_writes(replay.sent) == []


@pytest.mark.p1
def test_store_example_audio_is_gated_by_setup() -> None:
    collection = managed_collection(MANIFEST, reading_rules=False)
    item_id, _ = example_item(collection)
    store, replay = wired(collection, state="needs_migration")

    outcome = settle(store.store_example_audio(Language.EN, item_id, "Jump!", MP3))

    assert isinstance(outcome, AppError) and outcome.code is ErrorCode.SETUP_REQUIRED
    assert sent_writes(replay.sent) == []


# ---- the v1 to v2 migration ---------------------------------------------------------------


def manifest_v1() -> Manifest:
    """The SchemaVersion 1 manifest: no ExampleAudio field and no Example card template."""
    note_types = tuple(
        dataclasses.replace(
            nt,
            fields=tuple(f for f in nt.fields if f.name != "ExampleAudio"),
            templates=tuple(t for t in nt.templates if t.name != "Example"),
        )
        for nt in MANIFEST.note_types
    )
    decks = tuple(d for d in MANIFEST.decks if not d.endswith("::Example"))
    preset = dataclasses.replace(
        MANIFEST.preset, decks=tuple(d for d in MANIFEST.preset.decks if d in decks)
    )
    return dataclasses.replace(
        MANIFEST, schema_version=1, note_types=note_types, decks=decks, preset=preset
    )


def v1_anki() -> Collection:
    """Anki set up at SchemaVersion 1, with a Vocabulary, a Sentence and a Capture note."""
    v1 = manifest_v1()
    collection = apply_manifest(stock_collection(), v1)
    vocabulary = {"Target": "jump", "Example": "Jump!", "ExampleRussian": "Прыгай!"}
    item_note(collection, v1, EN_VOCABULARY, str(uuid.uuid4()), vocabulary)
    item_note(collection, v1, EN_SENTENCE, str(uuid.uuid4()), {"Target": "Hi."})
    managed_note(collection, v1, f"{PREFIX} Capture", "1")
    return collection


def setup_store(collection: Collection) -> tuple[AnkiConnectStore, AnkiConnectReplay]:
    """The production store wiring: the current manifest and `build_migrations`."""
    gate = SetupGate(MANIFEST)
    replay = AnkiConnectReplay(collection_replies(collection, writes=True))
    client = AnkiConnectClient(
        ANKI_URL, transport=replay.transport, guard=PrefixGuard(MANIFEST), gate=gate
    )
    store = AnkiConnectStore(
        client, AnkiLock(), manifest=MANIFEST, gate=gate, migrations=build_migrations(PREFIX)
    )
    return store, replay


@pytest.mark.p0
def test_the_production_migration_adds_example_audio_to_both_vocabulary_note_types() -> None:
    steps = (AddField(EN_VOCABULARY, "ExampleAudio"), AddField(FR_VOCABULARY, "ExampleAudio"))
    assert build_migrations(PREFIX) == (Migration(1, steps),)
    dev = build_migrations("LanguageLabDev")
    assert {step.note_type for step in dev[0].steps} == {
        "LanguageLabDev English Vocabulary",
        "LanguageLabDev French Vocabulary",
    }


@pytest.mark.p0
def test_a_v1_anki_previews_migrate_and_templates_repair_for_the_vocabulary_types_only() -> None:
    """Preview: the field change and the missing Example template show for the two Vocabulary
    note types only; the new Example decks are Creates; every note type holding notes is
    migrated; the state is needs_migration.
    """
    store, replay = setup_store(v1_anki())

    preview = run(store.setup_preview())

    schema_items = {
        i for i in preview.items if i.kind in (ResourceKind.NOTE_TYPE, ResourceKind.TEMPLATES)
    }
    assert schema_items == {
        PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, EN_VOCABULARY),
        PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, FR_VOCABULARY),
        PlanItem(PlanAction.REPAIR, ResourceKind.TEMPLATES, EN_VOCABULARY),
        PlanItem(PlanAction.REPAIR, ResourceKind.TEMPLATES, FR_VOCABULARY),
    }
    created = {i.name for i in preview.items if i.action is PlanAction.CREATE}
    assert created == set(EXAMPLE_DECK.values())
    assert preview.state is SetupState.NEEDS_MIGRATION
    assert sent_writes(replay.sent) == []


@pytest.mark.p0
def test_applying_setup_on_a_v1_anki_migrates_to_v2_and_leaves_ords_0_to_3_unchanged() -> None:
    """AC: both Vocabulary note types gain ExampleAudio and the Example template, every managed
    note is at SchemaVersion 2, ords 0-3 templates are unchanged, no card or note is deleted, no
    Example card is made yet, and the verification is ready.
    """
    collection = v1_anki()
    before_templates = {
        name: {card: dict(sides) for card, sides in model.templates.items()}
        for name, model in collection.models.items()
    }
    before_cards = dict(collection.cards)
    before_notes = set(collection.notes)
    store, replay = setup_store(collection)

    async def preview_then_apply() -> Any:
        preview = await store.setup_preview()
        return await store.setup_apply(plan_hash(preview.items))

    verified = run(preview_then_apply())

    for name in (EN_VOCABULARY, FR_VOCABULARY):
        model = collection.models[name]
        assert model.fields[-1] == "ExampleAudio"
        assert list(model.templates) == ["Understand", "Produce", "Write", "Pronounce", "Example"]
        old = before_templates[name]
        assert {k: v for k, v in model.templates.items() if k != "Example"} == old
    for name, model in collection.models.items():
        if name.startswith(PREFIX) and "Vocabulary" not in name:
            assert model.templates == before_templates[name], name
    assert {n.fields["SchemaVersion"] for n in collection.notes.values()} == {"2"}
    assert set(collection.notes) == before_notes
    assert set(collection.cards) == set(before_cards)  # no card deleted, no Example card yet
    writes = sent_writes(replay.sent)
    assert "deleteNotes" not in writes
    # the field exists before a template naming it is added
    last_field_add = max(i for i, w in enumerate(writes) if w == "modelFieldAdd")
    assert last_field_add < writes.index("modelTemplateAdd")
    assert verified.items == ()
    assert verified.state is SetupState.READY


@pytest.mark.p1
def test_a_sentence_note_type_is_never_given_example_audio() -> None:
    collection = v1_anki()
    sentence_fields = list(collection.models[EN_SENTENCE].fields)
    store, replay = setup_store(collection)

    async def preview_then_apply() -> None:
        preview = await store.setup_preview()
        await store.setup_apply(plan_hash(preview.items))

    run(preview_then_apply())

    assert collection.models[EN_SENTENCE].fields == sentence_fields
    for request in replay.sent:
        if request.body.get("action") in ("modelFieldAdd", "modelTemplateAdd"):
            assert "Vocabulary" in request.body["params"]["modelName"]
