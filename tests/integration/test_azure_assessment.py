"""Story 7.2 RED: real flat Azure NBest replies replayed through the future REST assess().

No SDK or live credentials. Unknown production imports and missing methods are returned
from settle(), so the criterion's first assertion owns the failure instead of collection.
"""

import base64
import json

import httpx
import pytest

from tests.support.aio import settle
from tests.support.assessment import (
    EN_REPLY,
    FR_REPLY,
    SILENCE_REPLY,
    assess_wire,
    assessment_wire,
    response_fixture,
    wav_bytes,
)
from tests.support.audio import AZURE_KEY, AZURE_REGION
from tests.support.azure import AzureReplay

pytestmark = pytest.mark.skip(reason="Story 7.2 RED scaffold: activate with Azure assessment")


class TestAzureAssessment:
    @pytest.mark.p0
    def test_english_flat_nbest_reply_keeps_ipa_and_prosody(self):
        """[P0] AC-7 English REST Assessment keeps the real scores, IPA and prosody."""
        replay = AzureReplay([httpx.Response(200, json=response_fixture(EN_REPLY))])

        outcome = settle(assess_wire(replay, locale="en-US", target="thought"))
        body = {} if isinstance(outcome, Exception) else outcome

        assert body.get("overall") == 79.2
        assert body == assessment_wire()
        (sent,) = replay.sent
        assert sent.method == "POST"
        assert sent.url.host == f"{AZURE_REGION}.stt.speech.microsoft.com"
        assert sent.url.path == "/speech/recognition/conversation/cognitiveservices/v1"
        assert dict(sent.url.params) == {"language": "en-US", "format": "detailed"}
        assert sent.headers["ocp-apim-subscription-key"] == AZURE_KEY
        assert sent.headers["content-type"] == "audio/wav; codecs=audio/pcm; samplerate=16000"
        header = json.loads(base64.b64decode(sent.headers["pronunciation-assessment"]))
        assert header == {
            "ReferenceText": "thought",
            "GradingSystem": "HundredMark",
            "Granularity": "Phoneme",
            "Dimension": "Comprehensive",
            "EnableMiscue": True,
            "PhonemeAlphabet": "IPA",
            "EnableProsodyAssessment": True,
        }
        assert sent.content == wav_bytes()
        assert 0 < sent.extensions["timeout"]["read"] <= 30

    @pytest.mark.p0
    def test_french_empty_phoneme_labels_become_positions_only(self):
        """[P0] AC-8 French phoneme order yields positions, with no named sound/prosody."""
        replay = AzureReplay([httpx.Response(200, json=response_fixture(FR_REPLY))])

        outcome = settle(assess_wire(replay, locale="fr-CA", target="bonjour"))
        body = {} if isinstance(outcome, Exception) else outcome
        positions = body.get("words", [{}])[0].get("positions")

        # Explicit scaffold choice: floor(3*i/n) thirds, minimum score per position.
        assert positions == {"start": 17.0, "middle": 0.0, "end": 0.0}
        assert body == assessment_wire(locale="fr-CA")
        assert body["prosody"] is None
        assert body["words"][0]["phonemes"] == []
        (sent,) = replay.sent
        assert sent.url.params["language"] == "fr-CA"
        header = json.loads(base64.b64decode(sent.headers["pronunciation-assessment"]))
        assert header["ReferenceText"] == "bonjour"
        assert "EnableProsodyAssessment" not in header
        assert "PhonemeAlphabet" not in header

    @pytest.mark.p0
    def test_success_with_every_word_omitted_is_nothing_heard(self):
        """[P0] AC-9 HTTP 200 all-Omission returns no usable Assessment, not a failure."""
        replay = AzureReplay([httpx.Response(200, json=response_fixture(SILENCE_REPLY))])

        outcome = settle(assess_wire(replay, locale="en-US", target="What's the weather like?"))

        assert outcome is None
        assert len(replay.sent) == 1
