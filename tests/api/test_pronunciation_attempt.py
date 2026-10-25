"""Story 7.2 RED: proposed multipart Attempt route, trusted Anki Target and privacy.

Provider endpoint: NEW POST /api/pronunciation/{lang}/attempt. itemId + recording only;
200 {assessment, nothingHeard}; 413 payload_too_large; 422 validation_failed for duration;
503 assessment_failed. The builder may rename the scaffold contracts with their helpers.
"""

import base64
import json

import pytest

from tests.support.anki_state import sent_actions, sent_writes
from tests.support.assessment import (
    ATTEMPT_API,
    MAX_ATTEMPT_BYTES,
    AttemptSpeech,
    assessment_wire,
    attempt_parts,
    attempt_rig,
    overlong_webm,
    sample,
    wav_properties,
)
from tests.support.audio import AZURE_KEY, AZURE_REGION, audio_client
from tests.support.captures import MANIFEST
from tests.support.fixtures.logs import LogCapture
from tests.support.fixtures.settings import SettingsFactory


def _client(settings_factory: SettingsFactory, rig, speech: AttemptSpeech):
    settings = settings_factory(
        anki_prefix=MANIFEST.prefix,
        azure_speech_key=AZURE_KEY,
        azure_speech_region=AZURE_REGION,
    )
    return audio_client(settings, rig.store, speech)


class TestAttemptRequest:
    @pytest.mark.p0
    def test_oversize_attempt_is_refused_before_assessment(self, settings_factory: SettingsFactory):
        """[P0] AC-4 more than 5 MB is payload_too_large before Azure is called."""
        rig, item_id = attempt_rig()
        speech = AttemptSpeech()
        recording = sample() + bytes(MAX_ATTEMPT_BYTES + 1 - len(sample()))
        client = _client(settings_factory, rig, speech)
        response = client.post(ATTEMPT_API, files=attempt_parts(item_id, recording))

        assert response.status_code == 413
        assert response.json()["error"]["code"] == "payload_too_large"
        assert speech.assessments == []
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p0
    def test_attempt_uses_the_target_read_from_anki_and_never_writes_it(
        self, settings_factory: SettingsFactory
    ):
        """[P0] AC-5 one Attempt reads the Item's trusted Target, with no Anki write."""
        rig, item_id = attempt_rig(target="thought")
        speech = AttemptSpeech()
        before = [(note.model, dict(note.fields)) for note in rig.collection.notes.values()]
        client = _client(settings_factory, rig, speech)

        # No Target or score is sent by the browser. The backend must obtain its reference.
        response = client.post(ATTEMPT_API, files=attempt_parts(item_id))
        trusted_target = speech.assessments[0]["target"] if speech.assessments else None

        assert trusted_target == "thought"
        assert response.status_code == 200
        assert response.json() == {"assessment": assessment_wire(), "nothingHeard": False}
        assert len(speech.assessments) == 1
        assert speech.assessments[0]["locale"] == "en-US"
        assert wav_properties(speech.assessments[0]["wav"])["sampleRate"] == 16_000
        assert "findNotes" in sent_actions(rig.replay.sent)
        assert "notesInfo" in sent_actions(rig.replay.sent)
        assert sent_writes(rig.replay.sent) == []
        assert [(note.model, dict(note.fields)) for note in rig.collection.notes.values()] == before

    @pytest.mark.p0
    def test_overlong_decoded_attempt_is_refused_before_azure(
        self, settings_factory: SettingsFactory
    ):
        """[P0] AC-17 a compressed 31-second Attempt is refused despite being below 5 MB."""
        rig, item_id = attempt_rig()
        speech = AttemptSpeech()
        client = _client(settings_factory, rig, speech)
        recording = overlong_webm()

        response = client.post(ATTEMPT_API, files=attempt_parts(item_id, recording, webm=True))

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_failed"
        assert len(recording) < MAX_ATTEMPT_BYTES
        assert speech.assessments == []
        assert sent_writes(rig.replay.sent) == []

    @pytest.mark.p0
    def test_attempt_success_and_failure_logs_exclude_audio_scores_and_target(
        self, settings_factory: SettingsFactory, log_capture: LogCapture
    ):
        """[P0] AC-18 the real Attempt success/failure path emits only content-free logs."""
        private_target = "private pronunciation target 7.2"
        rig, item_id = attempt_rig(target=private_target)
        speech = AttemptSpeech()
        client = _client(settings_factory, rig, speech)
        recording = sample()

        success = client.post(ATTEMPT_API, files=attempt_parts(item_id, recording))
        speech.assessment_error = True
        failure = client.post(ATTEMPT_API, files=attempt_parts(item_id, recording))

        # Prove the intended path ran before any negative privacy assertion can pass.
        assert [success.status_code, failure.status_code] == [200, 503]
        assert failure.json()["error"]["code"] == "assessment_failed"
        assert len(speech.assessments) == 2
        assert private_target not in log_capture.all_text
        assert base64.b64encode(recording).decode() not in log_capture.all_text
        assert repr(recording) not in log_capture.all_text
        assert json.dumps(assessment_wire()) not in log_capture.all_text
        assert all(
            word not in log_capture.all_text
            for word in ("AccuracyScore", "PronScore", '"overall"', '"phonemes"', '"score"')
        )
        assert [line["status"] for line in log_capture.request_lines] == [200, 503]


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_unknown_or_wrong_locale_item_is_not_assessed(settings_factory, lang):
    import uuid

    rig, item_id = attempt_rig()
    speech = AttemptSpeech()
    response = _client(settings_factory, rig, speech).post(
        f"/api/pronunciation/{lang}/attempt",
        files=attempt_parts(str(uuid.uuid4()) if lang == "en" else item_id),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert speech.assessments == []
    assert sent_writes(rig.replay.sent) == []


def test_exact_upload_limit_is_accepted_without_disk_spooling(settings_factory, monkeypatch):
    import builtins
    import tempfile

    rig, item_id = attempt_rig()
    speech = AttemptSpeech()
    client = _client(settings_factory, rig, speech)
    recording = sample() + bytes(MAX_ATTEMPT_BYTES - len(sample()))
    original_open = builtins.open

    def read_only_open(file, mode="r", *args, **kwargs):
        assert not any(flag in mode for flag in "wax+"), "Attempt wrote to disk"
        return original_open(file, mode, *args, **kwargs)

    def no_temporary_file(*args, **kwargs):
        raise AssertionError("Attempt spooled audio to disk")

    monkeypatch.setattr(builtins, "open", read_only_open)
    monkeypatch.setattr(tempfile, "SpooledTemporaryFile", no_temporary_file)
    monkeypatch.setattr(tempfile, "TemporaryFile", no_temporary_file)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", no_temporary_file)
    response = client.post(ATTEMPT_API, files=attempt_parts(item_id, recording))
    assert response.status_code == 200
    assert len(speech.assessments) == 1
    assert sent_writes(rig.replay.sent) == []


def test_nothing_heard_has_the_explicit_success_shape(settings_factory):
    rig, item_id = attempt_rig()
    speech = AttemptSpeech()

    async def silence(*args):
        return None

    speech.assess = silence
    response = _client(settings_factory, rig, speech).post(
        ATTEMPT_API, files=attempt_parts(item_id)
    )
    assert response.status_code == 200
    assert response.json() == {"assessment": None, "nothingHeard": True}
    assert sent_writes(rig.replay.sent) == []


@pytest.mark.parametrize("case", ["corrupt", "missing", "reference", "duplicate", "truncated"])
def test_invalid_multipart_or_audio_never_reaches_azure(settings_factory, case):
    rig, item_id = attempt_rig()
    speech = AttemptSpeech()
    client = _client(settings_factory, rig, speech)
    parts = list(attempt_parts(item_id).items())
    if case == "corrupt":
        parts = list(attempt_parts(item_id, b"private corrupt audio").items())
    elif case == "missing":
        parts.pop()
    elif case == "reference":
        parts.append(("target", (None, "untrusted reference")))
    elif case == "duplicate":
        parts.append(parts[0])
    if case == "truncated":
        response = client.post(
            ATTEMPT_API,
            content=b'--test\r\nContent-Disposition: form-data; name="itemId"\r\n\r\n',
            headers={"Content-Type": "multipart/form-data; boundary=test"},
        )
    else:
        response = client.post(ATTEMPT_API, files=parts)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert speech.assessments == []
    assert sent_writes(rig.replay.sent) == []
