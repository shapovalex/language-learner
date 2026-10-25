"""Story 6.1 Draft audio HTTP contracts through the real app and guarded Anki adapter.

Proposed new contracts: GET /api/audio/voices?locale=en-US returns
{voices:[{name,locale,displayName}]}; POST /api/audio/preview takes
{language,voice,target} and returns MP3 bytes. Save extends the existing item multipart
with audioFile when audio=replace; Item reads add audio: managed filename | null.
"""

import base64
import copy
import uuid
from pathlib import Path

import pytest

from language_lab.domain.errors import ErrorCode
from tests.fakes.speech import FakeSpeech
from tests.support.anki_state import item_note, managed_collection, sent_writes
from tests.support.audio import (
    AZURE_KEY,
    AZURE_REGION,
    EN_VOICE,
    MP3,
    PREVIEW_API,
    VOICES_API,
    MediaRig,
    audio_client,
    managed_name,
    preview_body,
    replace_parts,
)
from tests.support.captures import MANIFEST
from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory
from tests.support.item_delete import action_bodies
from tests.support.items import VOCABULARY, note_type_of, stored_fields


def _settings(settings_factory: SettingsFactory):
    return settings_factory(
        anki_prefix=MANIFEST.prefix,
        azure_speech_key=AZURE_KEY,
        azure_speech_region=AZURE_REGION,
    )


class TestReferenceAudio:
    @pytest.mark.p0
    def test_preview_returns_memory_only_mp3_without_anki_writes(
        self, settings_factory: SettingsFactory, tmp_path: Path
    ) -> None:
        """[P0] AC-4 Preview returns uncached MP3 and leaves Anki and local files unchanged."""
        # Given a ready collection, a fake Speech port, and the normal composition root.
        collection = managed_collection(MANIFEST)
        rig, speech = MediaRig(collection), FakeSpeech()
        before = copy.deepcopy(collection)
        client = audio_client(_settings(settings_factory), rig.store, speech)
        files_before = {
            p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
        }
        voices = client.get(VOICES_API, params={"locale": "en-US"})  # opaque setup read

        # When the user explicitly asks for Preview.
        response = client.post(PREVIEW_API, json=preview_body())

        # Then the new endpoint succeeds before any ancillary schema/retention checks.
        assert response.status_code == 200
        assert response.content == MP3
        assert response.headers["content-type"].split(";")[0] == "audio/mpeg"
        assert "no-store" in response.headers["cache-control"]
        assert "location" not in response.headers
        assert speech.requests == [("en-US", EN_VOICE, VOCABULARY["target"])]
        assert collection == before
        assert rig.media == {}
        assert sent_writes(rig.replay.sent) == []
        assert {
            p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
        } == files_before
        assert voices.json() == {
            "voices": [{"name": EN_VOICE, "locale": "en-US", "displayName": "Andrew"}]
        }

    @pytest.mark.p0
    def test_save_uploads_the_exact_preview_and_playback_returns_the_same_bytes(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P0] AC-6 accepted Preview bytes survive multipart Save and managed playback exactly."""
        # Given known fake synthesis bytes; the Preview setup response remains opaque.
        collection = managed_collection(MANIFEST)
        rig, speech = MediaRig(collection), FakeSpeech()
        client = audio_client(_settings(settings_factory), rig.store, speech)
        item_id = str(uuid.uuid4())
        expected_name = managed_name(item_id)
        preview = client.post(PREVIEW_API, json=preview_body())

        # When Use preview's candidate is uploaded as audioFile, with audio=replace.
        saved = client.post("/api/items/en", files=replace_parts(item_id, MP3))

        # Then the uploaded bytes are the first criterion-bearing property checked.
        assert rig.media.get(expected_name) == MP3
        assert saved.status_code == 200
        assert saved.json() == {"itemId": item_id}
        assert preview.status_code == 200
        assert preview.content == MP3
        played = client.get(f"/api/media/{expected_name}")
        assert played.status_code == 200
        assert played.content == preview.content
        assert len(speech.requests) == 1  # Save must not synthesize a second time.
        (note,) = collection.notes.values()
        assert note.fields["Audio"] == f"[sound:{expected_name}]"

    @pytest.mark.p0
    def test_save_computes_the_managed_name_from_received_bytes(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P0] AC-7 backend naming ignores the client-chosen upload filename."""
        # Given a valid ItemId and an upload named outside the managed Prefix.
        rig = MediaRig(managed_collection(MANIFEST))
        client = audio_client(_settings(settings_factory), rig.store, FakeSpeech())
        item_id = str(uuid.uuid4())

        # When Save receives the accepted clip with an untrusted multipart filename.
        response = client.post("/api/items/en", files=replace_parts(item_id))
        stores = [body for body in action_bodies(rig.replay) if body["action"] == "storeMediaFile"]

        # Then only the backend-computed name reaches Anki.
        assert [body["params"]["filename"] for body in stores] == [managed_name(item_id)]
        assert response.status_code == 200
        assert base64.b64decode(stores[0]["params"]["data"], validate=True) == MP3
        assert set(rig.media) == {managed_name(item_id)}

    @pytest.mark.p0
    def test_media_route_plays_managed_audio_and_refuses_foreign_names(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P0] AC-9 managed playback works and rejected names never reach Anki media reads."""
        # Given a saved valid managed filename and clip.
        item_id = str(uuid.uuid4())
        name = managed_name(item_id)
        rig = MediaRig(managed_collection(MANIFEST), media={name: MP3})
        client = audio_client(_settings(settings_factory), rig.store, FakeSpeech())

        # When the browser asks the sole stored-audio route to play it.
        response = client.get(f"/api/media/{name}")

        # Then a valid managed request succeeds before the guard's negative branches.
        assert response.status_code == 200
        assert response.content == MP3
        assert response.headers["content-type"].split(";")[0] == "audio/mpeg"
        reads = [
            body for body in action_bodies(rig.replay) if body["action"] == "retrieveMediaFile"
        ]
        assert [body["params"]["filename"] for body in reads] == [name]
        sent_before = len(rig.replay.sent)
        for rejected in [
            "foreign.mp3",
            managed_name(item_id, prefix="LanguageLabDev"),
            f"LanguageLab_{item_id}_abc.mp3",
        ]:
            refused = client.get(f"/api/media/{rejected}")
            assert refused.status_code == 404
        assert len(rig.replay.sent) == sent_before

    @pytest.mark.p1
    def test_item_detail_exposes_the_saved_reference_filename(
        self, settings_factory: SettingsFactory
    ) -> None:
        """[P1] AC-10 Item read exposes the persisted managed reference for later playback."""
        # Given an already-stored note, independent of the future replace endpoint.
        collection = managed_collection(MANIFEST)
        item_id = str(uuid.uuid4())
        name = managed_name(item_id)
        fields = {**stored_fields(VOCABULARY, item_id), "Audio": f"[sound:{name}]"}
        item_note(collection, MANIFEST, note_type_of("en", VOCABULARY), item_id, fields)
        rig = MediaRig(collection, media={name: MP3})
        client = audio_client(_settings(settings_factory), rig.store, FakeSpeech())

        # When the existing Item detail endpoint re-reads Anki.
        response = client.get(f"/api/items/en/{item_id}")

        # Then the newly promised scalar is checked before the established read contract.
        assert response.json().get("audio") == name
        assert response.status_code == 200
        assert response.json()["itemId"] == item_id
        assert response.json()["target"] == VOCABULARY["target"]
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p0
    def test_failed_audio_request_has_a_safe_envelope_and_content_free_logs(
        self, settings_factory: SettingsFactory, log_capture: LogCapture
    ) -> None:
        """[P0] AC-16 failed Preview has a typed envelope without credentials or user content."""
        # Given a successful binary request followed by a failing Speech-port call.
        rig, speech = MediaRig(managed_collection(MANIFEST)), FakeSpeech()
        client = audio_client(_settings(settings_factory), rig.store, speech)
        private_target = "private-target-do-not-log-6-1"
        client.post(PREVIEW_API, json=preview_body(target=private_target))  # opaque setup
        speech.error = ErrorCode.TTS_FAILED

        # When Preview fails through the existing domain-error path.
        response = client.post(PREVIEW_API, json=preview_body(target=private_target))

        # Then the promised error status owns RED before inspecting the envelope.
        assert response.status_code == 502
        error = response.json()["error"]
        assert error["code"] == "tts_failed"
        assert set(error) == {"code", "message", "requestId"}
        assert error["message"] == "Speech synthesis failed."
        assert error["requestId"]
        assert len(log_capture.request_lines) == 2
        assert log_capture.request_lines[-1]["code"] == "tts_failed"
        exposed = response.text + log_capture.all_text
        for sentinel in [AZURE_KEY, private_target, base64.b64encode(MP3).decode(), repr(MP3)]:
            assert sentinel not in exposed
        assert MP3 not in response.content
        assert sent_writes(rig.replay.sent) == []


@pytest.mark.p1
@pytest.mark.parametrize("locale", ["en-CA", "fr-FR", "en", ""])
def test_voice_catalog_rejects_unsupported_locales(settings_factory, locale):
    speech = FakeSpeech()
    rig = MediaRig(managed_collection(MANIFEST))
    client = audio_client(_settings(settings_factory), rig.store, speech)
    response = client.get(VOICES_API, params={"locale": locale})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert speech.voice_requests == []


@pytest.mark.p1
@pytest.mark.parametrize(
    "overrides",
    [
        {"language": "de"},
        {"voice": ""},
        {"voice": "en-US-RetiredNeural"},
        {"voice": "fr-CA-SylvieNeural"},
        {"target": " \n\t"},
    ],
)
def test_invalid_preview_never_synthesizes_or_writes(settings_factory, overrides):
    speech = FakeSpeech()
    rig = MediaRig(managed_collection(MANIFEST))
    response = audio_client(_settings(settings_factory), rig.store, speech).post(
        PREVIEW_API, json=preview_body(**overrides)
    )
    assert response.status_code == 422
    assert speech.requests == []
    assert rig.replay.sent == []


@pytest.mark.p0
@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not MP3",
        b"ID3bad",
        MP3[:-1],
        pytest.param(b"\xff\xfb\x90\x02" + b"\xff" * 413, id="reserved-emphasis"),
    ],
)
def test_invalid_audio_upload_stops_before_anki(settings_factory, data):
    rig = MediaRig(managed_collection(MANIFEST))
    client = audio_client(_settings(settings_factory), rig.store, FakeSpeech())
    response = client.post("/api/items/en", files=replace_parts(str(uuid.uuid4()), data))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert rig.replay.sent == []


@pytest.mark.p0
def test_audio_larger_than_five_megabytes_returns_413(settings_factory):
    rig = MediaRig(managed_collection(MANIFEST))
    client = audio_client(_settings(settings_factory), rig.store, FakeSpeech())
    response = client.post(
        "/api/items/en", files=replace_parts(str(uuid.uuid4()), b"x" * (5 * 1024 * 1024 + 1))
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert rig.replay.sent == []


@pytest.mark.p0
@pytest.mark.parametrize(
    "intent,file_present", [("keep", True), ("replace", False), ("remove", True)]
)
def test_inconsistent_audio_parts_are_rejected(settings_factory, intent, file_present):
    rig = MediaRig(managed_collection(MANIFEST))
    parts = replace_parts(str(uuid.uuid4()), audio=intent)
    if not file_present:
        parts.pop("audioFile")
    client = audio_client(_settings(settings_factory), rig.store, FakeSpeech())
    response = client.post("/api/items/en", files=parts)
    assert response.status_code == 422
    assert rig.replay.sent == []


@pytest.mark.p0
@pytest.mark.parametrize("state", ["needs_setup", "needs_migration", "newer_schema"])
def test_replace_is_setup_gated_but_media_reads_remain_available(settings_factory, state):
    name = managed_name(str(uuid.uuid4()))
    rig = MediaRig(managed_collection(MANIFEST), state=state, media={name: MP3})
    client = audio_client(_settings(settings_factory), rig.store, FakeSpeech())
    saved = client.post("/api/items/en", files=replace_parts(str(uuid.uuid4())))
    assert saved.status_code == 409
    assert saved.json()["error"]["code"] == "setup_required"
    assert sent_writes(rig.replay.sent) == []
    assert client.get(f"/api/media/{name}").content == MP3


@pytest.mark.p0
@pytest.mark.parametrize("value,status", [(False, 404), ("not base64!", 503), (None, 503)])
def test_missing_or_malformed_anki_media_fails_safely(settings_factory, value, status):
    name = managed_name(str(uuid.uuid4()))
    rig = MediaRig(
        managed_collection(MANIFEST),
        replies={"retrieveMediaFile": {"result": value, "error": None}},
    )
    response = audio_client(_settings(settings_factory), rig.store, FakeSpeech()).get(
        f"/api/media/{name}"
    )
    assert response.status_code == status
    assert "error" in response.json()
    assert rig.lock.holds == 1


@pytest.mark.p1
def test_voice_provider_failure_uses_safe_retryable_envelope(settings_factory, monkeypatch):
    from language_lab.domain.errors import AppError

    async def fail(locale):
        raise AppError(ErrorCode.TTS_FAILED)

    speech = FakeSpeech()
    monkeypatch.setattr(speech, "voices", fail)
    rig = MediaRig(managed_collection(MANIFEST))
    response = audio_client(_settings(settings_factory), rig.store, speech).get(
        VOICES_API, params={"locale": "en-US"}
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "tts_failed"
    assert rig.replay.sent == []
