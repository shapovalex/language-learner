"""Speech port fake: controlled catalog and synthesis, without provider calls."""

from language_lab.domain.audio import Voice
from language_lab.domain.errors import AppError, ErrorCode
from tests.support.audio import EN_VOICE, FR_VOICE, MP3


class FakeSpeech:
    def __init__(self, data: bytes = MP3, *, error: ErrorCode | None = None) -> None:
        self.data = data
        self.error = error
        self.requests: list[tuple[str, str, str]] = []
        self.voice_requests: list[str] = []

    async def voices(self, locale: str) -> list[Voice]:
        self.voice_requests.append(locale)
        catalog = [(EN_VOICE, "en-US", "Andrew"), (FR_VOICE, "fr-CA", "Sylvie")]
        return [
            Voice(name=name, locale=tag, display_name=label)
            for name, tag, label in catalog
            if tag == locale
        ]

    async def synthesize(self, locale: str, voice: str, target: str) -> bytes:
        self.requests.append((locale, voice, target))
        if self.error is not None:
            raise AppError(self.error)
        return self.data
