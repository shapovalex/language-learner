"""Azure REST examples replayed through httpx; never a live service or a recorded catalog."""

import json
from collections.abc import Sequence
from typing import Any

import httpx

from tests.support.audio import AZURE_KEY, AZURE_REGION, FIXTURES

TTS_URL = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
VOICES_URL = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/voices/list"


def catalog() -> list[dict[str, Any]]:
    return json.loads((FIXTURES / "catalog-example.json").read_text())


class AzureReplay:
    def __init__(self, replies: Sequence[httpx.Response]) -> None:
        self.sent: list[httpx.Request] = []
        self._replies = list(replies)
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.sent.append(request)
        if len(self.sent) > len(self._replies):
            raise AssertionError("Azure adapter sent an unexpected extra request")
        return self._replies[len(self.sent) - 1]


async def synthesize(replay: AzureReplay, target: str) -> bytes:
    """Proposed adapter interface; import resolves inside the observed async operation."""
    from language_lab.adapters.azure import AzureSpeech

    speech = AzureSpeech(AZURE_KEY, AZURE_REGION, transport=replay.transport)
    try:
        return await speech.synthesize("en-US", "en-US-AndrewNeural", target)
    finally:
        await speech.aclose()


async def voice_transition(replay: AzureReplay, locale: str) -> tuple[list[Any], list[Any]]:
    from language_lab.adapters.azure import AzureSpeech

    speech = AzureSpeech(AZURE_KEY, AZURE_REGION, transport=replay.transport)
    try:
        before = await speech.voices(locale)
        after = await speech.voices(locale)
        return before, after
    finally:
        await speech.aclose()
