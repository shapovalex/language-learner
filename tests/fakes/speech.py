"""Speech port fake: controlled catalog and synthesis, without provider calls."""

from language_lab.domain.audio import Voice
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.pronunciation import Assessment
from tests.support.audio import EN_VOICE, FR_FR_VOICE, FR_VOICE, MP3


class FakeSpeech:
    def __init__(self, data: bytes = MP3, *, error: ErrorCode | None = None) -> None:
        self.data = data
        self.error = error
        self.requests: list[tuple[str, str, str]] = []
        self.voice_requests: list[tuple[str, ...]] = []
        self.assessments: list[dict[str, object]] = []
        self.assessment: Assessment | None = None

    async def assess(self, locale: str, target: str, wav: bytes) -> Assessment | None:
        self.assessments.append({"locale": locale, "target": target, "wav": wav})
        if self.error is not None:
            raise AppError(self.error)
        return self.assessment

    async def voices(self, locales: tuple[str, ...]) -> list[Voice]:
        self.voice_requests.append(locales)
        # Returned in the given locale order, as the port promises; the Azure adapter's own
        # ordering is covered in tests/integration/test_azure_speech.py
        catalog = [
            (FR_FR_VOICE, "fr-FR", "Denise"),
            (EN_VOICE, "en-US", "Andrew"),
            (FR_VOICE, "fr-CA", "Sylvie"),
        ]
        found = [
            Voice(name=name, locale=tag, display_name=label)
            for name, tag, label in catalog
            if tag in locales
        ]
        return sorted(found, key=lambda voice: locales.index(voice.locale))

    async def synthesize(self, locale: str, voice: str, target: str) -> bytes:
        self.requests.append((locale, voice, target))
        if self.error is not None:
            raise AppError(self.error)
        return self.data
