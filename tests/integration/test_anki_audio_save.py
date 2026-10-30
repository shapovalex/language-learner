"""Story 6.1 replace Save ordering and failure boundary through the real guarded adapter."""

import copy
import uuid

import pytest

from tests.support.aio import settle
from tests.support.anki_state import item_note, managed_collection, sent_writes
from tests.support.audio import MP3, SECOND_MP3, MediaRig, managed_name, replace_audio
from tests.support.captures import MANIFEST, code_of
from tests.support.item_delete import action_bodies
from tests.support.items import VOCABULARY, note_type_of, stored_fields


class TestAudioSave:
    @pytest.mark.p0
    def test_one_lock_stores_media_before_the_note_and_four_card_placements(self) -> None:
        """[P0] AC-8 one use case stores media, adds the note, then moves only Study Cards."""
        # Given a ready managed collection and one shared observed Anki lock.
        collection = managed_collection(MANIFEST, reading_rules=False)
        rig = MediaRig(collection)
        item_id = str(uuid.uuid4())

        # When the real adapter saves a new Draft with an accepted MP3.
        outcome = settle(replace_audio(rig.store, item_id))

        # Then ordering is the primary promise; no broad result check can fail before it.
        assert sent_writes(rig.replay.sent) == [
            "storeMediaFile",
            "addNote",
            "changeDeck",
            "changeDeck",
            "changeDeck",
        ]
        assert outcome is None
        assert rig.lock.holds == 1
        assert rig.lock.depth == 0
        assert set(rig.lock.request_depths) == {1}
        (note_id,) = collection.notes
        note = collection.notes[note_id]
        assert note.fields["Audio"] == f"[sound:{managed_name(item_id)}]"
        assert note.fields["ItemId"] == item_id
        assert {card.ord: card.deck for card in collection.cards.values()} == {
            0: "LanguageLab::Study::English::Vocabulary::Understand",
            1: "LanguageLab::Study::English::Vocabulary::Produce",
            2: "LanguageLab::Study::English::Vocabulary::Write",
            3: "LanguageLab::Pronunciation::English::Vocabulary",
        }
        add = next(body for body in action_bodies(rig.replay) if body["action"] == "addNote")
        assert add["params"]["note"]["options"]["allowDuplicate"] is True
        assert (
            add["params"]["note"]["deckName"] == "LanguageLab::Pronunciation::English::Vocabulary"
        )

    @pytest.mark.p0
    def test_failed_note_write_retains_previous_values_and_stops_cleanup(self) -> None:
        """[P0] AC-15 failed note write after media storage preserves prior note and audio."""
        # Given a stored Item and old clip; Anki rejects the new note fields.
        collection = managed_collection(MANIFEST, reading_rules=False)
        item_id = str(uuid.uuid4())
        old_name = managed_name(item_id, SECOND_MP3)
        fields = {**stored_fields(VOCABULARY, item_id), "Audio": f"[sound:{old_name}]"}
        item_note(collection, MANIFEST, note_type_of("en", VOCABULARY), item_id, fields)
        before_notes, before_cards = (
            copy.deepcopy(collection.notes),
            copy.deepcopy(collection.cards),
        )
        rig = MediaRig(
            collection,
            media={old_name: SECOND_MP3},
            replies={"updateNoteFields": {"result": None, "error": "collection unavailable"}},
        )

        # When replacement stores the new clip, then the note write fails.
        outcome = settle(replace_audio(rig.store, item_id, MP3))

        # Then the promised failure code owns RED, before retention and stop assertions.
        assert code_of(outcome) == "anki_unavailable"
        assert sent_writes(rig.replay.sent) == ["storeMediaFile", "updateNoteFields"]
        assert collection.notes == before_notes
        assert collection.cards == before_cards
        assert rig.media[old_name] == SECOND_MP3
        assert rig.media[managed_name(item_id)] == MP3  # tolerated orphan, no compensation
        assert rig.lock.holds == 1
        assert rig.lock.depth == 0
        assert set(rig.lock.request_depths) == {1}


@pytest.mark.p0
def test_media_store_failure_stops_before_note_or_card_write():
    collection = managed_collection(MANIFEST, reading_rules=False)
    rig = MediaRig(collection, replies={"storeMediaFile": {"result": None, "error": "failed"}})
    result = settle(replace_audio(rig.store, str(uuid.uuid4())))
    assert code_of(result) == "anki_unavailable"
    assert sent_writes(rig.replay.sent) == ["storeMediaFile"]
    assert collection.notes == {}
    assert collection.cards == {}


@pytest.mark.p0
def test_replacement_cleans_superseded_media_only_after_successful_note_write():
    collection = managed_collection(MANIFEST, reading_rules=False)
    item_id = str(uuid.uuid4())
    old_name = managed_name(item_id, SECOND_MP3)
    fields = {**stored_fields(VOCABULARY, item_id), "Audio": f"[sound:{old_name}]"}
    item_note(collection, MANIFEST, note_type_of("en", VOCABULARY), item_id, fields)
    rig = MediaRig(collection, media={old_name: SECOND_MP3})
    assert settle(replace_audio(rig.store, item_id)) is None
    assert sent_writes(rig.replay.sent) == ["storeMediaFile", "updateNoteFields", "deleteMediaFile"]
    assert rig.media == {managed_name(item_id): MP3}
    assert len(collection.notes) == 1
    assert rig.lock.holds == 1


@pytest.mark.p0
def test_same_item_id_retry_keeps_same_hash_media_and_does_not_duplicate_note():
    collection = managed_collection(MANIFEST, reading_rules=False)
    rig = MediaRig(collection)
    item_id = str(uuid.uuid4())
    assert settle(replace_audio(rig.store, item_id)) is None
    assert settle(replace_audio(rig.store, item_id)) is None
    assert len(collection.notes) == 1
    assert rig.media == {managed_name(item_id): MP3}
    assert "deleteMediaFile" not in sent_writes(rig.replay.sent)


@pytest.mark.p0
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("category", ["vocabulary", "sentence"])
def test_replacement_bytes_and_four_decks_for_each_language_and_category(language, category):
    from language_lab.domain.catalog import Language
    from language_lab.domain.items import AudioIntent
    from tests.integration.test_anki_item_save import expected_decks
    from tests.support.items import SENTENCE, content

    wire = VOCABULARY if category == "vocabulary" else SENTENCE
    collection = managed_collection(MANIFEST, reading_rules=False)
    rig = MediaRig(collection)
    item_id = str(uuid.uuid4())
    result = settle(
        rig.store.save_item(
            item_id, Language(language), content(wire), AudioIntent.REPLACE, audio_bytes=MP3
        )
    )
    assert result is None
    assert rig.media == {managed_name(item_id): MP3}
    assert len(collection.notes) == 1
    assert {card.ord: card.deck for card in collection.cards.values()} == expected_decks(
        language, wire
    )


@pytest.mark.p0
@pytest.mark.parametrize("action", ["storeMediaFile", "retrieveMediaFile"])
def test_prefix_guard_refuses_foreign_audio_before_transport(action):
    from language_lab.adapters.anki.client import AnkiConnectClient
    from language_lab.adapters.anki.guard import PrefixGuard, PrefixViolation
    from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay

    replay = AnkiConnectReplay()
    client = AnkiConnectClient(ANKI_URL, guard=PrefixGuard(MANIFEST), transport=replay.transport)
    params = {"filename": managed_name(str(uuid.uuid4()), prefix="Foreign")}
    if action == "storeMediaFile":
        params["data"] = ""
    result = settle(client.invoke(action, **params))
    assert isinstance(result, PrefixViolation)
    assert replay.sent == []
