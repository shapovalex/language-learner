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

pytestmark = pytest.mark.skip(reason="Story 7.2 RED scaffold: activate when implementing Attempts")


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
