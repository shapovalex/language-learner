"""Items: Save, create-or-update by ItemId in the AnkiStore (AD-6, AD-20)."""

from language_lab.domain.catalog import Language
from language_lab.domain.items import AudioIntent, ItemContent
from language_lab.ports.anki_store import AnkiStore


class ItemService:
    def __init__(self, anki: AnkiStore) -> None:
        self._anki = anki

    async def save(
        self, item_id: str, language: Language, content: ItemContent, audio: AudioIntent
    ) -> None:
        """Save the Item `item_id`; a retry with the same ItemId updates it. Raises
        `AppError(SETUP_REQUIRED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        await self._anki.save_item(item_id, language, content, audio)
