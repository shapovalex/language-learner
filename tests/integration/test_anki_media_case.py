"""Managed media names are lowercase, because real Anki lowercases them (spike 2.2).

`anki/storeMediaFile.json` is the recorded reply: AnkiConnect stored `LLProbe_probe.mp3` as
`llprobe_probe.mp3`. The MediaRig's `storeMediaFile` answers the same way.
"""

import json
import uuid
from pathlib import Path

import pytest

from language_lab.domain.catalog import Category, Language
from tests.support.aio import settle
from tests.support.anki_state import Collection, item_note, managed_collection, sent_writes
from tests.support.audio import MP3, SECOND_MP3, MediaRig, remove_audio, replace_audio
from tests.support.captures import DEV, DEV_MANIFEST, MANIFEST, PREFIX, code_of
from tests.support.items import VOCABULARY, stored_fields

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "anki" / "storeMediaFile.json"


def _audio_of(collection: Collection) -> str:
    (note,) = collection.notes.values()
    return note.fields["Audio"]


@pytest.mark.p0
def test_the_recorded_store_reply_lowercases_the_requested_name() -> None:
    """The rule the MediaRig replays is the one real Anki showed."""
    recorded = json.loads(RECORDED.read_text())
    requested = recorded["request"]["params"]["filename"]

    assert requested != requested.lower()
    assert recorded["response"] == {"result": requested.lower(), "error": None}


@pytest.mark.p0
def test_a_mixed_case_prefix_saves_plays_replaces_removes_and_deletes() -> None:
    """Prefix `LanguageLabDev`, a replay that lowercases: a Draft and then an existing Item
    save new audio, and playback, replacement cleanup, removal and Item delete all work.
    """
    collection = managed_collection(DEV_MANIFEST, reading_rules=False)
    rig = MediaRig(collection, manifest=DEV_MANIFEST)
    item_id = str(uuid.uuid4())

    # A Draft saves with a clip.
    assert settle(replace_audio(rig.store, item_id, MP3)) is None
    (first,) = rig.media
    assert first.startswith(f"languagelabdev_{item_id}_")
    assert _audio_of(collection) == f"[sound:{first}]"
    assert settle(rig.store.get_media(first)) == MP3

    # The existing Item saves a new clip; the old one goes after the note write.
    assert settle(replace_audio(rig.store, item_id, SECOND_MP3)) is None
    (second,) = rig.media
    assert second != first and second.startswith(f"languagelabdev_{item_id}_")
    assert _audio_of(collection) == f"[sound:{second}]"
    assert settle(rig.store.get_media(second)) == SECOND_MP3

    # Remove audio empties the field and deletes the clip.
    assert settle(remove_audio(rig.store, item_id)) is None
    assert _audio_of(collection) == ""
    assert rig.media == {}

    # Item delete removes the clip saved since.
    assert settle(replace_audio(rig.store, item_id, MP3)) is None
    assert settle(rig.store.delete_item(Language.EN, item_id)) is None
    assert collection.notes == {}
    assert rig.media == {}
    assert not any(name.startswith(f"languagelabdev_{item_id}_") for name in collection.media)


@pytest.mark.p0
def test_an_existing_item_without_audio_saves_a_new_clip() -> None:
    collection = managed_collection(DEV_MANIFEST, reading_rules=False)
    item_id = str(uuid.uuid4())
    model = DEV_MANIFEST.item_note_type(Language.EN, Category.VOCABULARY)
    item_note(collection, DEV_MANIFEST, model, item_id, stored_fields(VOCABULARY, item_id))
    rig = MediaRig(collection, manifest=DEV_MANIFEST)

    assert settle(replace_audio(rig.store, item_id, MP3)) is None

    assert sent_writes(rig.replay.sent) == ["storeMediaFile", "updateNoteFields"]
    (name,) = rig.media
    assert _audio_of(collection) == f"[sound:{name}]"
    assert name == name.lower()


@pytest.mark.p0
@pytest.mark.parametrize("rename", [str.upper, lambda name: name.replace(".mp3", "-1.mp3")])
def test_a_store_answer_other_than_the_requested_name_fails_with_no_note_write(rename) -> None:
    """A real rename by Anki still fails safely; the leftover is a Setup repair."""
    collection = managed_collection(MANIFEST, reading_rules=False)

    def store_renamed(body):
        return {"result": rename(body["params"]["filename"]), "error": None}

    rig = MediaRig(collection, replies={"storeMediaFile": store_renamed})

    outcome = settle(replace_audio(rig.store, str(uuid.uuid4())))

    assert code_of(outcome) == "anki_unavailable"
    assert sent_writes(rig.replay.sent) == ["storeMediaFile"]
    assert collection.notes == {}


@pytest.mark.p1
@pytest.mark.parametrize(
    ("manifest", "other"), [(MANIFEST, DEV), (DEV_MANIFEST, PREFIX)], ids=["release", "dev"]
)
def test_a_mixed_case_name_or_the_other_prefix_is_not_served(manifest, other) -> None:
    item_id = str(uuid.uuid4())
    digest = "a" * 12
    mixed = f"{manifest.prefix}_{item_id}_{digest}.mp3"
    foreign = f"{other.lower()}_{item_id}_{digest}.mp3"
    rig = MediaRig(
        managed_collection(manifest, reading_rules=False),
        media={mixed: MP3, foreign: MP3},
        manifest=manifest,
    )

    for name in (mixed, foreign):
        assert code_of(settle(rig.store.get_media(name))) == "not_found"
    assert sent_writes(rig.replay.sent) == []
    assert "retrieveMediaFile" not in [s.body["action"] for s in rig.replay.sent]
