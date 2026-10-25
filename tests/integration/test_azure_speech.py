"""Story 6.1 Azure REST adapter: one primary RED leaf for synthesis and fresh locale Voices.

Fixtures are documented synthetic examples, not a captured subscription catalog.
Proposed interface: adapters.azure.AzureSpeech(key, region, transport=...),
voices(locales) -> list[Voice], synthesize(locale, voice, target) -> MP3 bytes.
"""

from xml.etree import ElementTree

import httpx
import pytest

from tests.support.aio import settle
from tests.support.audio import AZURE_KEY, EN_VOICE, FR_FR_VOICE, FR_VOICE, MP3
from tests.support.azure import AzureReplay, catalog, synthesize, voice_transition


class TestAzureSpeech:
    @pytest.mark.p1
    def test_synthesis_returns_the_azure_mp3_and_escapes_ssml(self) -> None:
        """[P1] AC-1 selected Voice and escaped Target reach Azure REST with backend credentials."""
        # Given a raw Target with XML metacharacters and a byte-exact Azure reply.
        target = 'Say <wait> & "think" before concluding.'
        replay = AzureReplay(
            [httpx.Response(200, content=MP3, headers={"content-type": "audio/mpeg"})]
        )

        # When the real adapter synthesizes (a missing future adapter is observed as RED).
        outcome = settle(synthesize(replay, target))

        # Then the newly promised result is the exact returned clip, before secondary checks.
        assert outcome == MP3
        (sent,) = replay.sent
        assert sent.method == "POST"
        assert str(sent.url).endswith("/cognitiveservices/v1")
        assert sent.url.host == "eastus.tts.speech.microsoft.com"
        assert sent.headers["ocp-apim-subscription-key"] == AZURE_KEY
        assert sent.headers["content-type"].split(";")[0] == "application/ssml+xml"
        assert sent.headers["x-microsoft-outputformat"].endswith("-mono-mp3")
        assert 0 < len(sent.headers["user-agent"]) < 255
        document = ElementTree.fromstring(sent.content)
        assert document.attrib["{http://www.w3.org/XML/1998/namespace}lang"] == "en-US"
        voice = next(
            element for element in document.iter() if element.tag.rsplit("}", 1)[-1] == "voice"
        )
        assert voice.attrib["name"] == EN_VOICE
        assert "".join(voice.itertext()) == target
        assert list(voice) == []
        assert AZURE_KEY.encode() not in sent.content

    @pytest.mark.p1
    def test_each_voice_read_filters_the_new_current_catalog(self) -> None:
        """[P1] AC-2 a changed catalog replaces the previous locale-filtered Voice list."""
        # Given an initial mixed-locale catalog and a changed catalog on the next read.
        before = catalog()
        new_fr = {
            **next(v for v in before if v["Locale"] == "fr-CA"),
            "ShortName": "fr-CA-TestReplacementNeural",
            "DisplayName": "Replacement",
        }
        after = [new_fr, next(v for v in before if v["Locale"] == "en-US")]
        replay = AzureReplay([httpx.Response(200, json=before), httpx.Response(200, json=after)])

        # When the same adapter reads the same locale twice across a provider change.
        outcome = settle(voice_transition(replay, ("fr-CA",)))
        latest = None if isinstance(outcome, Exception) else [v.name for v in outcome[1]]

        # Then the first assertion isolates the new catalog value, not merely a static list.
        assert latest == [new_fr["ShortName"]]
        assert [voice.name for voice in outcome[0]] == [FR_VOICE]
        assert [voice.locale for voice in outcome[1]] == ["fr-CA"]
        assert [voice.display_name for voice in outcome[1]] == ["Replacement"]
        assert len(replay.sent) == 2
        assert all(request.method == "GET" for request in replay.sent)
        assert all(
            str(request.url).endswith("/cognitiveservices/voices/list") for request in replay.sent
        )
        assert all(
            request.headers["ocp-apim-subscription-key"] == AZURE_KEY for request in replay.sent
        )


@pytest.mark.p1
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, text="secret credential or target"),
        httpx.Response(429, text="private response"),
        httpx.Response(200, content=b"invalid MP3"),
    ],
)
def test_synthesis_upstream_failures_have_only_the_fixed_error(response):
    from language_lab.domain.errors import AppError, ErrorCode

    replay = AzureReplay([response])
    result = settle(synthesize(replay, "private input"))
    assert isinstance(result, AppError)
    assert result.code is ErrorCode.TTS_FAILED
    assert str(result) == "Speech synthesis failed."


@pytest.mark.p1
def test_catalog_excludes_non_neural_and_non_exact_locales():
    rows = catalog()
    en = next(row for row in rows if row["Locale"] == "en-US")
    rows += [{**en, "VoiceType": "Standard"}, {**en, "Locale": "en-CA"}]
    replay = AzureReplay([httpx.Response(200, json=rows), httpx.Response(200, json=rows)])
    result = settle(voice_transition(replay, ("en-US",)))
    assert [voice.name for voice in result[0]] == [EN_VOICE]
    assert all(0 < request.extensions["timeout"]["read"] <= 30 for request in replay.sent)


@pytest.mark.p1
def test_french_catalog_is_one_read_of_canada_then_france_voices():
    """The French list holds both locales in locale order, though the reply lists France first."""
    rows = catalog()
    fr_fr = next(row for row in rows if row["Locale"] == "fr-FR")
    rows += [{**fr_fr, "Locale": "fr-BE", "ShortName": "fr-BE-TestNeural"}]
    replay = AzureReplay([httpx.Response(200, json=rows), httpx.Response(200, json=rows)])
    result = settle(voice_transition(replay, ("fr-CA", "fr-FR")))
    assert [(voice.name, voice.locale) for voice in result[0]] == [
        (FR_VOICE, "fr-CA"),
        (FR_FR_VOICE, "fr-FR"),
    ]
    assert len(replay.sent) == 2  # one GET per read: voice_transition reads twice


@pytest.mark.p1
def test_transport_timeout_is_tts_failed_without_the_upstream_message():
    from language_lab.adapters.azure import AzureSpeech
    from language_lab.domain.errors import AppError, ErrorCode

    def fail(request):
        raise httpx.ReadTimeout("secret provider response", request=request)

    async def run():
        speech = AzureSpeech(AZURE_KEY, "eastus", transport=httpx.MockTransport(fail))
        try:
            return await speech.voices(("en-US",))
        finally:
            await speech.aclose()

    result = settle(run())
    assert isinstance(result, AppError)
    assert result.code is ErrorCode.TTS_FAILED
    assert str(result) == "Speech synthesis failed."
