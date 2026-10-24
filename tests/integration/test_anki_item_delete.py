"""Story 5.3 destructive adapter contract: gate, one lock, scope and AD-6 stop/retry.

The primary ATDD criteria and destructive boundaries run against the guarded adapter.
Histories require real Anki acceptance evidence.
"""

import uuid
from typing import Any

import pytest

from language_lab.adapters.anki.query import note_query
from language_lab.domain.catalog import Language
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


@pytest.mark.parametrize("wire", [vocabulary(), sentence()])
@pytest.mark.parametrize(
    ("owner_language", "requested_language"), [("fr", Language.EN), ("en", Language.FR)]
)
def test_absent_item_preserves_media_owned_by_another_language(
    wire, owner_language, requested_language
) -> None:
    collection = managed_collection(MANIFEST)
    item_id = str(uuid.uuid4())
    fields = stored_fields(wire, item_id) | {"ItemId": f"<div>{item_id}</div>"}
    note_id = item_note(collection, MANIFEST, note_type_of(owner_language, wire), item_id, fields)
    collection.media.update(media_names(item_id))
    before_cards = dict(collection.cards)
    lock = ObservedLock()
    store, replay = wired_delete(collection, lock=lock)

    outcome = settle(store.delete_item(requested_language, item_id))

    assert outcome is None
    assert note_id in collection.notes
    assert collection.cards == before_cards
    assert collection.media == set(media_names(item_id))
    assert sent_writes(replay.sent) == []
    assert lock.holds == 1
    assert set(lock.request_depths) == {1}
    owner_scope = note_query(MANIFEST, note_type_of(owner_language, wire))
    assert owner_scope in sent_queries(replay.sent)


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
    assert "getMediaFilesNames" not in [body["action"] for body in action_bodies(replay)]
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


@pytest.mark.parametrize("state", ["needs_setup", "needs_migration", "newer_schema"])
def test_all_nonready_states_gate_leftover_cleanup_on_an_absent_note(state: str) -> None:
    collection = managed_collection(MANIFEST)
    item_id = str(uuid.uuid4())
    collection.media.update(media_names(item_id))
    store, replay = wired_delete(collection, state=state)
    outcome = settle(delete_item(store, item_id))
    assert code_of(outcome) == "setup_required"
    assert sent_writes(replay.sent) == []
    assert collection.media == set(media_names(item_id))


@pytest.mark.parametrize("wire", [vocabulary(), sentence()])
def test_both_categories_decode_the_item_id_and_succeed_without_media(wire) -> None:
    collection = managed_collection(MANIFEST)
    item_id = str(uuid.uuid4())
    fields = stored_fields(wire, item_id) | {"ItemId": f"<div>{item_id}</div>", "Audio": ""}
    note_id = item_note(collection, MANIFEST, note_type_of("en", wire), item_id, fields)
    store, replay = wired_delete(collection)
    assert settle(delete_item(store, item_id)) is None
    assert note_id not in collection.notes
    assert sent_writes(replay.sent) == ["deleteNotes"]
    start = len(replay.sent)
    assert settle(delete_item(store, item_id)) is None
    assert sent_writes(replay.sent[start:]) == []


@pytest.mark.parametrize("result", [None, {}, [123], ["valid-name", False]])
def test_malformed_media_enumeration_stops_and_releases_the_lock(result) -> None:
    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection)
    lock = ObservedLock()
    store, replay = wired_delete(
        collection, lock=lock, replies={"getMediaFilesNames": {"result": result, "error": None}}
    )
    assert code_of(settle(delete_item(store, item_id))) == "anki_unavailable"
    assert note_id not in collection.notes
    assert sent_writes(replay.sent) == ["deleteNotes"]
    assert lock.depth == 0
    # A subsequent use case can acquire the same lock after the failure.
    assert settle(store.reachable()) is True
    assert lock.holds == 2


def test_media_names_are_filtered_by_item_id_and_the_managed_filename_contract() -> None:
    collection = managed_collection(MANIFEST)
    item_id = str(uuid.uuid4())
    matching = media_names(item_id)
    kept = [
        *media_names(str(uuid.uuid4())),
        *media_names(item_id, prefix=DEV_MANIFEST.prefix),
        f"{MANIFEST.prefix}_{item_id}_invalid.mp3",
        f"{MANIFEST.prefix}_{item_id}_{'a' * 12}.mp3/../outside",
    ]
    collection.media.update([*matching, *kept])
    # Even a provider returning names outside the requested pattern must not widen cleanup.
    store, _ = wired_delete(
        collection,
        replies={"getMediaFilesNames": {"result": [*matching, *matching, *kept], "error": None}},
    )
    assert settle(delete_item(store, item_id)) is None
    assert collection.media == set(kept)


@pytest.mark.parametrize("entry", [None, [], {"noteId": True}, {"noteId": "1"}])
def test_malformed_matching_note_reply_refuses_every_write(entry) -> None:
    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection)
    answers = collection_replies(collection, writes=True)

    def notes(body):
        reply = answers["notesInfo"](body)
        original = reply["result"][0]
        reply["result"] = [original | entry if isinstance(entry, dict) else entry]
        return reply

    store, replay = wired_delete(collection, replies={"notesInfo": notes})
    assert code_of(settle(delete_item(store, item_id))) == "anki_unavailable"
    assert sent_writes(replay.sent) == []
    assert note_id in collection.notes


def test_prefix_guard_refuses_a_foreign_note_returned_by_a_malformed_lookup() -> None:
    from language_lab.adapters.anki.guard import PrefixViolation

    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection)
    answers = collection_replies(collection, writes=True)

    def foreign(body):
        reply = answers["notesInfo"](body)
        for info in reply["result"]:
            info["modelName"] = f"{DEV_MANIFEST.prefix} English Vocabulary"
        return reply

    store, replay = wired_delete(collection, replies={"notesInfo": foreign})
    assert isinstance(settle(delete_item(store, item_id)), PrefixViolation)
    assert sent_writes(replay.sent) == []
    assert note_id in collection.notes


def test_a_note_disappearing_between_reads_still_cleans_leftovers() -> None:
    collection = managed_collection(MANIFEST)
    item_id, _ = put_item(collection)
    collection.media.update(media_names(item_id))
    store, replay = wired_delete(collection, replies={"notesInfo": {"result": [{}], "error": None}})
    assert settle(delete_item(store, item_id)) is None
    assert collection.media == set()
    assert "deleteNotes" not in sent_writes(replay.sent)


def test_delete_waits_for_another_use_case_and_busy_timeout_sends_no_request() -> None:
    import asyncio

    from tests.support.aio import run, settled

    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection)
    lock = ObservedLock()
    lock.wait_seconds = 0.01
    store, replay = wired_delete(collection, lock=lock)

    async def scenario():
        async with lock.hold():
            outcome = await settled(delete_item(store, item_id))
            assert code_of(outcome) == "anki_busy"
            assert replay.sent == []
        lock.wait_seconds = 1
        async with lock.hold():
            waiting = asyncio.create_task(delete_item(store, item_id))
            await asyncio.sleep(0)
            assert not waiting.done()
            assert replay.sent == []
        await waiting

    run(scenario())
    assert note_id not in collection.notes
    assert lock.depth == 0


def test_save_cannot_enter_anki_while_delete_is_cleaning_media(monkeypatch) -> None:
    import asyncio

    from language_lab.domain.catalog import Language
    from tests.support.aio import run
    from tests.support.items import content

    collection = managed_collection(MANIFEST)
    item_id, _ = put_item(collection)
    other_id, other_note = put_item(collection)
    collection.media.update(media_names(item_id))
    lock = ObservedLock()
    store, replay = wired_delete(collection, lock=lock)
    invoke = store._client.invoke

    async def scenario():
        deleting_media = asyncio.Event()
        release_media = asyncio.Event()

        async def pause_cleanup(action, **params):
            if action == "deleteMediaFile" and not deleting_media.is_set():
                deleting_media.set()
                await release_media.wait()
            return await invoke(action, **params)

        monkeypatch.setattr(store._client, "invoke", pause_cleanup)
        deleting = asyncio.create_task(delete_item(store, item_id))
        await deleting_media.wait()
        start = len(replay.sent)
        saving = asyncio.create_task(
            store.save_item(
                other_id, Language.EN, content(vocabulary(target="saved after cleanup"))
            )
        )
        await asyncio.sleep(0)
        assert not saving.done()
        assert len(replay.sent) == start
        release_media.set()
        await asyncio.gather(deleting, saving)

    run(scenario())
    assert collection.notes[other_note].fields["Target"] == "saved after cleanup"
    assert sent_writes(replay.sent) == ["deleteNotes", *["deleteMediaFile"] * 3, "updateNoteFields"]
    assert lock.depth == 0
    assert set(lock.request_depths) == {1}


@pytest.mark.parametrize("result", [None, {}, [True], ["123"]])
def test_malformed_scope_ids_stop_before_notes_or_media_writes(result) -> None:
    collection = managed_collection(MANIFEST)
    item_id, _ = put_item(collection)
    store, replay = wired_delete(
        collection, replies={"findNotes": {"result": result, "error": None}}
    )
    assert code_of(settle(delete_item(store, item_id))) == "anki_unavailable"
    assert sent_writes(replay.sent) == []
    assert all(body["action"] == "findNotes" for body in action_bodies(replay))


def test_enumeration_failure_after_note_deletion_is_retryable() -> None:
    collection = managed_collection(MANIFEST)
    item_id, note_id = put_item(collection)
    collection.media.update(media_names(item_id))
    answers = collection_replies(collection, writes=True)
    attempts = 0

    def enumerate_media(body):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return {"result": None, "error": "unavailable"}
        return answers["getMediaFilesNames"](body)

    store, replay = wired_delete(collection, replies={"getMediaFilesNames": enumerate_media})
    assert code_of(settle(delete_item(store, item_id))) == "anki_unavailable"
    assert note_id not in collection.notes
    assert collection.media == set(media_names(item_id))
    start = len(replay.sent)
    assert settle(delete_item(store, item_id)) is None
    assert collection.media == set()
    assert sent_writes(replay.sent[start:]) == ["deleteMediaFile"] * 3
