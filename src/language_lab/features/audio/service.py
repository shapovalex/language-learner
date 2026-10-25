"""Speech requests do not enter the Anki lock or retain preview state."""

from language_lab.domain.audio import Voice
from language_lab.domain.catalog import LOCALES, Language
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.ports.speech import Speech


class AudioService:
    def __init__(self, speech: Speech):
        self._speech = speech

    async def voices(self, language: Language) -> list[Voice]:
        """All of the Language's Voices, in its locale order, from one catalog read."""
        return await self._speech.voices(LOCALES[language])

    async def preview(self, language: Language, voice: str, target: str) -> bytes:
        """Synthesize in the chosen Voice's own locale, once it is in the Language's catalog."""
        if not target.strip():
            raise AppError(ErrorCode.VALIDATION_FAILED)
        chosen = next((entry for entry in await self.voices(language) if entry.name == voice), None)
        if chosen is None:
            raise AppError(ErrorCode.VALIDATION_FAILED)
        return await self._speech.synthesize(chosen.locale, voice, target)
