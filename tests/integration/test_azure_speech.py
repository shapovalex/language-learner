"""Story 6.1 Azure REST adapter: one primary RED leaf for synthesis and fresh locale Voices.

Fixtures are documented synthetic examples, not a captured subscription catalog.
Proposed interface: adapters.azure.AzureSpeech(key, region, transport=...),
voices(locale) -> list[Voice], synthesize(locale, voice, target) -> MP3 bytes.
"""

from xml.etree import ElementTree

import httpx
import pytest

from tests.support.aio import settle
from tests.support.audio import AZURE_KEY, EN_VOICE, FR_VOICE, MP3
from tests.support.azure import AzureReplay, catalog, synthesize, voice_transition

pytestmark = pytest.mark.skip(
    reason="ATDD RED scaffold until story 6.1 Speech/Azure implementation"
)


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
        outcome = settle(voice_transition(replay, "fr-CA"))
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
