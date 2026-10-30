"""Story 6.2 remove-intent failure boundary through the real guarded adapter (AD-6, AD-3).

The prior note and clip stay untouched until the note write succeeds. A failure after that
write stops without rollback; a retry succeeds and Setup offers the leftover clip as an
opt-in orphanMedia repair rather than any inline compensation.
"""

import copy
import uuid

import pytest

from tests.support.aio import run, settle
from tests.support.anki_state import managed_collection, sent_writes
from tests.support.audio import (
    MP3,
    SECOND_MP3,
    MediaRig,
    managed_name,
    remove_audio,
    replace_audio,
    stored_with_audio,
)
from tests.support.captures import MANIFEST, code_of

FAILED = {"result": None, "error": "collection unavailable"}


class TestAudioRemovalFailures:
    @pytest.mark.p0
    def test_failed_note_write_during_removal_keeps_the_field_and_clip(self) -> None:
        """[P0] AC-7 a refused note write stops removal before any media deletion."""
        # Given a stored Item and clip; Anki rejects the note update.
        collection = managed_collection(MANIFEST, reading_rules=False)
        item_id = str(uuid.uuid4())
        old_name = stored_with_audio(collection, item_id, SECOND_MP3)
        before_notes = copy.deepcopy(collection.notes)
        before_cards = copy.deepcopy(collection.cards)
        rig = MediaRig(
            collection, media={old_name: SECOND_MP3}, replies={"updateNoteFields": FAILED}
        )

        # When removal is saved through the real adapter.
        outcome = settle(remove_audio(rig.store, item_id))

        # Then the note write's failure is reported (not a refused intent) and nothing follows.
        assert code_of(outcome) == "anki_unavailable"
        assert sent_writes(rig.replay.sent) == ["updateNoteFields"]
        assert collection.notes == before_notes
        assert collection.cards == before_cards
        assert rig.media == {old_name: SECOND_MP3}
        assert rig.lock.holds == 1
        assert rig.lock.depth == 0

    @pytest.mark.p0
    def test_cleanup_failure_after_the_note_write_is_retryable_and_setup_repairable(
        self,
    ) -> None:
        """[P0] AC-8 failed clip cleanup reports, keeps the note write, retries, then repairs."""
        # Given a stored Item and clip; Anki refuses only the media deletion.
        collection = managed_collection(MANIFEST, reading_rules=False)
        item_id = str(uuid.uuid4())
        old_name = stored_with_audio(collection, item_id, SECOND_MP3)
        rig = MediaRig(
            collection, media={old_name: SECOND_MP3}, replies={"deleteMediaFile": FAILED}
        )

        # When removal is saved, then retried with the same intent.
        first = settle(remove_audio(rig.store, item_id))

        # Then the cleanup failure is reported after the successful note write.
        assert code_of(first) == "anki_unavailable"
        assert sent_writes(rig.replay.sent) == ["updateNoteFields", "deleteMediaFile"]
        (note,) = collection.notes.values()
        assert note.fields["Audio"] == ""  # the note write stands: no rollback
        assert old_name in collection.media
        assert rig.media == {old_name: SECOND_MP3}
        retry = settle(remove_audio(rig.store, item_id))
        assert retry is None
        assert sent_writes(rig.replay.sent) == [
            "updateNoteFields",
            "deleteMediaFile",
            "updateNoteFields",
        ]
        assert rig.lock.holds == 2
        assert rig.lock.depth == 0
        preview = run(rig.store.setup_preview())
        assert {row.key for row in preview.repairs} == {f"orphanMedia:{old_name}"}


class TestAudioReplacementCleanupFailure:
    @pytest.mark.p0
    def test_replace_cleanup_failure_is_retryable_and_setup_repairable(self) -> None:
        """[P0] AC-8 replace: failed old-clip cleanup reports, the note stands, retry succeeds."""
        collection = managed_collection(MANIFEST, reading_rules=False)
        item_id = str(uuid.uuid4())
        old_name = stored_with_audio(collection, item_id, SECOND_MP3)
        new_name = managed_name(item_id, MP3)
        rig = MediaRig(
            collection, media={old_name: SECOND_MP3}, replies={"deleteMediaFile": FAILED}
        )

        first = settle(replace_audio(rig.store, item_id, MP3))

        assert code_of(first) == "anki_unavailable"
        assert sent_writes(rig.replay.sent) == [
            "storeMediaFile",
            "updateNoteFields",
            "deleteMediaFile",
        ]
        (note,) = collection.notes.values()
        assert note.fields["Audio"] == f"[sound:{new_name}]"  # no rollback
        assert rig.media == {old_name: SECOND_MP3, new_name: MP3}
        retry = settle(replace_audio(rig.store, item_id, MP3))
        assert retry is None
        assert sent_writes(rig.replay.sent)[3:] == ["storeMediaFile", "updateNoteFields"]
        assert rig.media[new_name] == MP3
        assert rig.lock.holds == 2
        assert rig.lock.depth == 0
        preview = run(rig.store.setup_preview())
        assert {row.key for row in preview.repairs} == {f"orphanMedia:{old_name}"}
