"""Story 4.1: Save Item in the Anki adapter, with the `keep` audio intent (AD-4, AD-6, AD-9,
AD-10, AD-19, AD-20).

`AnkiStore.save_item(item_id, language, content, audio=AudioIntent.KEEP)` is one use case under
the Anki lock, create-or-update by ItemId (AD-20):

1. **Lookup by ItemId (AD-4).** `findNotes` on the exact note type scope of the Item's Language
   and Category (`note_query`), then `notesInfo`, and the ItemId is matched in Python on the
   decoded field. Neither the ItemId nor any user text ever enters a query.
2. **Not found: create (AD-6, keep order).** `addNote` of `<Prefix> <Language> <Category>` into
   its Language/Category **Pronunciation** deck with `allowDuplicate: true`, every field written
   through the codec: the alternatives joined with `", "` (AD-10), `Audio` empty, `ItemId` and
   `SchemaVersion`. Then cards 0-2 move to their Study decks with `changeDeck`. One note, exactly
   four Cards: Understand, Produce and Write in `Study::<Language>::<Category>::<Exercise>`,
   Pronounce in `Pronunciation::<Language>::<Category>`.
3. **Found: update.** `updateNoteFields` on that note with the content's fields, through the
   codec. `Audio` (keep) and `SchemaVersion` are not sent, no card moves, and no second note is
   made.

Every write goes through `client.invoke`, so the AD-4 Prefix guard and the AD-19 setup gate both
apply. A failing Anki is `anki_unavailable`; a failed `addNote` sends no `changeDeck`.

Anki is the in-memory collection in tests/support/anki_state.py. The real `changeDeck` and
`updateNoteFields` replies are hand-built from AnkiConnect's documented ones; story 4.4's
acceptance run checks them. `language_lab.domain.items` doesn't exist yet, so `Language` comes
from domain/catalog.py and ItemContent through tests/support/items.py.
"""

import uuid
from typing import Any

import pytest

from language_lab.adapters.anki.codec import encode_field
from language_lab.adapters.anki.query import note_query
from language_lab.domain.catalog import Language
from tests.support.aio import settle
from tests.support.anki_connect import AnkiConnectReplay, refused
from tests.support.anki_state import (
    Collection,
    apply_manifest,
    item_note,
    managed_collection,
    sent_queries,
    sent_writes,
)
from tests.support.captures import DEV_MANIFEST, GATED_STATES, MANIFEST, PREFIX, code_of, wired
from tests.support.items import (
    SENTENCE,
    VOCABULARY,
    content,
    keep,
    note_type_of,
    stored_fields,
)

pytestmark = pytest.mark.skip(
    reason="ATDD red phase: un-skip when story 4.1 adds AnkiStore.save_item"
)

LANGUAGE_NAMES = {"en": "English", "fr": "French"}
DECK_WORDS = {"vocabulary": "Vocabulary", "sentence": "Sentences"}

# Every Language and Category: the four note types Save writes
SAVES = {
    "en-vocabulary": ("en", VOCABULARY),
    "en-sentence": ("en", SENTENCE),
    "fr-vocabulary": ("fr", VOCABULARY),
    "fr-sentence": ("fr", SENTENCE),
}


def save(store: Any, item_id: str, language: str, wire: dict[str, Any]) -> Any:
    """`store.save_item(...)`'s result, or the exception it raised."""
    return settle(store.save_item(item_id, Language(language), content(wire), audio=keep()))


def expected_decks(language: str, wire: dict[str, Any]) -> dict[int, str]:
    """Each card ord's deck (FR-20): ords 0-2 in Study, ord 3 in Pronunciation."""
    branch = f"{LANGUAGE_NAMES[language]}::{DECK_WORDS[wire['category']]}"
    study = f"{PREFIX}::Study::{branch}"
    return {
        0: f"{study}::Understand",
        1: f"{study}::Produce",
        2: f"{study}::Write",
        3: f"{PREFIX}::Pronunciation::{branch}",
    }


def notes_of(collection: Collection, note_type: str) -> dict[int, Any]:
    return {i: note for i, note in collection.notes.items() if note.model == note_type}


def card_decks(collection: Collection, note_id: int) -> dict[int, str]:
    return {c.ord: c.deck for c in collection.cards.values() if c.note == note_id}


def sent_note(replay: AnkiConnectReplay, action: str) -> dict[str, Any]:
    """The `note` param of the one `action` sent."""
    (body,) = [r.body for r in replay.sent if r.body.get("action") == action]
    return body["params"]["note"]


@pytest.mark.p0
@pytest.mark.parametrize(("language", "wire"), SAVES.values(), ids=SAVES.keys())
def test_a_new_item_id_makes_one_note_with_four_cards_in_their_decks(
    language: str, wire: dict[str, Any]
) -> None:
    """AC-4: a new ItemId adds one note of its Language/Category note type, its fields written
    through the codec, to the Pronunciation deck with `allowDuplicate`, then moves cards 0-2 to
    their Study decks: exactly four Cards, each in its deck.
    """
    collection = managed_collection(MANIFEST)
    note_type = note_type_of(language, wire)
    store, replay = wired(collection)
    item_id = str(uuid.uuid4())

    save(store, item_id, language, wire)

    notes = notes_of(collection, note_type)
    assert [card_decks(collection, i) for i in notes] == [expected_decks(language, wire)]
    (note_id,) = notes
    assert collection.notes[note_id].fields == stored_fields(wire, item_id)
    added = sent_note(replay, "addNote")
    assert added["deckName"] == expected_decks(language, wire)[3]
    assert added["options"]["allowDuplicate"] is True
    writes = sent_writes(replay.sent)
    assert writes[0] == "addNote"
    assert set(writes[1:]) == {"changeDeck"}


def _another_item(collection: Collection, item_id: str) -> None:
    fields = {"Target": "notwithstanding", "Russian": "несмотря на"}
    item_note(collection, MANIFEST, note_type_of("en", VOCABULARY), str(uuid.uuid4()), fields)


def _same_target_as_another(collection: Collection, item_id: str) -> None:
    fields = {"Target": encode_field(VOCABULARY["target"]), "Russian": "сделать вывод"}
    item_note(collection, MANIFEST, note_type_of("en", VOCABULARY), str(uuid.uuid4()), fields)


def _dev_item_with_the_id(collection: Collection, item_id: str) -> None:
    """A `LanguageLabDev` Item carrying the same ItemId: another Prefix, never a match."""
    apply_manifest(collection, DEV_MANIFEST)
    dev_type = f"{DEV_MANIFEST.prefix} English Vocabulary"
    item_note(collection, DEV_MANIFEST, dev_type, item_id, {"Target": "dev", "Russian": "дев"})


@pytest.mark.p0
@pytest.mark.parametrize(
    "arrange",
    [lambda collection, _: None, _another_item, _same_target_as_another, _dev_item_with_the_id],
    ids=["no-items", "another-item", "same-target-as-another", "dev-prefix-item-with-the-id"],
)
def test_the_item_id_lookup_queries_only_the_exact_note_type_scope(arrange: Any) -> None:
    """AC-5: the ItemId lookup sends only the exact query of the Item's note type; neither the
    ItemId nor the Target is sent outside `addNote`, and an Item with the same Target, or another
    Prefix's Item with the same ItemId, is never matched: a new note is made.
    """
    collection = managed_collection(MANIFEST)
    item_id = str(uuid.uuid4())
    arrange(collection, item_id)
    note_type = note_type_of("en", VOCABULARY)
    before = set(notes_of(collection, note_type))
    store, replay = wired(collection)

    save(store, item_id, "en", VOCABULARY)

    assert set(sent_queries(replay.sent)) == {note_query(MANIFEST, note_type)}
    bodies = repr([r.body for r in replay.sent if r.body.get("action") != "addNote"])
    assert item_id not in bodies
    assert VOCABULARY["target"] not in bodies
    assert len(set(notes_of(collection, note_type)) - before) == 1


def _stored_plain(collection: Collection, item_id: str) -> int:
    fields = {"Target": "jump to conclusions", "Russian": "сделать вывод", "Audio": "[sound:a.mp3]"}
    return item_note(collection, MANIFEST, note_type_of("en", VOCABULARY), item_id, fields)


def _stored_in_editor_markup(collection: Collection, item_id: str) -> int:
    """Edited in Anki's editor: the hidden ItemId wrapped in markup the codec strips."""
    note_id = _stored_plain(collection, str(uuid.uuid4()))
    collection.notes[note_id].fields["ItemId"] = f"<div>{item_id}&nbsp;</div>"
    return note_id


@pytest.mark.p0
@pytest.mark.parametrize(
    "arrange",
    [_stored_plain, _stored_in_editor_markup],
    ids=["stored-plain", "stored-in-editor-markup"],
)
def test_a_retried_save_with_the_same_item_id_updates_that_note(arrange: Any) -> None:
    """AC-6: a Save whose ItemId is already stored updates that note's fields through the codec
    with `updateNoteFields` only: no second note, no card moved, and `Audio` (keep) and
    `SchemaVersion` left as they are (AD-20).
    """
    collection = managed_collection(MANIFEST)
    item_id = str(uuid.uuid4())
    note_id = arrange(collection, item_id)
    note_type = note_type_of("en", VOCABULARY)
    decks_before = card_decks(collection, note_id)
    store, replay = wired(collection)

    save(store, item_id, "en", VOCABULARY)

    assert sent_writes(replay.sent) == ["updateNoteFields"]
    assert list(notes_of(collection, note_type)) == [note_id]
    stored = collection.notes[note_id].fields
    assert stored["Russian"] == encode_field(VOCABULARY["russian"])
    assert stored["Example"] == encode_field(VOCABULARY["example"])
    assert stored["Audio"] == "[sound:a.mp3]"
    assert card_decks(collection, note_id) == decks_before
    sent = sent_note(replay, "updateNoteFields")
    assert sent["id"] == note_id
    assert "Audio" not in sent["fields"]
    assert "SchemaVersion" not in sent["fields"]


@pytest.mark.p0
@pytest.mark.parametrize("state", GATED_STATES)
def test_a_gated_anki_refuses_save_item_before_any_write(state: str) -> None:
    """AC-7: unless the SetupState is `ready`, save_item is `setup_required` and nothing is
    written (AD-19).
    """
    collection = managed_collection(MANIFEST)
    store, replay = wired(collection, state=state)

    outcome = save(store, str(uuid.uuid4()), "en", VOCABULARY)

    assert code_of(outcome) == "setup_required"
    assert sent_writes(replay.sent) == []
    assert notes_of(collection, note_type_of("en", VOCABULARY)) == {}


def _anki_error(body: Any) -> dict[str, Any]:
    return {"result": None, "error": "collection is not available"}


@pytest.mark.p0
@pytest.mark.parametrize("failure", ["anki-down", "add-note-fails"])
def test_a_failing_anki_returns_anki_unavailable_with_no_note(failure: str) -> None:
    """AC-8: Anki down, or an `addNote` that fails, is `anki_unavailable`; no note is made and
    no `changeDeck` is sent.
    """
    collection = managed_collection(MANIFEST)
    if failure == "anki-down":
        store, replay = wired(collection, failure=refused)
    else:
        store, replay = wired(collection, replies={"addNote": _anki_error})

    outcome = save(store, str(uuid.uuid4()), "en", VOCABULARY)

    assert code_of(outcome) == "anki_unavailable"
    assert "changeDeck" not in sent_writes(replay.sent)
    assert notes_of(collection, note_type_of("en", VOCABULARY)) == {}


@pytest.mark.p1
def test_a_failing_card_move_is_anki_unavailable_and_a_retry_updates_the_note() -> None:
    """AC-8: a `changeDeck` that fails after `addNote` is `anki_unavailable`, and the cards stay
    in the Pronunciation deck (a tolerated AD-6 leftover for Setup to report). A retry with that
    ItemId finds the note and updates it: still one note (AD-20).
    """
    collection = managed_collection(MANIFEST)
    note_type = note_type_of("en", VOCABULARY)
    store, _ = wired(collection, replies={"changeDeck": _anki_error})
    item_id = str(uuid.uuid4())

    outcome = save(store, item_id, "en", VOCABULARY)

    assert code_of(outcome) == "anki_unavailable"
    (note_id,) = notes_of(collection, note_type)
    pronunciation = expected_decks("en", VOCABULARY)[3]
    assert set(card_decks(collection, note_id).values()) == {pronunciation}
    retry_store, retry_replay = wired(collection)
    save(retry_store, item_id, "en", VOCABULARY)
    assert sent_writes(retry_replay.sent) == ["updateNoteFields"]
    assert list(notes_of(collection, note_type)) == [note_id]
