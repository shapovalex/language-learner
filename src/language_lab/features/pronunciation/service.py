"""Pronunciation review: the Language's queue read and a Card's Rating through the AnkiStore
(FR-30, FR-34, AD-20), and the session start and end signals, which only ask the
SyncRequester for a Sync and never wait for it (FR-36, AD-17). Nothing about a session is kept.
"""

import asyncio

from language_lab.domain.catalog import Language
from language_lab.domain.pronunciation import Assessment, PronunciationQueue, Rating
from language_lab.features.pronunciation.audio import to_wav
from language_lab.ports.anki_store import AnkiStore
from language_lab.ports.speech import Speech
from language_lab.ports.sync_requester import SyncRequester


class PronunciationService:
    def __init__(self, anki: AnkiStore, *, sync: SyncRequester, speech: Speech) -> None:
        self._anki = anki
        self._sync = sync
        self._speech = speech

    async def attempt(
        self, language: Language, item_id: str, recording: bytes
    ) -> Assessment | None:
        # get_item's scoped lock is released before decode or the provider request.
        item = await self._anki.get_item(language, item_id)
        wav = await asyncio.to_thread(to_wav, recording)
        locale = "en-US" if language == Language.EN else "fr-CA"
        return await self._speech.assess(locale, item.content.target, wav)

    async def queue(self, language: Language) -> PronunciationQueue:
        """The Language's queue in FR-30 order. Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`."""
        return await self._anki.pronunciation_queue(language)

    async def rate(self, language: Language, card_id: int, reps: int, rating: Rating) -> bool:
        """Answer the Card at `reps`; True when it was already answered (AD-20). Raises
        `AppError(NOT_FOUND | SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        return await self._anki.answer_card(language, card_id, reps, rating)

    async def session_signal(self) -> None:
        """A session started or ended: request a Sync and return at once. Never raises."""
        await self._sync.request()
