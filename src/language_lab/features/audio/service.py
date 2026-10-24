"""Speech requests do not enter the Anki lock or retain preview state."""

from language_lab.domain.audio import Voice
from language_lab.domain.catalog import LOCALES, Language
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.ports.speech import Speech


class AudioService:
    def __init__(self, speech: Speech):
        self._speech = speech

    async def voices(self, locale: str) -> list[Voice]:
        if locale not in LOCALES.values():
            raise AppError(ErrorCode.VALIDATION_FAILED)
        return await self._speech.voices(locale)

    async def preview(self, language: Language, voice: str, target: str) -> bytes:
        if not target.strip():
            raise AppError(ErrorCode.VALIDATION_FAILED)
        locale = LOCALES[language]
        if voice not in {entry.name for entry in await self.voices(locale)}:
            raise AppError(ErrorCode.VALIDATION_FAILED)
        return await self._speech.synthesize(locale, voice, target)
