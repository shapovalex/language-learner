"""Study lock: a new Item's Produce, Write and Example cards wait for its Understand card
(plan lock-study-cards-until-understood).

Save adds a new Item's note with the lock tag `<Prefix>::Locked` and, once its cards are in
their decks, suspends its Produce (ord 1), Write (ord 2) and Example (ord 4) cards; Understand
(ord 0) and Pronounce (ord 3) are left alone. `unlock_answered_items()` (run before each Sync)
finds the locked notes whose Understand card is no longer new, with the exact note type scope
plus fixed literals, unsuspends their Produce and Write cards (and the Example card when
`ExampleAudio` holds something), then removes the tag. Notes without the tag are never touched.

Anki is the in-memory collection in tests/support/anki_state.py, through the real guarded,
gated client.
"""

import uuid
from typing import Any

import pytest

from language_lab.adapters.anki.query import unlockable_notes_query
from language_lab.domain.catalog import Category, Language
from language_lab.domain.items import AudioIntent
from tests.support.aio import settle
from tests.support.anki_connect import refused
from tests.support.anki_state import (
    Collection,
    item_note,
    managed_collection,
    review_card,
    sent_queries,
    sent_writes,
)
from tests.support.audio import MP3
from tests.support.captures import GATED_STATES, MANIFEST, PREFIX, code_of, wired
from tests.support.items import SENTENCE, VOCABULARY, content

LOCK_TAG = f"{PREFIX}::Locked"
EN_VOCABULARY = f"{PREFIX} English Vocabulary"


def note_of(collection: Collection, item_id: str) -> tuple[int, Any]:
    (found,) = [(i, n) for i, n in collection.notes.items() if n.fields.get("ItemId") == item_id]
    return found


def suspended_by_ord(collection: Collection, note_id: int) -> dict[int, bool]:
    return {c.ord: c.suspended for c in collection.cards.values() if c.note == note_id}


def decks_by_ord(collection: Collection, note_id: int) -> dict[int, str]:
    return {c.ord: c.deck for c in collection.cards.values() if c.note == note_id}


def save(store: Any, item_id: str, wire: dict[str, Any], *, example: bytes | None = None) -> Any:
    return settle(
        store.save_item(
            item_id,
            Language.EN,
            content(wire),
            audio=AudioIntent.KEEP,
            example_audio_bytes=example,
        )
    )


def locked_item(collection: Collection, *, example_audio: str = "", reviewed: bool = False) -> int:
    """A Vocabulary Item as a locked Save leaves it: the tag, ords 1, 2 (and 4 when made)
    suspended; its Understand card answered once when `reviewed`.
    """
    fields = {
        "Target": "jump to conclusions",
        "Russian": "делать поспешные выводы",
        "Example": "Don't jump to conclusions.",
        "ExampleRussian": "Не делай поспешных выводов.",
        "ExampleAudio": example_audio,
    }
    return item_note(
        collection,
        MANIFEST,
        EN_VOCABULARY,
        str(uuid.uuid4()),
        fields,
        tags=[LOCK_TAG],
        suspended_ords=(1, 2, 4),
        reviewed_ords=(0,) if reviewed else (),
    )


@pytest.mark.p0
@pytest.mark.parametrize(
    ("wire", "example", "locked_ords"),
    [(VOCABULARY, MP3, {1, 2, 4}), (VOCABULARY, None, {1, 2}), (SENTENCE, None, {1, 2})],
    ids=["vocabulary-with-example-audio", "vocabulary", "sentence"],
)
def test_a_new_item_is_saved_locked(
    wire: dict[str, Any], example: bytes | None, locked_ords: set[int]
) -> None:
    """New Item: the note has the lock tag; ords 1, 2 (and 4 if made) suspended; 0, 3 not."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    store, replay = wired(collection)
    item_id = str(uuid.uuid4())

    assert save(store, item_id, wire, example=example) is None

    note_id, note = note_of(collection, item_id)
    assert note.tags == [LOCK_TAG]
    suspended = suspended_by_ord(collection, note_id)
    assert {ord for ord, is_suspended in suspended.items() if is_suspended} == locked_ords
    assert suspended[0] is False
    assert suspended[3] is False
    assert sent_writes(replay.sent).count("suspend") == 1


@pytest.mark.p0
def test_a_locked_item_whose_understand_card_is_new_stays_locked() -> None:
    """Not yet answered: the unlock writes nothing and leaves the note locked."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    note_id = locked_item(collection, example_audio="[sound:x.mp3]")
    store, replay = wired(collection)

    assert settle(store.unlock_answered_items()) == 0

    assert sent_writes(replay.sent) == []
    assert collection.notes[note_id].tags == [LOCK_TAG]
    assert suspended_by_ord(collection, note_id) == {0: False, 1: True, 2: True, 3: False, 4: True}


@pytest.mark.p0
def test_an_answered_locked_item_is_unlocked() -> None:
    """Answered: ords 1, 2 and 4 (it has example audio) unsuspended, the tag removed; the
    searches sent are the exact unlockable scopes only.
    """
    collection = managed_collection(MANIFEST, reading_rules=False)
    note_id = locked_item(collection, example_audio="[sound:x.mp3]", reviewed=True)
    waiting = locked_item(collection)
    store, replay = wired(collection)

    assert settle(store.unlock_answered_items()) == 1

    assert collection.notes[note_id].tags == []
    assert suspended_by_ord(collection, note_id) == {k: False for k in range(5)}
    assert collection.notes[waiting].tags == [LOCK_TAG]
    assert sent_writes(replay.sent) == ["unsuspend", "removeTags"]
    expected = {
        unlockable_notes_query(MANIFEST, MANIFEST.item_note_type(language, category))
        for language in Language
        for category in Category
    }
    assert set(sent_queries(replay.sent)) == expected
    # A second pass finds nothing left to unlock
    assert settle(store.unlock_answered_items()) == 0


@pytest.mark.p0
def test_an_answered_locked_item_without_example_audio_keeps_its_example_card_suspended() -> None:
    """Answered, `ExampleAudio` empty: Produce and Write unlocked, Example stays suspended."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    note_id = locked_item(collection, example_audio="[sound:x.mp3]", reviewed=True)
    collection.notes[note_id].fields["ExampleAudio"] = ""  # emptied since, its card kept
    store, _ = wired(collection)

    assert settle(store.unlock_answered_items()) == 1

    assert collection.notes[note_id].tags == []
    unlocked = {0: False, 1: False, 2: False, 3: False, 4: True}
    assert suspended_by_ord(collection, note_id) == unlocked


@pytest.mark.p0
def test_example_audio_arriving_while_locked_leaves_the_example_card_suspended() -> None:
    """Example audio arrives while locked: the Example card moves to its Study deck, suspended;
    the unlock frees it once Understand is answered.
    """
    collection = managed_collection(MANIFEST, reading_rules=False)
    store, _ = wired(collection)
    item_id = str(uuid.uuid4())
    save(store, item_id, VOCABULARY)
    note_id, _ = note_of(collection, item_id)
    assert 4 not in suspended_by_ord(collection, note_id)

    example = VOCABULARY["example"]
    assert settle(store.store_example_audio(Language.EN, item_id, example, MP3)) is True

    assert decks_by_ord(collection, note_id)[4] == MANIFEST.card_deck(EN_VOCABULARY, 4)
    assert suspended_by_ord(collection, note_id)[4] is True
    review_card(collection, note_id, 0)
    assert settle(store.unlock_answered_items()) == 1
    assert suspended_by_ord(collection, note_id) == {k: False for k in range(5)}


@pytest.mark.p0
def test_an_existing_item_updated_by_save_is_not_locked() -> None:
    """Existing Item updated: no tag, no suspend; behaves as before."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    item_id = str(uuid.uuid4())
    note_id = item_note(collection, MANIFEST, EN_VOCABULARY, item_id, {"Target": "t"})
    store, replay = wired(collection)

    save(store, item_id, VOCABULARY, example=MP3)

    assert collection.notes[note_id].tags == []
    assert "suspend" not in sent_writes(replay.sent)
    assert not any(suspended_by_ord(collection, note_id).values())


@pytest.mark.p0
def test_a_card_the_user_suspended_on_an_unlocked_note_is_never_unsuspended() -> None:
    """No lock tag: the unlock never touches the note, even with Understand answered."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    note_id = item_note(
        collection,
        MANIFEST,
        EN_VOCABULARY,
        str(uuid.uuid4()),
        {"Target": "t"},
        suspended_ords=(1, 2),
        reviewed_ords=(0,),
    )
    store, replay = wired(collection)

    assert settle(store.unlock_answered_items()) == 0

    assert sent_writes(replay.sent) == []
    assert suspended_by_ord(collection, note_id) == {0: False, 1: True, 2: True, 3: False}


@pytest.mark.p1
def test_a_save_failing_after_add_note_leaves_the_tag_for_a_later_unlock() -> None:
    """Failure mid-way: the tag is already on the note, so a later unlock still resolves it."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    failing = {"changeDeck": lambda body: {"result": None, "error": "boom"}}
    store, _ = wired(collection, replies=failing)
    item_id = str(uuid.uuid4())

    assert code_of(save(store, item_id, VOCABULARY)) == "anki_unavailable"

    note_id, note = note_of(collection, item_id)
    assert note.tags == [LOCK_TAG]
    assert suspended_by_ord(collection, note_id) == {0: False, 1: True, 2: True, 3: False}
    review_card(collection, note_id, 0)
    store, _ = wired(collection)
    assert settle(store.unlock_answered_items()) == 1
    assert collection.notes[note_id].tags == []
    assert not any(suspended_by_ord(collection, note_id).values())


@pytest.mark.p1
@pytest.mark.parametrize("state", GATED_STATES)
def test_the_unlock_is_gated_and_writes_nothing_when_setup_is_not_ready(state: str) -> None:
    """Setup not ready: the unlock raises `setup_required` before any write."""
    collection = managed_collection(MANIFEST, reading_rules=False)
    note_id = locked_item(collection, reviewed=True)
    store, replay = wired(collection, state=state)

    assert code_of(settle(store.unlock_answered_items())) == "setup_required"

    assert sent_writes(replay.sent) == []
    assert collection.notes[note_id].tags == [LOCK_TAG]


@pytest.mark.p1
def test_the_unlock_raises_anki_unavailable_when_anki_is_down() -> None:
    """Anki down: `anki_unavailable` (the Sync logs and skips it)."""
    store, _ = wired(managed_collection(MANIFEST, reading_rules=False), failure=refused)

    assert code_of(settle(store.unlock_answered_items())) == "anki_unavailable"
