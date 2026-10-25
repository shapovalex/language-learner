"""Speech synthesis boundary. No preview sessions or persistence."""

from typing import Protocol

from language_lab.domain.audio import Voice
from language_lab.domain.pronunciation import Assessment


class Speech(Protocol):
    async def voices(self, locales: tuple[str, ...]) -> list[Voice]:
        """Neural Voices of these exact locales, grouped in the given locale order."""
        ...

    async def synthesize(self, locale: str, voice: str, target: str) -> bytes: ...

    async def assess(self, locale: str, target: str, wav: bytes) -> Assessment | None:
        """None means every reference word was omitted; failures raise ASSESSMENT_FAILED."""
        ...
