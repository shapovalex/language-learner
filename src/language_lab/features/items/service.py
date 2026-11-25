"""Items: Save, create-or-update by ItemId in the AnkiStore (AD-6, AD-20), and the Item reads:
the search and the duplicate check, both matched on normalized text here (AD-12), and one Item
by ItemId, permanent deletion with retryable media cleanup, excluding an Item from
Pronunciation (its Pronounce Card suspended in Anki, AD-13), and clearing an Item's Anki flags
once the user has fixed it (the flag lives in Anki only).

Example audio: a Vocabulary Save given a Voice makes the example sentence's audio when the
Example and ExampleRussian both hold text and the stored Item has no example audio or another
Example; speech runs outside the Anki lock, and a failed synthesis saves the Item without it
(the caller warns). A clip the user chose on Item detail is stored instead, with nothing
synthesized. The backfill gives a batch of a Language's Vocabulary Items that lack it
their example audio, one Item at a time, a failed one counted and skipped.
"""

from dataclasses import dataclass

from language_lab.domain.catalog import Category, Language
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.items import (
    AudioIntent,
    Item,
    ItemContent,
    VocabularyContent,
    normalize_text,
)
from language_lab.features.audio.service import AudioService
from language_lab.ports.anki_store import AnkiStore

BACKFILL_BATCH = 5  # Items per backfill request: each one is a synthesis and a Save


@dataclass(frozen=True)
class BackfillBatch:
    """One backfill batch: Items given example audio, Items that failed (skipped), and Items
    still waiting after the `skip` the caller passed and this batch.
    """

    done: int
    failed: int
    remaining: int


def _wants_example(content: ItemContent) -> bool:
    return (
        isinstance(content, VocabularyContent)
        and bool(content.example.strip())
        and bool(content.example_russian.strip())
    )


class ItemService:
    def __init__(self, anki: AnkiStore, audio: AudioService | None = None) -> None:
        self._anki = anki
        self._audio = audio

    async def save(
        self,
        item_id: str,
        language: Language,
        content: ItemContent,
        audio: AudioIntent,
        audio_bytes: bytes | None = None,
        example_voice: str | None = None,
        example_audio_bytes: bytes | None = None,
    ) -> bool:
        """Save the Item `item_id`; a retry with the same ItemId updates it. With
        `example_voice`, a Vocabulary Item whose example audio is missing or whose Example
        changed gets new example audio in that Voice first (module docstring). Given
        `example_audio_bytes` (a clip the user chose), they are stored as its example audio
        instead and nothing is synthesized; they need a Vocabulary Item whose Example and
        ExampleRussian both hold text, else `VALIDATION_FAILED` before anything is written.
        Returns True when the synthesized audio couldn't be made, so the Item was saved without
        it. Raises `AppError(VALIDATION_FAILED | SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        example_bytes = example_audio_bytes
        failed = False
        if example_audio_bytes is not None:
            if not _wants_example(content):
                raise AppError(ErrorCode.VALIDATION_FAILED)
        elif example_voice and self._audio is not None and _wants_example(content):
            assert isinstance(content, VocabularyContent)
            if await self._example_changed(language, item_id, content):
                try:
                    example_bytes = await self._audio.preview(
                        language, example_voice, content.example
                    )
                except AppError:
                    failed = True
        await self._anki.save_item(
            item_id,
            language,
            content,
            audio,
            audio_bytes=audio_bytes,
            example_audio_bytes=example_bytes,
        )
        return failed

    async def _example_changed(
        self, language: Language, item_id: str, content: VocabularyContent
    ) -> bool:
        """Whether the stored Item lacks example audio or holds another Example (or is new)."""
        try:
            stored = await self._anki.get_item(language, item_id)
        except AppError as exc:
            if exc.code is ErrorCode.NOT_FOUND:
                return True
            raise
        if not stored.has_example_audio:
            return True
        old = stored.content
        return not isinstance(old, VocabularyContent) or old.example != content.example

    async def backfill_example_audio(
        self, language: Language, voice: str, skip: int = 0, limit: int = BACKFILL_BATCH
    ) -> BackfillBatch:
        """Give up to `limit` of `language`'s Vocabulary Items with an Example and its Russian
        but no example audio that audio in `voice`, after skipping the first `skip` such Items
        (the ones earlier batches failed). Each is synthesized outside the Anki lock, then
        written only if the Item is unchanged. Only a failed synthesis counts as `failed` (the
        caller's next `skip`); an Item changed since the read counts as neither. An unknown
        Voice is `VALIDATION_FAILED` before anything is written. Raises
        `AppError(VALIDATION_FAILED | SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        if self._audio is None or not voice.strip():
            raise AppError(ErrorCode.VALIDATION_FAILED)
        if not any(v.name == voice for v in await self._audio.voices(language)):
            raise AppError(ErrorCode.VALIDATION_FAILED)
        candidates = await self._anki.item_candidates(language, Category.VOCABULARY)
        pending = [
            item
            for item in candidates
            if not item.has_example_audio and _wants_example(item.content)
        ][skip:]
        done = failed = skipped = 0
        for item in pending[:limit]:
            content = item.content
            assert isinstance(content, VocabularyContent)
            try:
                data = await self._audio.preview(language, voice, content.example)
                written = await self._anki.store_example_audio(
                    language, item.item_id, content.example, data
                )
            except AppError as exc:
                # A clip that couldn't be made (or isn't an MP3) fails the Item, which the
                # caller then skips; Anki failing ends the batch
                if exc.code not in (ErrorCode.TTS_FAILED, ErrorCode.VALIDATION_FAILED):
                    raise
                failed += 1
                continue
            if written:
                done += 1
            else:
                # Gone, edited or given audio since the read: neither done nor failed; it drops
                # out of the next read or is pending there again
                skipped += 1
        return BackfillBatch(done, failed, max(0, len(pending) - done - failed - skipped))

    async def media(self, name: str) -> bytes:
        return await self._anki.get_media(name)

    async def search(
        self, language: Language, query: str = "", flagged_only: bool = False
    ) -> list[Item]:
        """The Items of `language`, both Categories, whose normalized Target, Russian meaning or
        any Russian alternative contains `query`'s normalized text, in Category order then store
        order (FR-22, AD-12). A query that normalizes to nothing lists every Item; with
        `flagged_only`, only the Items with a flagged card in Anki are kept. Anki only
        gets the exact note-type scopes (AD-4); nothing is written. Raises
        `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        wanted = normalize_text(query)
        found: list[Item] = []
        for category in Category:
            for item in await self._anki.item_candidates(language, category, with_flags=True):
                if flagged_only and not item.flagged:
                    continue
                if not wanted or _matches(item, wanted):
                    found.append(item)
        return found

    async def duplicates(
        self, language: Language, category: Category, target: str, item_id: str | None = None
    ) -> list[Item]:
        """The Items of `language` and `category` whose normalized Target equals `target`'s,
        leaving out `item_id`'s own, in the store's order (FR-19, AD-12). Raises
        `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        wanted = normalize_text(target)
        return [
            item
            for item in await self._anki.item_candidates(language, category)
            if item.item_id != item_id and normalize_text(item.content.target) == wanted
        ]

    async def get(self, language: Language, item_id: str) -> Item:
        """The Item `item_id` of `language`. Raises
        `AppError(NOT_FOUND | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        return await self._anki.get_item(language, item_id)

    async def delete(self, language: Language, item_id: str) -> None:
        """Permanently delete the scoped Item, then clean its media; retries finish cleanup."""
        await self._anki.delete_item(language, item_id)

    async def set_pronunciation_excluded(
        self, language: Language, item_id: str, excluded: bool
    ) -> None:
        """Exclude the Item `item_id` from Pronunciation, or include it again; a flag that
        already matches writes nothing. Raises
        `AppError(NOT_FOUND | SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        await self._anki.set_pronunciation_excluded(language, item_id, excluded)

    async def clear_flag(self, language: Language, item_id: str) -> None:
        """Clear the Anki flag of every flagged card of the Item `item_id`; an Item with no
        flagged card writes nothing. Raises
        `AppError(NOT_FOUND | SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        await self._anki.clear_flag(language, item_id)


def _matches(item: Item, wanted: str) -> bool:
    content = item.content
    texts = [content.target, content.russian, *content.russian_alternatives]
    return any(wanted in normalize_text(text) for text in texts)
