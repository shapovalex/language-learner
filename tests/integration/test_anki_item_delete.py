"""Story 5.3 destructive adapter contract: gate, one lock, scope and AD-6 stop/retry.

Exactly one primary scaffold per assigned criterion; secondary branches belong to the
green-phase checklist. Missing delete_item is captured as an outcome, so the first failure
is the promised behavior's assertion. Histories require real Anki acceptance evidence.
"""

import uuid
from typing import Any

import pytest

from language_lab.adapters.anki.query import note_query
from tests.support.aio import settle
from tests.support.anki_state import (
    apply_manifest,
    collection_replies,
    item_note,
    managed_collection,
    sent_queries,
    sent_writes,
)
from tests.support.captures import DEV_MANIFEST, MANIFEST, code_of
from tests.support.duplicates import sentence, vocabulary
from tests.support.item_delete import (
    ObservedLock,
    action_bodies,
    delete_item,
    media_names,
    put_item,
    wired_delete,
)
from tests.support.items import note_type_of, stored_fields

pytestmark = pytest.mark.skip(reason="ATDD RED: story 5.3 Item deletion is not implemented")


@pytest.mark.p0
def test_setup_gate_refuses_delete_and_preserves_note_cards_and_media() -> None:
    """[P0] AC-2 A non-ready SetupState refuses deletion before any write."""
    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection)
    collection.media.update(media_names(item_id))
    before_cards = dict(collection.cards)
    store, replay = wired_delete(collection, state="needs_setup")

    outcome = settle(delete_item(store, item_id))

    assert code_of(outcome) == "setup_required"
    assert sent_writes(replay.sent) == []
    assert note_id in collection.notes
    assert collection.cards == before_cards
    assert collection.media == set(media_names(item_id))


@pytest.mark.p0
def test_delete_holds_one_shared_lock_through_the_last_media_write() -> None:
    """[P0] AC-3 Lookup, note deletion and all media cleanup run under one Anki lock hold."""
    collection = managed_collection(MANIFEST)
    item_id, _ = put_item(collection)
    collection.media.update(media_names(item_id))
    lock = ObservedLock()
    store, replay = wired_delete(collection, lock=lock)

    outcome = settle(delete_item(store, item_id))

    assert lock.holds == 1
    assert outcome is None
    assert lock.request_depths and set(lock.request_depths) == {1}
    assert sent_writes(replay.sent)[-1] == "deleteMediaFile"
    assert collection.media == set()
    assert lock.depth == 0


@pytest.mark.p0
def test_delete_removes_only_the_scoped_note_cards_and_matching_media_in_order() -> None:
    """[P0] AC-4 Delete the scoped Item note/four Cards before its media; keep all others."""
    collection = managed_collection(MANIFEST)
    item_id, target = put_item(collection)
    _, other = put_item(collection)
    french = item_note(
        collection,
        MANIFEST,
        note_type_of("fr", vocabulary()),
        item_id,
        stored_fields(vocabulary(), item_id),
    )
    apply_manifest(collection, DEV_MANIFEST)
    dev = item_note(
        collection,
        DEV_MANIFEST,
        f"{DEV_MANIFEST.prefix} English Vocabulary",
        item_id,
        stored_fields(vocabulary(), item_id),
    )
    matching = media_names(item_id)
    kept_media = {
        *media_names(str(uuid.uuid4())),
        *media_names(item_id, prefix=DEV_MANIFEST.prefix),
        "personal-audio.mp3",
    }
    collection.media.update([*matching, *kept_media])
    target_cards = {i for i, card in collection.cards.items() if card.note == target}
    kept_cards = {i: card for i, card in collection.cards.items() if card.note != target}
    store, replay = wired_delete(collection)

    outcome = settle(delete_item(store, item_id))

    assert target not in collection.notes
    assert outcome is None
    assert set(collection.notes) == {other, french, dev}
    assert len(target_cards) == 4
    assert not target_cards.intersection(collection.cards)
    assert collection.cards == kept_cards
    assert collection.media == kept_media
    writes = sent_writes(replay.sent)
    assert writes == ["deleteNotes", *["deleteMediaFile"] * len(matching)]
    bodies = action_bodies(replay)
    assert [b["params"]["notes"] for b in bodies if b["action"] == "deleteNotes"] == [[target]]
    deleted_media = [b["params"]["filename"] for b in bodies if b["action"] == "deleteMediaFile"]
    assert set(deleted_media) == set(matching)
    scopes = {note_query(MANIFEST, note_type_of("en", wire)) for wire in (vocabulary(), sentence())}
    assert sent_queries(replay.sent)
    assert set(sent_queries(replay.sent)).issubset(scopes)
    assert all(item_id not in query for query in sent_queries(replay.sent))


@pytest.mark.p0
def test_note_delete_failure_stops_before_any_media_delete() -> None:
    """[P0] AC-6 A failed note deletion returns an error and never attempts media cleanup."""
    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection)
    collection.media.update(media_names(item_id))
    before_cards = dict(collection.cards)
    store, replay = wired_delete(
        collection, replies={"deleteNotes": {"result": None, "error": "collection unavailable"}}
    )

    outcome = settle(delete_item(store, item_id))

    assert code_of(outcome) == "anki_unavailable"
    assert sent_writes(replay.sent) == ["deleteNotes"]
    assert note_id in collection.notes
    assert collection.cards == before_cards
    assert collection.media == set(media_names(item_id))


@pytest.mark.p0
def test_media_failure_stops_and_retry_cleans_leftovers_after_note_is_gone() -> None:
    """[P0] AC-7 Partial media cleanup stops; retry finishes despite the already-gone note."""
    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection)
    names = media_names(item_id)
    collection.media.update(names)
    answers = collection_replies(collection, writes=True)
    failed_names: list[str] = []
    removed_names: list[str] = []
    retry = False

    def delete_media(body: Any) -> Any:
        name = body["params"]["filename"]
        # Fail the second cleanup, irrespective of the adapter's enumeration order.
        if not retry and len(removed_names) == 1:
            failed_names.append(name)
            return {"result": None, "error": "media unavailable"}
        removed_names.append(name)
        return answers["deleteMediaFile"](body)

    store, replay = wired_delete(collection, replies={"deleteMediaFile": delete_media})

    first_outcome = settle(delete_item(store, item_id))
    note_gone_after_failure = note_id not in collection.notes
    media_left_after_failure = set(collection.media)
    removed_before_retry = list(removed_names)
    failed_before_retry = list(failed_names)
    writes_before_retry = sent_writes(replay.sent)
    before_retry = len(replay.sent)
    retry = True

    outcome = settle(delete_item(store, item_id))

    assert collection.media == set()
    assert outcome is None
    assert code_of(first_outcome) == "anki_unavailable"
    assert note_gone_after_failure
    assert len(removed_before_retry) == 1
    assert len(failed_before_retry) == 1
    assert len(media_left_after_failure) == 2
    assert writes_before_retry == ["deleteNotes", "deleteMediaFile", "deleteMediaFile"]
    assert sent_writes(replay.sent[before_retry:]) == ["deleteMediaFile", "deleteMediaFile"]
