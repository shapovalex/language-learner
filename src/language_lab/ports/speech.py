"""Speech synthesis boundary. No preview sessions or persistence."""

from typing import Protocol

from language_lab.domain.audio import Voice


class Speech(Protocol):
    async def voices(self, locale: str) -> list[Voice]: ...

    async def synthesize(self, locale: str, voice: str, target: str) -> bytes: ...
