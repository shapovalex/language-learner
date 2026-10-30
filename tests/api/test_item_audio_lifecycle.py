"""Story 6.2 existing-Item audio removal over HTTP through the real guarded Anki adapter.

Proposed contract: the existing multipart Save accepts audio=remove with only the `item` part
(no audioFile). AD-6 order skips media storage: update the note with an empty Audio field, then
delete the superseded managed clip. Item detail then reads `audio: null`.
"""

import uuid

import pytest

from tests.fakes.speech import FakeSpeech
from tests.support.anki_state import managed_collection, sent_writes
from tests.support.audio import (
    AZURE_KEY,
    AZURE_REGION,
    MP3,
    SECOND_MP3,
    MediaRig,
    audio_client,
    managed_name,
    remove_parts,
    replace_parts,
    stored_with_audio,
)
from tests.support.captures import MANIFEST
from tests.support.fixtures.settings import SettingsFactory


class TestItemAudioRemoval:
    @pytest.mark.p0
    def test_remove_clears_the_audio_field_then_deletes_the_superseded_clip(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P0] AC-6 audio=remove empties Audio, then deletes the old clip, under one lock."""
        # Given a stored Item whose Audio field references its managed clip.
        collection = managed_collection(MANIFEST, reading_rules=False)
        item_id = str(uuid.uuid4())
        old_name = stored_with_audio(collection, item_id, SECOND_MP3)
        rig = MediaRig(collection, media={old_name: SECOND_MP3})
        settings = settings_factory(
            anki_prefix=MANIFEST.prefix,
            azure_speech_key=AZURE_KEY,
            azure_speech_region=AZURE_REGION,
        )
        client = audio_client(settings, rig.store, FakeSpeech())

        # When Save changes commits the removal.
        response = client.post("/api/items/en", files=remove_parts(item_id))

        # Then the newly accepted intent succeeds before any ordering or state checks.
        assert response.status_code == 200
        assert response.json() == {"itemId": item_id}
        assert sent_writes(rig.replay.sent) == ["updateNoteFields", "deleteMediaFile"]
        (note,) = collection.notes.values()
        assert note.fields["Audio"] == ""
        assert note.fields["ItemId"] == item_id
        assert rig.media == {}
        assert rig.lock.holds == 1
        assert rig.lock.depth == 0
        assert set(rig.lock.request_depths) == {1}
        detail = client.get(f"/api/items/en/{item_id}")
        assert detail.status_code == 200
        assert detail.json()["audio"] is None
        assert client.get(f"/api/media/{old_name}").status_code == 404


def _client(settings_factory: SettingsFactory, rig: MediaRig):
    settings = settings_factory(
        anki_prefix=MANIFEST.prefix,
        azure_speech_key=AZURE_KEY,
        azure_speech_region=AZURE_REGION,
    )
    return audio_client(settings, rig.store, FakeSpeech())


class TestItemAudioRemovalMatrix:
    @pytest.mark.p1
    def test_remove_on_an_item_without_audio_writes_the_note_and_deletes_no_media(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P1] AC-6 remove on a stored Item with no clip only rewrites its note."""
        collection = managed_collection(MANIFEST, reading_rules=False)
        item_id = str(uuid.uuid4())
        stored_with_audio(collection, item_id, SECOND_MP3)
        (note,) = collection.notes.values()
        note.fields["Audio"] = ""
        rig = MediaRig(collection)

        response = _client(settings_factory, rig).post("/api/items/en", files=remove_parts(item_id))

        assert response.status_code == 200
        assert sent_writes(rig.replay.sent) == ["updateNoteFields"]
        assert note.fields["Audio"] == ""

    @pytest.mark.p1
    def test_remove_on_a_new_item_id_adds_the_note_with_empty_audio(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P1] AC-6 remove under a new ItemId adds the note and places cards, no media."""
        collection = managed_collection(MANIFEST, reading_rules=False)
        rig = MediaRig(collection)
        item_id = str(uuid.uuid4())

        response = _client(settings_factory, rig).post("/api/items/en", files=remove_parts(item_id))

        assert response.status_code == 200
        writes = sent_writes(rig.replay.sent)
        assert writes == ["addNote", "changeDeck", "changeDeck", "changeDeck"]
        assert "deleteMediaFile" not in writes
        assert "storeMediaFile" not in writes
        (note,) = collection.notes.values()
        assert note.fields["Audio"] == ""
        assert note.fields["ItemId"] == item_id

    @pytest.mark.p0
    def test_remove_with_an_audio_file_is_rejected_with_zero_writes(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P0] AC-4 remove plus an audioFile is 422 and writes nothing."""
        collection = managed_collection(MANIFEST, reading_rules=False)
        item_id = str(uuid.uuid4())
        old_name = stored_with_audio(collection, item_id, SECOND_MP3)
        rig = MediaRig(collection, media={old_name: SECOND_MP3})
        parts = {
            **remove_parts(item_id),
            "audioFile": ("preview.mp3", SECOND_MP3, "audio/mpeg"),
        }

        response = _client(settings_factory, rig).post("/api/items/en", files=parts)

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_failed"
        assert rig.replay.sent == []
        assert rig.media == {old_name: SECOND_MP3}

    @pytest.mark.p0
    @pytest.mark.parametrize("state", ["needs_setup", "needs_migration", "newer_schema"])
    def test_setup_gate_refuses_remove_before_any_write(
        self, settings_factory: SettingsFactory, state: str
    ) -> None:
        """[P0] AC-6 the Setup gate refuses remove; the note and clip stay."""
        collection = managed_collection(MANIFEST, reading_rules=False)
        item_id = str(uuid.uuid4())
        old_name = stored_with_audio(collection, item_id, SECOND_MP3)
        rig = MediaRig(collection, media={old_name: SECOND_MP3}, state=state)

        response = _client(settings_factory, rig).post("/api/items/en", files=remove_parts(item_id))

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "setup_required"
        assert sent_writes(rig.replay.sent) == []
        (note,) = collection.notes.values()
        assert note.fields["Audio"] == f"[sound:{old_name}]"
        assert rig.media == {old_name: SECOND_MP3}

    @pytest.mark.p1
    def test_has_audio_in_the_list_follows_replace_then_remove(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P1] AC-3/AC-4 the Items list's hasAudio follows the saved audio intent."""
        collection = managed_collection(MANIFEST, reading_rules=False)
        item_id = str(uuid.uuid4())
        old_name = stored_with_audio(collection, item_id, SECOND_MP3)
        rig = MediaRig(collection, media={old_name: SECOND_MP3})
        client = _client(settings_factory, rig)

        def has_audio() -> bool:
            (row,) = client.get("/api/items/en").json()["items"]
            return row["hasAudio"]

        assert has_audio() is True
        assert client.post("/api/items/en", files=replace_parts(item_id, MP3)).status_code == 200
        assert has_audio() is True
        new_name = managed_name(item_id, MP3)
        assert client.get(f"/api/items/en/{item_id}").json()["audio"] == new_name
        assert client.get(f"/api/media/{new_name}").content == MP3
        assert old_name not in rig.media
        assert client.post("/api/items/en", files=remove_parts(item_id)).status_code == 200
        assert has_audio() is False
        assert rig.media == {}
