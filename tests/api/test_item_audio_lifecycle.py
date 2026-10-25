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
    SECOND_MP3,
    MediaRig,
    audio_client,
    remove_parts,
    stored_with_audio,
)
from tests.support.captures import MANIFEST
from tests.support.fixtures.settings import SettingsFactory

pytestmark = pytest.mark.skip(
    reason="ATDD red phase until story 6.2 existing-Item audio lifecycle is built"
)


class TestItemAudioRemoval:
    @pytest.mark.p0
    def test_remove_clears_the_audio_field_then_deletes_the_superseded_clip(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P0] AC-6 audio=remove empties Audio, then deletes the old clip, under one lock."""
        # Given a stored Item whose Audio field references its managed clip.
        collection = managed_collection(MANIFEST)
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
