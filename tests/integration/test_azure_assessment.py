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


@pytest.mark.parametrize("status", [401, 429, 500])
def test_provider_http_errors_redact_the_response(status):
    from language_lab.domain.errors import AppError, ErrorCode

    replay = AzureReplay([httpx.Response(status, text="private Target and subscription details")])
    outcome = settle(assess_wire(replay, locale="en-US", target="private Target"))
    assert isinstance(outcome, AppError)
    assert outcome.code == ErrorCode.ASSESSMENT_FAILED
    assert str(outcome) == "Pronunciation assessment failed."


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"NBest": []},
        {"RecognitionStatus": "NoMatch"},
        {"RecognitionStatus": "Success", "NBest": [{"Words": []}]},
    ],
)
def test_malformed_or_empty_provider_reply_is_unusable(payload):
    from language_lab.domain.errors import AppError, ErrorCode

    replay = AzureReplay([httpx.Response(200, json=payload)])
    outcome = settle(assess_wire(replay, locale="en-US", target="thought"))
    assert isinstance(outcome, AppError)
    assert outcome.code == ErrorCode.ASSESSMENT_FAILED


def test_timeout_has_the_fixed_assessment_failure():
    from language_lab.adapters.azure import AzureSpeech
    from language_lab.domain.errors import AppError, ErrorCode

    def timeout(request):
        raise httpx.ReadTimeout("private provider details", request=request)

    async def run():
        speech = AzureSpeech(AZURE_KEY, AZURE_REGION, transport=httpx.MockTransport(timeout))
        try:
            return await speech.assess("en-US", "private target", wav_bytes())
        finally:
            await speech.aclose()

    outcome = settle(run())
    assert isinstance(outcome, AppError)
    assert outcome.code == ErrorCode.ASSESSMENT_FAILED
    assert "private" not in str(outcome)


@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ([], {"start": None, "middle": None, "end": None}),
        ([23], {"start": 23, "middle": None, "end": None}),
        ([81, 19], {"start": 81, "middle": 19, "end": None}),
        ([90, 70, 10], {"start": 90, "middle": 70, "end": 10}),
        ([90, 60, 40, 20], {"start": 60, "middle": 40, "end": 20}),
    ],
)
def test_french_short_words_preserve_empty_buckets_and_never_sound_names(scores, expected):
    reply = response_fixture(FR_REPLY)
    reply["NBest"][0]["Words"][0]["Phonemes"] = [
        {"Phoneme": "private-sound", "AccuracyScore": score} for score in scores
    ]
    replay = AzureReplay([httpx.Response(200, json=reply)])
    body = settle(assess_wire(replay, locale="fr-CA", target="bonjour"))
    assert body["words"][0]["positions"] == expected
    assert body["words"][0]["phonemes"] == []
    assert "private-sound" not in json.dumps(body)


@pytest.mark.parametrize("invalid_score", [-1, 101, "private score"])
def test_invalid_scores_fail_closed(invalid_score):
    from language_lab.domain.errors import AppError, ErrorCode

    reply = response_fixture(EN_REPLY)
    reply["NBest"][0]["Words"][0]["Phonemes"][0]["AccuracyScore"] = invalid_score
    replay = AzureReplay([httpx.Response(200, json=reply)])
    outcome = settle(assess_wire(replay, locale="en-US", target="thought"))
    assert isinstance(outcome, AppError)
    assert outcome.code == ErrorCode.ASSESSMENT_FAILED
